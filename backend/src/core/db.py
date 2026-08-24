# src/core/redis_db.py

import logging
from redisvl.index import SearchIndex
from src.core.config import settings

logger = logging.getLogger(__name__)

# 1. Instantiate the SearchIndex using our centralized declarative schema.
# By passing the redis_url here, RedisVL automatically handles the low-level 
# redis-py connection pooling and byte decoding for us.
cache_index = SearchIndex.from_dict(
    settings.CACHE_SCHEMA, 
    redis_url=settings.REDIS_URL
)

def init_redis():
    """
    Checks if the Redis vector index exists. 
    If not, creates it safely using the declarative schema.
    """
    try:
        # overwrite=False ensures that if you restart your server, 
        # it doesn't accidentally wipe out your existing cached queries!
        cache_index.create(overwrite=False, drop=False)
        logger.info(f"RedisVL index '{cache_index.name}' is initialized and ready.")
        
    except Exception as e:
        logger.error(f"Failed to initialize RedisVL index: {e}")
        raise e