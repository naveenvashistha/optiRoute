import logging
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from src.core.config import settings

logger = logging.getLogger(__name__)

logger.info(f"Loading DistilBERT Router from {settings.ROUTER_MODEL_PATH}...")
try:
    router_tokenizer = AutoTokenizer.from_pretrained(settings.ROUTER_MODEL_PATH)
    router_model = AutoModelForSequenceClassification.from_pretrained(settings.ROUTER_MODEL_PATH)
    router_model.eval()  # CPU inference mode
    logger.info("DistilBERT Router loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Router Model: {e}")
    raise e

def evaluate_difficulty(latest_query: str) -> int:
    """
    Evaluates prompt complexity:
        0: Simple -> Route to Local SLM
        1: Complex -> Route to Cloud LLM
    """
    try:
        inputs = router_tokenizer(
            latest_query,
            return_tensors="pt",
            truncation=True,
            max_length=256
        )
        
        with torch.no_grad():
            outputs = router_model(**inputs)
            
        logits = outputs.logits.detach().numpy()
        prediction = int(np.argmax(logits, axis=1).flatten()[0])
        
        route_label = "LOCAL_SLM" if prediction == 0 else "CLOUD_LLM"
        logger.info(f"DistilBERT classified query as {prediction} ({route_label})")
        return prediction

    except Exception as e:
        logger.error(f"Router evaluation failed: {e}")
        return 1  # Default to Cloud to ensure the user gets an answer