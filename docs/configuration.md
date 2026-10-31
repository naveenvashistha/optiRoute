# Configuration reference

## Environment-file boundaries

| File | Consumer | Contents |
| --- | --- | --- |
| `backend/.env.example` | Humans copying the template | Safe setting names/defaults with empty credential fields. |
| Local `backend/.env` | Backend, or Compose `env_file` | Provider keys and backend settings. |
| VM `/opt/optiroute/backend/.env` | Backend container | VM-only credentials/settings, owned by root with mode 600. |
| VM `/opt/optiroute/.env` | Docker Compose interpolation | `IMAGE_TAG=<full-commit-sha>`. |

Compose receives the root file explicitly through `--env-file`. The backend's
`env_file` injects variables into that container; it does not select the image
tag for Compose. The deployment script temporarily exports its SHA, which takes
precedence over the root .env during validation/pulling, then updates only
IMAGE_TAG after downloads succeed. Do not append `@sha256:...` to this shared tag:
frontend and backend have different image digests.

In production, root owns `/opt/optiroute` and its environment files. The deployment
account uses sudo with this absolute path; its OS Login username/home directory
does not change the path. A directory beginning with `~` would depend on the user.

## Runtime version files

`frontend/.nvmrc` records Node 22 for tools that understand that file, and
`backend/.python-version` records Python 3.11 for compatible Python version
managers. They help humans/tools select a runtime; the files do not install a
runtime or start a server by themselves. Frontend package.json also declares
the supported Node/npm range. Docker runtime selection comes from the FROM
instructions, and dependency versions come from requirements.txt/package-lock.json.
Patch-level base-image versions are not pinned by digest in this setup.

## Backend settings

The complete template is [backend/.env.example](../backend/.env.example), and the
implementation is [config.py](../backend/src/core/config.py).

| Group | Settings and behavior |
| --- | --- |
| Provider selection | `SLM_PROVIDER`: `groq` or `ollama`; `CLOUD_PROVIDER`: `gemini`, `openai`, or `groq`. Demo uses Groq/Gemini. |
| Credentials | `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`. Groq is also required for current cloud fallbacks. |
| Model names | `GROQ_SLM_MODEL`, `GROQ_CLOUD_MODEL`, `GEMINI_MODEL`, `OPENAI_MODEL`; use models available to your provider accounts. |
| Ollama | `OLLAMA_BASE_URL`, `LOCAL_MODEL_NAME`, `OLLAMA_NUM_CTX`; Compose does not provision an Ollama service. |
| Redis | Host development defaults to localhost; Compose supplies `REDIS_URL=redis://redis:6379`. Redis must support Search/vector indexing. |
| Session expiry | `REDIS_SESSION_TTL=86400` seconds of inactivity by default. Refresh loses the browser session reference; server expiry happens separately. |
| Cache expiry | `CACHE_TTL=3600` seconds by default; index/prefix use `REDIS_INDEX_NAME` and `REDIS_KEY_PREFIX`. |
| Models | Compose supplies `/app/models/intent_mlp_model.joblib` and `/app/models/optiroute_router_model`. |
| Embeddings | `VECTOR_DIMENSION=384`; changing this requires a compatible embedding model/index. |
| Thresholds | `SIMILARITY_THRESHOLD=0.10`, `INTENT_THRESHOLD=0.97` are the current defaults. |
| Application logs | `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL; defaults to INFO for `src` application loggers. |
| Savings display | `PRICE_PER_1M_INPUT_TOKENS`, `PRICE_PER_1M_OUTPUT_TOKENS` are configurable estimation inputs, not live provider pricing. |

Startup validates the selected providers and fallback settings without making
provider requests. Conditional SDK initialization was deferred: the current
module still constructs both OpenAI-compatible clients at import time. Retain
the credentials/configuration from your working deployment; do not assume every
unused-provider combination has been tested. This guide documents that behavior
without changing provider logic or adding dummy API keys.

## HTTP and resource controls

| Control | Current value/location |
| --- | --- |
| API body limit | Nginx `/api/`: 128 KiB; oversized bodies return 413. |
| Chat message content | 1–20,000 characters per message. |
| Message roles | `user` and `assistant`; at least one message is required. |
| Session identifier | UUID v4 in the request body; not a login credential. |
| Chat rate | 10 requests/minute per visitor IP, burst allowance 3; excess returns 429. |
| Concurrent chat requests | 5 across visitors for this Nginx instance; excess returns 429. |
| Proxy read timeout | 300 seconds between upstream reads, not a total generation deadline. |
| Docker logs | JSON files, maximum 10 MiB each, 3 files per service. |

Rate/concurrency keys apply to POST `/api/ask` and `/api/ask/`; health/static
requests do not consume chat slots. The Compose CPU/memory limits are listed
in the [architecture guide](architecture.md). No account/password gate is added.

## What is baked into images

Frontend source and `frontend/nginx.conf` are built into the frontend image.
Changing them requires an image build, handled by the workflow. The two
production proxy-trust files are runtime mounts, transferred by the workflow.
Backend source, classifier/router weights, and predownloaded embedding assets
are packaged into the backend image. API credentials are supplied at runtime.

Caddy runs on the host; its exact Caddyfile is documented in the
[cloud setup guide](cloud-setup.md#configure-caddy).
Its certificate storage is managed by the installed systemd service. Application
deployments do not automatically replace the host Caddy configuration.
