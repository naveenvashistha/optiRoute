import logging
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# 1. Initialize FastEmbed Model
# This will download the BAAI/bge-small-en-v1.5 model the first time it runs 
# and load it into your local CPU memory for blazing-fast inference.
logger.info(f"Loading FastEmbed model: BAAI/bge-small-en-v1.5")
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_embedding(text: str) -> list[float]:
    """Helper function to convert text into a 384-dimension vector."""
    # FastEmbed returns a generator of numpy arrays, we want the first list of floats
    embeddings_generator = embedding_model.embed([text])
    first_embedding = next(embeddings_generator)
    return first_embedding.tolist()