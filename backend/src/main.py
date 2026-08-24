from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.core.db import init_redis
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
logger = logging.getLogger(__name__)

# ── Lifespan Context ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything BEFORE the yield runs exactly once when the server boots
    logger.info("Initializing infrastructure...")
    init_redis()
    logger.info("OptiRoute is fully booted and ready to accept traffic.")
    
    yield
    
    # Everything AFTER the yield runs when you stop the server (Ctrl+C)
    logger.info("Shutting down OptiRoute...")

app = FastAPI(title="OptiRoute API", version="1.0.0", lifespan=lifespan)

# Allow the React dev server (port 3000) to call this API and exchange cookies.
# allow_credentials=True is required for the qm_session cookie to be sent/received.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("OptiRoute initialized")

@app.get("/api/health")
def health():
    # Simple liveness check — used to verify the server is up.
    logger.info("Health check requested")
    return {"status": "ok"}
    