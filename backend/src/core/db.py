# src/core/db.py

import logging
import redis
from redisvl.index import SearchIndex
from src.core.config import settings

logger = logging.getLogger(__name__)

# 1. Create a SINGLE shared Connection Pool
# This ensures all Redis operations use the same underlying TCP connections.
pool = redis.ConnectionPool.from_url(settings.REDIS_URL)

# 2. Instantiate the SearchIndex for Semantic Caching.
# We create a raw client WITHOUT decode_responses for RedisVL because 
# vector embeddings are stored and retrieved as raw bytes.
redis_raw = redis.Redis(connection_pool=pool)
cache_index = SearchIndex.from_dict(
    settings.CACHE_SCHEMA, 
    redis_client=redis_raw
)

# 2. Expose a raw, standard redis-py client for Session State Management.
# By setting decode_responses=True, Redis automatically converts the raw bytes 
# it stores into standard Python strings, eliminating the need to manually decode 
# UTF-8 every time we fetch a chat history.
redis_client = redis.Redis.from_url(connection_pool=pool, decode_responses=True)

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