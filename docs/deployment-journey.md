# Deployment journey and decisions

This is the learning/history companion to the setup instructions. It records
the preparation topics, decisions, and explanations covered while taking the
project from local development to its working public CI/CD deployment. Exact
commands/configuration live in the linked guides and repository files.

## Goal and boundaries

The goal was to learn a company-style deployment flow using containers, a real
cloud VM, cloud identities, a registry, and GitHub Actions, while getting a
working app ready for a teacher presentation. The chosen first deployment was
one VM with Docker Compose. Kubernetes and multi-cloud deployment were not
requirements for this first functioning pipeline.

Work was deliberately broken into small, reviewable changes. Builds, cloud
commands, uploads, and workflow runs were performed by the user. Existing
GitHub Actions/Docker experience was expanded into a complete deployment path.
The final documentation describes the actual GCP deployment rather than the
initial AWS proposal or every abandoned intermediate configuration.

## Application preparation: topics 1–12

| Topic | What changed or was decided | Where to look |
| --- | --- | --- |
| 1. API addressing/proxy | Browser requests use relative /api URLs. Vite proxies in development; Nginx proxies in the frontend image. | frontend/src/api/chatApi.js, frontend/vite.config.js, frontend/nginx.conf |
| 2. CORS | Removed backend CORS configuration for the selected single-origin proxy deployment. | backend/src/main.py |
| 3. Provider/model configuration | Model names and provider selection moved into environment-backed settings. | backend/src/core/config.py |
| 4. Configuration validation | Validate selected provider/fallback settings at startup. Conditional SDK-client initialization was explicitly deferred. | backend/src/core/config.py, backend/src/services/llm_client.py |
| 5. Environment template | Added a safe template with setting names/defaults and blank API credentials. | backend/.env.example |
| 6. Runtime/dependency versions | Python 3.11, Node 22/npm 10, direct Python pins, frontend lockfile. Complete transitive Python locking remains deferred. | backend/.python-version, frontend/.nvmrc, requirements.txt, package-lock.json |
| 7. Model artifacts | Keep classifier/router weights available to deployment; backend GitHub checkout pulls Git LFS, and the image build validates models. | .gitattributes, backend/Dockerfile, publish-images.yml |
| 8. Health/readiness | Separate process liveness from Redis readiness. Startup/readiness failures propagate to deployment checks. | backend/src/main.py, backend/src/core/db.py |
| 9. Redis startup/recovery | Use Compose healthy dependency ordering. Additional runtime recovery/retry work was deferred. | compose.yaml |
| 10. Shutdown/client cleanup | Existing per-request HTTP context managers remain; additional shared-client cleanup was deferred. | backend/src/services/llm_client.py, backend/src/main.py |
| 11. Logging | Reduce sensitive/noisy request logging, configure application verbosity, and rotate container log files. | application loggers, config.py, compose.yaml |
| 12. Lint cleanup | Removed unused imports/variables. Remaining React hook/export lint findings were deferred rather than treated as an implemented CI gate. | frontend source and eslint.config.js |

The direct dependency/model compatibility caveats remain documented in the
[README](../README.md). Documentation does not imply those deferred changes
were implemented later.

### The separate conversation-state issue

Before packaging, shared in-process conversation memory was replaced with
Redis state keyed by a browser-generated session UUID. A Python module/global
list belongs to the server process; it does not become a fresh isolated list
for every visitor. Multiple requests can otherwise read or mutate the same
conversation. Additional workers would each have their own inconsistent copy,
and a process restart would lose that copy.

The selected design has no login system and no durable chat storage. React
keeps its session UUID only in memory. Ordinary requests send the new message
and UUID, with edit/regeneration information when applicable; the schema also
accepts multiple user/assistant messages for supported history scenarios.
Redis stores each conversation with a rolling TTL. Refreshing loses the browser
UUID and starts a new conversation, while abandoned keys expire later. This is
not a cookie-backed persistent login/session system.

Redis being external to the Python process fixes that specific global-state
problem. It does not by itself guarantee arbitrary same-session concurrent
updates are transactional or prove multi-worker performance. Those were not
claimed as tested deployment properties.

## Packaging and public readiness: topics 13–17

| Topic | Final result |
| --- | --- |
| 13. Docker images | Separate frontend/backend images. Frontend uses a build stage and Nginx runtime; backend packages CPU dependencies/models and one production Uvicorn worker. |
| 14. Compose | Three services: frontend, backend, Redis, with health-based ordering, restart policies, logs, and private networking. |
| 15. Public entry point | Initially loopback-only HTTP; later completed with a reserved GCP IP, Name.com DNS, and host-side Caddy HTTPS. |
| 16. Resource limits | Backend 2 GiB/1.5 CPU, frontend 128 MiB/0.25 CPU, Redis 512 MiB/0.25 CPU, checked against observed usage. |
| 17. Public demo safeguards | Body/schema limits, per-IP request rate, global active-chat limit, correct proxy trust, and cloud firewall rules. An account/password gate was explicitly declined. |

The initial backend measurements were about 559 MiB idle and 613 MiB during one
generation. A later limited run showed about 523 MiB against its 2 GiB ceiling.
These supported initial headroom; they were not a full load test or proof that
the VM can sustain any particular number of simultaneous users.

Docker Desktop initially displayed 7.432 GiB as a shared engine memory limit,
not an individual 7.432 GiB reservation per container. A limit of 1.5 CPUs means
approximately 1.5 CPU-seconds of scheduler time per second across available
cores. It does not mean one-and-a-half physical processors or a fixed number
of Python threads.

The five-chat limit is an admission limit at Nginx, independent of Uvicorn's
worker count. One worker is a process, not one request at a time: asynchronous
work can interleave while waiting, while synchronous work may still block it.
The limit keeps active generation from growing without a ceiling; it does not
spawn five dedicated application instances or guarantee a measured capacity.

HTTPS encrypts/authenticates transport but does not choose the application's
request-body limit. Nginx's 128 KiB limit bounds bytes accepted before forwarding
to Python; the 20,000-character schema limit is a separate per-message rule.
An application can therefore return 413 for total body size even if each
message individually fits its character limit.

## Cloud and automation: topic 18

### Why the first AWS attempt stopped

An AWS account was created and root MFA enabled. The console presented a managed
project/account experience named Fresh Deploy. IAM users, IAM Identity Center,
and IAM OIDC identity providers were discussed, but they are different features:
the intended GitHub integration needed a workload identity trust relationship,
not a human SSO directory.

Attempting `iam:CreateOpenIDConnectProvider` returned an explicit denial from
an organization service control policy while using AccountFullAccessRole.
Reading that policy was also denied. This was an observed restriction of that
account context. Switching from the console to CloudShell, adding an IAM allow,
or making another user would not override an applicable explicit organization
deny. The conversation moved to GCP instead of changing the managing
organization's controls.

Do not generalize the earlier assistant/Amazon Q discussion into a current rule
that every AWS free account lacks OIDC, or that IAM and Identity Center are the
same service. No AWS deployment was completed. The actual completed pipeline
uses GCP and requires no AWS resources or credentials.

Root MFA protected the original AWS root sign-in. A human root/admin identity,
a regular human login, a workload trust provider, and a service role are
different concepts; creating one does not replace every other access check.
The GCP implementation uses the human project owner for setup and separate
service accounts for build/deployment and VM runtime responsibilities.

Cloud VM baseline usage is associated with allocated infrastructure and uptime,
not only the number of chat requests. Hosted-model API usage is a separate
resource. Trial credits and free allowances were considered while choosing a
provider, but current eligibility and remaining credit must be checked in the
account; no dated trial offer is treated as a permanent feature of the app.

### GCP setup in the order it was learned

1. Create the GCP project and enable required APIs.
2. Create github-deployer, workload identity pool/provider, claim restrictions,
   and Workload Identity User binding; select main as the deployment branch.
3. Add the provider resource name as a GitHub repository variable and verify
   cloud authentication with GitHub Actions.
4. Create Artifact Registry and give the deployment identity repository Writer.
   Adapt builds to Docker's maintained login/Buildx/build-push actions, caching,
   commit tags, and separate frontend/backend jobs.
5. Create optiroute-runtime with repository Reader, attach it to the VM, and
   install Docker. Verify the runtime identity and manually pull published images.
6. Upload Compose/config/environment files, run the production override, and
   confirm healthy containers through the loopback entry point.
7. Reserve the VM IP, register optiroutee.tech, set its root A record, and verify
   DNS. Establish client-IP and HTTPS-scheme forwarding through both proxies.
8. Install/validate/reload host Caddy, open web ports, and test public HTTPS and
   browser streaming.
9. Grant IAP/OS Login access, discovery permissions, and actAs; verify GitHub's
   SSH login and passwordless sudo.
10. Prepare root-owned /opt/optiroute and implement deploy.sh. Then connect it to
    the workflow so every main push can build, publish, deploy, and verify.

The [cloud setup guide](cloud-setup.md) contains reconstruction commands. The
[pipeline walkthrough](pipeline.md) explains exactly what each workflow stage
and script section does.

## Important explanations and mistakes corrected

### Same-origin proxying and CORS

The browser downloads frontend files, then its JavaScript makes API requests.
Those API requests are not automatically made by the frontend server. With
relative /api URLs, the browser contacts the same public hostname and the
reverse proxy forwards them internally. That same-origin browser URL removes
the need for CORS in this deployment; changing a backend Host header alone is
not what removes browser cross-origin checks.

### localhost, Docker, and WSL

127.0.0.1 means the current network namespace's loopback. A container's localhost
is not the host's localhost or another container's localhost. Docker service
names resolve other Compose containers on their shared network.

On Windows, Docker Desktop can run its Linux engine through WSL2, adding a
Linux VM/networking layer between Windows and the containers. Publishing a port
asks Docker/Desktop to route host traffic to the container; a running Redis
container alone does not prove that a backend in another namespace can reach
it using that backend's localhost. The exact original Windows Redis error and
root cause are not reconstructed here without its complete diagnostic output.
The final Compose deployment removes host-specific Redis addressing by using
redis://redis:6379 on the shared Docker network.

### Source address versus destination address

Caddy connects to the host's 127.0.0.1:8080 destination. Docker forwards that to
Nginx and the request arrives from the bridge gateway 172.18.0.1 in this setup.
That is why Nginx originally saw the gateway rather than loopback/visitor IP.
172.18.0.1 and 172.18.0.10 are different addresses. The latter is the frontend's
own address for connections to the backend. Real-IP header processing changes
Nginx's interpretation of the visitor; it does not change the container's IP.

### Configuration mounted versus baked into an image

The main frontend Nginx configuration is baked into the frontend image. The
host-specific trusted-proxy address/scheme entries are mounted in production
with read-only bind mounts. `create_host_path: false` makes a missing file fail
instead of silently creating an unexpected directory. This keeps local-image
defaults separate from the production trust boundary without an image rebuild
for every host-specific trust file adjustment.

### Tokens, Docker login, tags, and digests

Obtaining a GCP token and configuring Docker to use it are separate operations.
Docker login saves registry credentials for the Docker client user; the token
does not automatically renew just because the VM has a service account.
Expiration explained later manual pull failures. The final script retrieves a
fresh token on every deployment and cleans its temporary Docker configuration.

The same source commit tags frontend and backend, but the images have different
content digests. A frontend digest appended to the shared IMAGE_TAG caused a
backend not-found error. IMAGE_TAG now contains only the commit SHA. The chosen
tag is explicit; Compose never searches the registry for the newest commit.

### Root log level versus application log level

`logging.basicConfig(level=INFO)` sets the root logging baseline. Named loggers
normally inherit through their dotted-name hierarchy unless overridden. Setting
the `src` logger to LOG_LEVEL changes the application's logger subtree while
leaving the root baseline for other libraries separate. Raising/lowering the
root level alone would affect unrelated inheriting libraries too. Container log
rotation is separate from which messages the Python logger emits.

## Topic 19: excluded

Release-recording/snapshot additions were undone at the user's request. The
working CI/CD health checks remain; no rollback workflow, saved release ledger,
or automatic restoration behavior is configured. The pre-existing .env.previous
file only saves the last attempted environment selection and is not a full
release history. We are not proceeding with the rest of topic 19.

## Topic 20: documentation

The requested deliverable is this documentation set: architecture, cloud setup,
configuration, pipeline internals, operations, and the decisions/lessons above.
Infrastructure as code was explicitly excluded. The documentation records
manual infrastructure setup and the implemented automatic application pipeline.
No Terraform, Kubernetes setup, cloud provisioning, or new account system is
introduced by this step.
