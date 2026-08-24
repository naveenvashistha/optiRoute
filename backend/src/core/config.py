import os
from dotenv import load_dotenv

# Load environment variables the moment this file is imported
load_dotenv()

class Settings:
    # Qdrant Database Configuration
    # We default to a local folder so your vectors are saved to disk between server restarts.
    QDRANT_STORAGE_PATH: str = os.getenv("QDRANT_STORAGE_PATH", "./qdrant_data")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "query_cache")
    
    # Embedding Configuration
    # BAAI/bge-small-en-v1.5 explicitly outputs 384-dimensional vectors.
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "384"))
    
    # Semantic Search Threshold
    # Any distance above this number is considered a Cache Hit (e.g., 90% similar)
    CACHE_THRESHOLD: float = float(os.getenv("CACHE_THRESHOLD", "0.90"))

settings = Settings()