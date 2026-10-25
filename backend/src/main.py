from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from src.core.config import settings
from src.core.db import init_redis, is_redis_ready
import logging

# ── Logging setup ─────────────────────────────────────────────────────────────
# Configure root logger once here so every module's logger inherits this format.
# Each module does `logger = logging.getLogger(__name__)` to get a named logger,
# so terminal output shows which file the log came from.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("src").setLevel(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# ── Lifespan Context ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything BEFORE the yield runs exactly once when the server boots
    logger.info("Validating configuration...")
    settings.validate()
    logger.info("Initializing infrastructure...")
    init_redis()
    logger.info("OptiRoute is fully booted and ready to accept traffic.")
    
    yield
    
    # Everything AFTER the yield runs when you stop the server (Ctrl+C)
    logger.info("Shutting down OptiRoute...")

app = FastAPI(title="OptiRoute API", version="1.0.0", lifespan=lifespan)


logger.info("OptiRoute initialized")

# --- ADD THESE TWO LINES ---
from src.api import chat
app.include_router(chat.router, prefix="/api")

@app.get("/api/health")
def health():
    # Simple liveness check — used to verify the server is up.
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.get("/api/ready")
def readiness():
    """Report whether the backend can reach its required session database."""
    if not is_redis_ready():
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
