# src/core/db.py

import logging
import redis
from redisvl.index import SearchIndex
from src.core.config import settings

logger = logging.getLogger(__name__)

# 1. Instantiate the SearchIndex for Semantic Caching.
# RedisVL handles its own internal byte decoding for vector searches.
cache_index = SearchIndex.from_dict(
    settings.CACHE_SCHEMA, 
    redis_url=settings.REDIS_URL
)

# 2. Expose a raw, standard redis-py client for Session State Management.
# By setting decode_responses=True, Redis automatically converts the raw bytes 
# it stores into standard Python strings, eliminating the need to manually decode 
# UTF-8 every time we fetch a chat history.
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def init_redis():
    """
    Checks if the Redis vector index exists. 
    If not, creates it safely using the declarative schema.
    """
    try:
        cache_index.create(overwrite=False, drop=False)
        logger.info(f"RedisVL index '{cache_index.name}' is initialized and ready.")
        
        # Simple ping to ensure the standard key-value client is also connected
        redis_client.ping()
        logger.info("Standard Redis key-value client connected successfully.")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis database: {e}")
        raise e