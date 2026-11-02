# OptiRoute

OptiRoute is a streaming AI chat application that classifies requests, checks a
semantic cache, and routes generation to hosted language models. React serves
the UI, FastAPI runs the gateway and local routing models, and Redis holds
temporary conversations and cached answers.

Demo: [optiroutee.tech](https://optiroutee.tech).

## Deployment documentation

| Guide | Contents |
| --- | --- |
| [Architecture](docs/architecture.md) | Request flow, containers, proxy trust, identities, and CI/CD. |
| [Cloud setup](docs/cloud-setup.md) | GCP resources, GitHub OIDC, VM preparation, DNS, and HTTPS. |
| [Configuration](docs/configuration.md) | Environment files, provider settings, runtime limits, and temporary state. |
| [Deploying releases](deploy/deployment.md) | One-time /opt setup and the automatic deployment workflow. |
| [VM access](deploy/vm-access.md) | IAP, OS Login, and deployment-account permissions. |
| [Operations](docs/operations.md) | Status, logs, restarts, failed deployments, and demonstration checks. |
| [Pipeline walkthrough](docs/pipeline.md) | Detailed explanation of the workflow, deployment script, and authentication flow. |
| [Deployment journey](docs/deployment-journey.md) | Preparation steps, decisions, troubleshooting lessons, and deferred work. |

The deployed application uses a single GCP VM with Docker Compose and host-side
Caddy. A push to `main` builds separate frontend/backend images, publishes them
to Artifact Registry, deploys that commit to the VM, and checks public readiness.
Release-history snapshots and rollback automation are intentionally excluded.

## Local development with containers

Install Git LFS and Docker with the Compose plugin. From the repository root:

```bash
git lfs install
git lfs pull
cp backend/.env.example backend/.env
```

Fill `backend/.env` with your own provider credentials and model configuration.
The default provider combination uses Groq and Gemini. See the
[configuration guide](docs/configuration.md), including the deferred client
initialization behavior.

```bash
docker build -t optiroute-backend:local ./backend
docker build -t optiroute-frontend:local ./frontend
docker compose up -d --wait --wait-timeout 300
```

Open [localhost:8080](http://localhost:8080). Check infrastructure readiness:

```bash
curl -fsS http://localhost:8080/api/ready
docker compose ps
```

The backend build downloads the embedding model and loads the packaged routing
models. Git LFS weights must be present before building. Images do not include
environment files. Local Compose uses the two local image names; production
explicitly adds `compose.production.yaml` to select Artifact Registry images.

## Developing without application containers

Use Python 3.11 and Node.js 22 (at least 22.13.0), with npm 10. The runtime files
select families rather than exact patch versions. The previously checked local
versions were Python 3.11.4, Node.js 22.18.0, and npm 10.9.3.

Start a Redis instance providing Search/vector support, for example in a
separate terminal:

```bash
docker run --rm --name optiroute-dev-redis -p 127.0.0.1:6379:6379 redis:8.8
```

Create and activate a Python 3.11 virtual environment. In `backend`:

```bash
python -m pip install "torch==2.13.0" --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python -m pip check
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Install CPU-only PyTorch first to avoid selecting CUDA dependencies for the CPU
server. In another terminal, from `frontend`:

```bash
npm ci
npm run dev
```

Open the URL Vite prints. Its `/api` proxy targets `127.0.0.1:8000`. A backend
running on the host uses `REDIS_URL=redis://localhost:6379`; Compose overrides it
with the Redis service address when the backend is containerized.

## Checks and known deferred work

From `frontend`, run `npm run build` and `npm run lint`. The frontend build is
part of image publishing; lint is not currently a required deployment gate.
Previously deferred React hook/export lint findings remain to be reviewed.

Backend direct dependencies are pinned, but the complete transitive dependency
graph is not locked. Container builds run `pip check` and model-loading checks.
The saved intent classifier has scikit-learn 1.0.2 metadata while the runtime
uses 1.9.0; the model loads in the current build but its compatibility warning
has not been resolved.

These guides document the setup implemented during this project; infrastructure
as code is outside the requested scope.

Other deferred work includes conditional provider-client initialization, shared
client shutdown cleanup, runtime Redis recovery/retries beyond startup ordering,
and broader concurrent-user testing. There is one backend worker to avoid
duplicating the local ML models. No Kubernetes, managed database, user-account
system, or automatic rollback is configured.
