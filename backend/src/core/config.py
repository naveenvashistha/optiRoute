import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables the moment this file is imported
load_dotenv()

# Calculate the absolute path to the root 'backend' folder.
# __file__ is config.py. We go up three levels: core -> src -> backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    # ── Redis Connection Settings ─────────────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Time-To-Live in seconds (e.g., 3600 = 1 hour). 
    # Redis will automatically delete entries older than this.
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))

    # ── Embedding & Similarity Settings ───────────────────────────────────────
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "384"))
    
    # Cache Threshold. Note: RedisVL calculates distance (1.0 - similarity).
    # If you want 90% similarity, the maximum distance allowed is 0.10.
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.10"))

    # Intent Classifier Threshold. If the probability of class 1 (cachable query)
    # is greater than or equal to this threshold, we classify it as a cachable query.
    INTENT_THRESHOLD: float = float(os.getenv("INTENT_THRESHOLD", "0.97"))

    # ── Intent Classifier Settings ────────────────────────────────────────────
    # Path to your trained MLP classifier .joblib file
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "intent_mlp_model.joblib"))

    # ── Telemetry & Pricing Settings (NEW) ────────────────────────────────────
    # Baseline pricing (per 1 Million tokens) used to calculate "Cost Saved"
    # Defaults are based on OpenAI's GPT-4o-mini pricing
    PRICE_PER_1M_INPUT_TOKENS: float = float(os.getenv("PRICE_PER_1M_INPUT_TOKENS", "0.150"))
    PRICE_PER_1M_OUTPUT_TOKENS: float = float(os.getenv("PRICE_PER_1M_OUTPUT_TOKENS", "0.600"))

    # ── RedisVL Schema Definition ──────────────────────────────────────────────
    # We define the RedisVL index structure declaratively here.
    CACHE_SCHEMA: dict = {
        "index": {
            "name": os.getenv("REDIS_INDEX_NAME", "query_cache_idx"),
            "prefix": os.getenv("REDIS_KEY_PREFIX", "cache"),
            "storage_type": "hash"
        },
        "fields": [
            {"name": "query", "type": "text"},
            {"name": "answer", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": VECTOR_DIMENSION,
                    "distance_metric": "cosine",
                    "algorithm": "hnsw",
                    "datatype": "float32"
                }
            }
        ]
    }

settings = Settings()