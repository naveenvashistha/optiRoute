import os
from dotenv import load_dotenv

# Load environment variables the moment this file is imported
load_dotenv()

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
    CACHE_THRESHOLD: float = float(os.getenv("CACHE_THRESHOLD", "0.10"))

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