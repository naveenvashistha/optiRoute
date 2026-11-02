# Operating and troubleshooting OptiRoute

Use **Cloud Shell** for cloud/IAM administration and the **VM SSH terminal** for
host/container commands. Do not paste access tokens, backend environment files,
resolved Compose configuration, or provider credentials into shared output.

## Connect to the VM

From **Cloud Shell**:

```bash
gcloud compute ssh optiroute-vm \
  --project=optiroute-512819 --zone=asia-south1-a --tunnel-through-iap
```

For the following commands, define this Bash helper in the **VM SSH terminal**.
It works from your own home; root's access is used for /opt, so you do not need
to cd into its mode-700 directory as an unprivileged user.

```bash
dc() {
  sudo docker compose --project-name optiroute \
    --project-directory /opt/optiroute \
    --env-file /opt/optiroute/.env \
    -f /opt/optiroute/compose.yaml \
    -f /opt/optiroute/compose.production.yaml "$@"
}
```

## Status, logs, and resource usage

```bash
dc ps
dc logs --tail=100 backend
dc logs --tail=100 frontend
dc logs --tail=100 redis
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -n 100 --no-pager

sudo docker stats --no-stream
sudo docker system df
df -h
free -h
```

Use `dc logs -f --tail=100 backend` to follow logs and Ctrl+C to stop following;
that does not stop the container. Review log output before sharing it. The
application avoids logging prompt bodies in normal request processing, but
third-party and infrastructure errors still need review.

Compose rotates service logs at 10 MiB per file and three files per service.
Image layers accumulate separately from container logs. Disk usage should be
checked after multiple releases; there is no automatic image-pruning task.

## Readiness and demonstration checks

From the VM:

```bash
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS http://127.0.0.1:8080/api/ready
```

From Cloud Shell or your laptop:

```bash
curl -I http://optiroutee.tech
curl -fsS https://optiroutee.tech/api/ready
```

Expected results are `{"status":"ok"}`, `{"status":"ready"}`, an HTTP-to-HTTPS
redirect, and public ready JSON. Readiness pings Redis; it does not validate
provider keys, quotas, or generation quality.

For a presentation: open the HTTPS site without a certificate warning, send one
normal message and observe streaming, send a follow-up to demonstrate context,
then refresh and confirm a fresh conversation. Show the green GitHub workflow,
its image-tag summary, and `dc ps`. Browser refresh abandons the old session
reference; the Redis key itself remains until TTL/restart.

## Restarting and configuration updates

For a stuck backend using the already deployed configuration:

```bash
dc restart backend
dc ps
curl -fsS http://127.0.0.1:8080/api/ready
```

A restart does not reread changed Compose/environment-file configuration.
After intentionally editing backend runtime configuration on the VM:

```bash
sudo nano /opt/optiroute/backend/.env
sudo chmod 600 /opt/optiroute/backend/.env
dc config --quiet
dc up -d --no-build --pull never --wait --wait-timeout 300
```

For application source, Dockerfile, or versioned deployment-file changes,
commit and merge into main so the pipeline builds/deploys one matching commit.
For a Caddyfile edit, validate first, then reload its service:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

Redis is deliberately temporary. Restarting/recreating Redis loses chats and
semantic cache; stopping the backend alone does not deliberately clear Redis.
Do not use `compose down` as the normal release command; deploy.sh uses `up`.

## Failed GitHub deployment

Open the failed job and find the first failed step:

| Stage | First things to check |
| --- | --- |
| Checkout/backend model load | Git LFS weights downloaded; Dockerfile model checks and dependency errors. |
| GCP authentication | Provider repository variable, project number, numeric GitHub claims, main ref, and Workload Identity User binding. |
| Registry login/push | Artifact Registry API/repository/region and deployer Writer binding on that repository. |
| IAP/SSH | IAP rule, OS Login metadata, instance OS Admin Login, discovery permissions, actAs on runtime account. |
| Missing /opt files | Complete the one-time directory/private environment setup in the deployment guide. |
| Metadata identity/login | Runtime SA attached, cloud-platform scope, Reader binding, metadata token retrieval. |
| Pull | Both images published under the exact commit SHA; fresh authentication; VM disk capacity. |
| Startup/local readiness | `dc ps`, backend/frontend/Redis logs, runtime configuration, model memory, and Docker network. |
| Public HTTPS readiness | DNS, reserved IP, TCP 80/443 rules, Caddy status/certificate logs, then loopback readiness. |

A pipeline skipped because main moved is intentional; inspect the newer run.
An active run is not canceled by a new push, and intermediate pending runs can
be replaced. A lock error means another script is deploying; let it finish and
inspect that run rather than deleting the lock file during deployment.

Build/pull failures before the switch leave the running app unchanged by the
script. After installation/container replacement starts, a failure can leave a
partially updated app. No automatic rollback exists. Diagnose the failed stage,
fix the configuration/code, and deploy the intended current main commit.

## Specific problems encountered during setup

### Registry authentication failed after an earlier successful pull

The original manual metadata access token expired. Having a service account
attached does not automatically log Docker in or refresh a saved login. Use the
fresh metadata-token Docker login from the cloud setup guide before a manual
pull. deploy.sh performs that login on every deployment with a temporary config.
Existing running containers do not need registry authentication to keep running.

### Frontend pulls but backend returns not found

IMAGE_TAG previously contained `<commit>@sha256:<frontend-digest>`. A digest
selects specific image content; the frontend digest does not identify the
backend. Use only the full commit SHA for the shared IMAGE_TAG. Check the two
published image references in the workflow summary.

### Compose does not select the expected images

Use both Compose files, with production second, and the correct root env file.
`up` uses the selected tag; it does not discover the newest commit in the
registry. `--pull always` means refresh that selected reference, not select
another tag. backend/.env is a container environment file, not the source of
Compose's IMAGE_TAG interpolation.

### Network optiroute_default declared as external, but could not be found

An earlier config expected an externally managed Docker network. `compose down`
removed the existing network, so the next up could not find it. The final
production file declares a Compose-managed bridge with an explicit subnet and
gateway, allowing Compose to create it. Use the current committed production
file. If Docker reports an overlap instead, inspect existing networks before
changing the bridge or any trusted-proxy addresses:

```bash
sudo docker network ls
sudo docker network inspect optiroute_default
```

### sudo works initially, then prints "I'm afraid I can't do that"

In this VM session, the alternative sudo implementation worked when the default
one did not. The observed diagnosis was `sudo.ws -n whoami` returning root while
`sudo whoami` failed. The workaround used the supported system alternative:

```bash
update-alternatives --display sudo
sudo.ws update-alternatives --set sudo /usr/bin/sudo.ws
hash -r
sudo whoami
readlink -f /usr/bin/sudo
```

Use this only when that alternative actually exists and the same diagnosis
applies. It is not a general fix for missing sudo privileges or OS Login IAM.
The exact distribution bug was not established in the chat.

### The browser sees HTTP redirects after HTTPS access

There are two redirects: Caddy upgrades HTTP to HTTPS; FastAPI can correct a
trailing slash. Check the production trusted-proxy mounts, scheme map, fixed
frontend IP, and backend FORWARDED_ALLOW_IPS before changing TLS itself.
The following VM-only probe deliberately requests the slash variant:

```bash
curl -sS -o /dev/null -D - \
  -H 'Host: optiroutee.tech' \
  -H 'X-Forwarded-For: 203.0.113.50' \
  -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:8080/api/ready/
```

Expected Location is `https://optiroutee.tech/api/ready`. The 203.0.113.50 address
is a synthetic test value, not a real visitor. Never broaden forwarded-header
trust to every address to make this test pass.

### Two Redis containers appear in docker stats

One was a standalone container created with docker run; the other belonged to
the Compose app. Compose uses the `redis` service on its network. An unrelated
standalone container does not automatically become this service. Inspect names
and the backend's configured Redis address before stopping anything.

## HTTP status reference

| Symptom | Meaning to investigate |
| --- | --- |
| 413 | Nginx API body limit exceeded. |
| 422 | Chat schema validation, such as missing/invalid session UUID or invalid message fields. |
| 429 | Nginx chat rate/concurrency limit or a provider limit reported through the app; inspect which layer rejected it. |
| 502 | A reverse proxy cannot obtain a usable upstream response; inspect Caddy/Nginx/backend status in order. |
| 503 from /api/ready | Backend cannot reach Redis in its readiness probe. |
| 504/stream stalls | Proxy/upstream timeout, provider delay, resource pressure, or connectivity; inspect logs. |

SSE generation errors can also arrive inside an already-started HTTP 200 stream.
A 200 response alone is not proof that generation completed successfully.

## What remains outside this deployment

There is no account/password gate, application database persistence, release
history/rollback automation, infrastructure-as-code provisioning, or cluster
orchestrator. Cloud resources remain until deliberately changed/removed; stopping
a container is not the same as deleting cloud resources. Check the GCP billing
console for current usage instead of assuming an idle deployment has no cost.
