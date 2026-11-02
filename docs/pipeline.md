# CI/CD pipeline walkthrough

This explains the implementation in
[publish-images.yml](../.github/workflows/publish-images.yml) and
[deploy.sh](../deploy/deploy.sh). The live pipeline was verified working during
the chat. This document describes that pipeline, not an additional deployment.

## 1. What triggers it

The workflow is named **Build and deploy OptiRoute**. It runs when a commit is
pushed to main, including a PR merge into main, or when manually dispatched on
main. It does not deploy pull-request branches or tags. Each job also checks
`github.ref == 'refs/heads/main'`, matching the cloud identity condition.

```text
push/merge to main
        ├── publish-frontend ──┐
        └── publish-backend ───┤
                              └── deploy → public readiness
```

The publish jobs run independently on separate temporary GitHub-hosted Ubuntu
runners. `runs-on: ubuntu-latest` does not mean our GCP VM. The final job connects
from its runner to our VM to update the application.

## 2. Permissions and credentials

The workflow has no default permissions. Each job explicitly requests:

- `contents: read` to check out repository contents and, in deployment, read the
  current main branch reference.
- `id-token: write` to request a signed identity token from GitHub's OIDC issuer.

There is no `packages: write` permission because images go to GCP Artifact
Registry, not GitHub Container Registry. The registry permissions come from
github-deployer's GCP repository-level IAM grant.

The authentication sequence is:

1. GitHub creates a signed OIDC JWT describing this workflow/repository/ref.
2. `google-github-actions/auth` sends it through GCP Workload Identity Federation.
3. GCP validates the issuer/signature, maps claims, and applies the owner ID,
   repository ID, and main-branch condition.
4. The matching principal has Workload Identity User on github-deployer, allowing
   service-account impersonation and short-lived credentials.
5. Build jobs request `token_format: access_token` and use the returned token
   with Docker login. The deployment job creates a temporary credential file
   used by gcloud for IAP/SSH calls.

The GCP provider name is read from the repository variable
`GCP_WORKLOAD_IDENTITY_PROVIDER`. Provider names, project IDs, account emails,
and image names are configuration identifiers; provider API keys remain only
in the VM's backend environment file. GitHub authentication does not use those
LLM keys. No long-lived GCP service-account key is created.

## 3. Building and publishing the images

Both jobs check out the exact event commit. Backend checkout has `lfs: true`
because the router's safetensors weights are Git LFS objects. Without that,
the build could receive a small pointer file rather than the model weights.

The Docker actions set up Buildx, authenticate to Artifact Registry, and build
and push the image from `./frontend` or `./backend`. Action versions are pinned
to full commit SHAs. GitHub Actions cache scopes are separate for frontend and
backend, allowing unchanged Docker layers to be reused across runs.

The target is `linux/amd64`, matching the x86-64 VM. QEMU and ARM multi-platform
builds were not needed for this target. `docker/metadata-action` was unnecessary
for the selected tagging scheme: each image is tagged directly with
`${{ github.sha }}` and labeled with the source repository and revision.

The frontend Dockerfile runs `npm ci` and `npm run build`, then copies only the
built static files into Nginx. Node is a build dependency, not a production
frontend server process.

The backend Dockerfile installs CPU-only PyTorch before the pinned Python
requirements, runs `pip check`, downloads/tests the 384-dimensional embedding
model at build time, and loads the classifier/router to catch packaging issues.
It uses a non-root application user and starts one Uvicorn worker. Environment
files are excluded from Docker build contexts/images.

Both image references appear in the GitHub run summary. The SHA tag denotes
the source commit; each image also has its own content digest. Tags remain
mutable in the current setup, so rebuilding the same SHA can replace that tag.
This pipeline does not deploy by pinned digest or maintain a release ledger.

## 4. Why deployment waits

The deployment job declares:

```yaml
needs: [publish-frontend, publish-backend]
```

GitHub starts it only after both jobs succeed. A failed frontend/backend build
does not start the deployment job, so the VM is not intentionally switched to
a release missing one application image.

After checkout/authentication, the job reads main's current SHA through GitHub's
API. If main has moved on, it records a skipped deployment in the summary.
This also prevents a rerun of an older workflow from intentionally restoring
an old commit. It is a pre-deployment check, not a continuous branch lock: a new
push after the check waits for the active workflow to finish.

## 5. How overlapping runs are handled

The entire workflow uses concurrency group `optiroute-production` with
`cancel-in-progress: false`. New pushes do not cancel an active SSH deployment.
By default GitHub retains one pending run and replaces that pending run if a
newer run arrives. Do not assume every intermediate commit will be deployed.

Separately, deploy.sh takes a nonblocking `flock` on
`/opt/optiroute/.deploy.lock`. A second manual/script deployment fails rather
than installing files while another script is changing containers. The lock
covers configuration installation and the container update, not just downloads.

## 6. Which files reach the VM

The runner creates a tar archive with this explicit list:

```text
compose.yaml
compose.production.yaml
deploy/deploy.sh
deploy/nginx-trusted-proxy.conf
deploy/nginx-forwarded-scheme.map
```

It uses gcloud SSH through IAP to create a private staging directory in the
deployment account's home, then gcloud SCP through IAP to upload the archive:

```text
~/.optiroute-release-<workflow-run-id>-<attempt>/release.tar.gz
```

OS Login automatically determines the account's Linux username. A service
account has an OS Login username prefixed with `sa_`. We do not hardcode that
username or its home directory. Inside the remote shell, `$HOME` refers to the
deployment account's home; `/opt/optiroute` is a fixed filesystem location shared
by all users with appropriate permissions.

The remote command checks that the root and backend environment files already
exist in /opt, extracts the archive, and invokes:

```text
sudo -n bash <staging-directory>/deploy/deploy.sh <commit-sha> <staging-directory>
```

`sudo -n` requires noninteractive administrator access. The workflow never
prompts for a password. It removes the staging directory when the remote command
finishes, including failures. A connection/upload failure before that command
starts can leave an unused staging directory for later inspection.

## 7. What deploy.sh does

The optional second argument is the absolute directory containing versioned
release files. Without it, a manual run uses files already in /opt/optiroute.
The script uses `set -euo pipefail` and `umask 077` to fail on unhandled errors,
catch pipeline failures, and create private temporary files.

In execution order:

1. Validate the lowercase 40-character SHA, root execution, tools, environment
   files, and the release-file list; enter /opt and acquire the deployment lock.
2. Export IMAGE_TAG for the requested commit. Compose shell variables override
   values in the root .env for this invocation. Validate the staged Compose
   configuration with `config --quiet` so resolved secrets are not printed.
3. Ask the metadata service for the VM's attached account email. Refuse to use
   an unexpected identity instead of pulling with arbitrary VM credentials.
4. Retrieve a fresh runtime access token and send it to Docker login over stdin.
   DOCKER_CONFIG points to a private temporary directory, leaving the existing
   root Docker login configuration alone. Exit cleanup removes the temporary
   token/configuration; do not enable shell tracing around these commands.
5. Pull frontend/backend with `--policy always`, and Redis with `--policy missing`.
   If downloading fails, running containers and the root release selection have
   not yet been changed by this script.
6. Install the staged Compose files, proxy files, and script under /opt, while
   holding the same deployment lock.
7. Preserve the previous root .env as `.env.previous`, then replace only the
   IMAGE_TAG setting through an atomic temporary-file rename. The backend
   credential file is not overwritten.
8. Run Compose with the fixed project name optiroute and explicit project
   directory/env/Compose paths. Use `up -d --no-build --pull never --wait
   --wait-timeout 300`, since images were downloaded before the switch.
9. Check `/api/ready` through `127.0.0.1:8080` and require `status == "ready"`.
   Exit with an error if startup/readiness fails; clean temporary credentials
   and release the deployment lock on exit.

The fixed Compose project name updates the existing app even though its
configuration moved from a personal home to /opt. Production Compose is listed
second, so it overrides local image names and adds production networking and
trust mounts. `--project-directory /opt/optiroute` makes relative runtime paths
resolve there even when the Compose files were uploaded into staging.

## 8. The public check and its limits

After the SSH deployment command succeeds, the runner requests:

```text
https://optiroutee.tech/api/ready
```

This exercises DNS, public network access, TLS, Caddy, frontend proxying, the
backend, and its Redis readiness check from outside the VM. It does not invoke
a paid LLM response or prove every feature works. Browser chat/streaming remains
an additional manual demonstration check.

An unhealthy deployment or failed public check makes the job red. Some new
containers/configuration may already be active at that point. There is no
automatic rollback, saved release snapshot, or restoration job. `.env.previous`
only holds the previous environment selection from the most recent attempt;
it is not a full known-good release record. Failure handling is inspection and
an intentional corrective main-branch deployment.

## 9. What is automatic and what remains one-time/manual

| Automatic per main release | One-time or deliberate administration |
| --- | --- |
| Build and publish both images | Create GCP resources/permissions and reserve the IP. |
| Authenticate GitHub via OIDC | Configure DNS and install/configure host Caddy. |
| Transfer versioned deployment files | Prepare /opt and private provider configuration. |
| Authenticate the VM's Docker client and pull images | Change/rotate provider keys and adjust cloud resources. |
| Apply Compose and run readiness checks | Inspect logs, investigate errors, and test a real browser chat. |

The separate **Check GCP authentication** workflow is manually dispatched on
main. It verifies registry access and IAP/OS Login with `whoami; sudo -n whoami`.
It does not publish images or deploy containers.

References: [workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[Google authentication action](https://github.com/google-github-actions/auth),
[Compose up](https://docs.docker.com/reference/cli/docker/compose/up/), and
[gcloud SCP](https://docs.cloud.google.com/sdk/gcloud/reference/compute/scp).
