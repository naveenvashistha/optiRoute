"""
Semantic Routing Service (DistilBERT)
=====================================
This module loads a fine-tuned DistilBERT sequence classification model 
to evaluate the complexity of incoming user queries. 
It acts as the traffic controller, deciding whether a prompt is simple enough
to be handled by the Local SLM (cost-saving) or complex enough to require 
the Cloud LLM (high capability).
"""

import logging
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from src.core.config import settings

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 ROUTER MODEL INITIALIZATION
# ==========================================
# We load the model at module import time so it stays resident in memory,
# preventing cold-start delays on every incoming chat request.
logger.info(f"Loading DistilBERT Router from {settings.ROUTER_MODEL_PATH}...")
try:
    router_tokenizer = AutoTokenizer.from_pretrained(settings.ROUTER_MODEL_PATH)
    router_model = AutoModelForSequenceClassification.from_pretrained(settings.ROUTER_MODEL_PATH)
    
    # Set to evaluation mode. Since this is a lightweight DistilBERT model, 
    # CPU inference is extremely fast and doesn't require a dedicated GPU.
    router_model.eval()  
    logger.info("DistilBERT Router loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Router Model: {e}")
    raise e


def evaluate_difficulty(latest_query: str) -> int:
    """
    Evaluates the semantic complexity of the user's prompt.

    Args:
        latest_query (str): The most recent user message.

    Returns:
        int: The routing decision.
             0: Simple query -> Route to Local SLM (e.g., Ollama/Groq)
             1: Complex query -> Route to Cloud LLM (e.g., Gemini/OpenAI)
    """
    try:
        # Tokenize the input text. We truncate to 256 tokens as most 
        # complexity markers (math formulas, deep technical jargon) appear early.
        inputs = router_tokenizer(
            latest_query,
            return_tensors="pt",
            truncation=True,
            max_length=256
        )
        
        # Disable gradient calculations for faster, memory-efficient inference
        with torch.no_grad():
            outputs = router_model(**inputs)
            
        # Convert raw logits to a numpy array and extract the predicted class (0 or 1)
        logits = outputs.logits.detach().numpy()
        prediction = int(np.argmax(logits, axis=1).flatten()[0])
        
        route_label = "LOCAL_SLM" if prediction == 0 else "CLOUD_LLM"
        logger.info(f"DistilBERT classified query as {prediction} ({route_label})")
        
        return prediction

    except Exception as e:
        # Failsafe: If the router crashes (e.g., out of memory, malformed input),
        # we default to the Cloud LLM (1) to guarantee the user receives a high-quality answer.
        logger.error(f"Router evaluation failed: {e}")
        return 1