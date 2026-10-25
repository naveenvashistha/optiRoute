# Build from the repository root: docker build -t optiroute-backend:local ./backend
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FASTEMBED_CACHE_PATH=/opt/fastembed_cache

WORKDIR /app

# ONNX Runtime uses OpenMP. The application itself does not need root privileges.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --no-log-init app \
    && mkdir -p /opt/fastembed_cache \
    && chown app:app /opt/fastembed_cache

COPY requirements.txt ./requirements.txt

# Install CPU-only PyTorch first to avoid pulling CUDA dependencies from PyPI.
RUN python -m pip install "torch==2.13.0" --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements.txt \
    && python -m pip check

USER app

# Download and exercise the embedding model during the build, not server startup.
RUN python -c "from fastembed import TextEmbedding; model = TextEmbedding(model_name='BAAI/bge-small-en-v1.5'); assert len(next(model.embed(['Build check']))) == 384"

ENV HF_HUB_OFFLINE=1

COPY src/ ./src/
# Git LFS weights must be downloaded into the checkout before building.
COPY models/ ./models/

# Fail the build if the packaged classifier or router cannot load on Linux.
RUN python -c "from src.services.classifier import classifier_model; from src.services.router import router_model"

EXPOSE 8000

# One worker avoids duplicating the in-memory ML models. No development reloader.
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
