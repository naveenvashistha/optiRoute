import logging
from redisvl.query import VectorQuery
from src.services.embedding import get_embedding
from src.core.config import settings
from src.core.db import cache_index

logger = logging.getLogger(__name__)


def check_cache(user_query: str) -> str | None:
    """
    Searches Redis for a semantically similar query.
    Returns the cached answer if found above the threshold, else None.
    """
    try:
        query_vector = get_embedding(user_query)
        
        # Build a RedisVL VectorQuery
        # We ask it to return exactly 1 result (num_results=1) based on our vector
        v_query = VectorQuery(
            vector=query_vector,
            vector_field_name="embedding",
            return_fields=["query", "answer", "vector_distance"],
            num_results=1
        )
        
        # Execute the search against our Redis cache
        results = cache_index.query(v_query)
        
        if not results:
            return None
            
        # RedisVL returns results as a list of dictionaries. Get the top match.
        best_match = results[0]
        distance = float(best_match["vector_distance"])
        
        # If the distance is smaller than our allowed threshold (e.g., < 0.10 for 90% similarity)
        if distance <= settings.SIMILARITY_THRESHOLD:
            logger.info(f"Cache HIT! Matched with distance: {distance}")
            return best_match["answer"]
            
        logger.info(f"Cache MISS. Closest match was too far (distance: {distance})")
        return None

    except Exception as e:
        logger.error(f"Error querying semantic cache: {e}")
        return None

def save_to_cache(user_query: str, answer: str):
    """
    Embeds a new query and saves the query, answer, and vector to RedisVL.
    """
    try:
        query_vector = get_embedding(user_query)
        
        # RedisVL's load() method takes a list of dictionaries to insert
        record = {
            "query": user_query,
            "answer": answer,
            "embedding": query_vector
        }
        
        # We use a custom TTL for the keys during insertion
        cache_index.load([record], ttl=settings.CACHE_TTL)
        logger.info(f"Successfully cached query: '{user_query}'")
        
    except Exception as e:
        logger.error(f"Error saving to semantic cache: {e}")