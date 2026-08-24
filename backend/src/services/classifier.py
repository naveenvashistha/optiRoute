# src/services/classifier.py

import logging
import joblib
import numpy as np

from src.core.config import settings
from src.services.embedding import get_embedding

logger = logging.getLogger(__name__)

logger.info(f"Loading Intent Classifier from {settings.MODEL_PATH}")
try:
    classifier_model = joblib.load(settings.MODEL_PATH)
    logger.info("Intent Classifier loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load Intent Classifier: {e}")
    raise e

def predict_intent(user_query: str) -> int:
    """
    Embeds the user query and runs it through the neural network.
    Returns:
        0: Cacheable / Simple Query (Proceed to Semantic Cache)
        1: Complex Query (Bypass Cache, Route to SLM/Cloud)
    """
    try:
        # Step 1: Convert text to the 384-dimension vector
        vector = get_embedding(user_query)
        
        # Step 2: Reshape for scikit-learn
        # scikit-learn expects a 2D array for predictions, so we reshape our 1D vector to (1, 384)
        model_input = np.array(vector).reshape(1, -1)
        
        # Step 3: Get probabilities (just like your Jupyter notebook)
        # predict_proba returns an array of shape (1, 2) -> [[prob_class_0, prob_class_1]]
        probabilities = classifier_model.predict_proba(model_input)
        
        # Extract the probability for class 1 (index 1)
        prob_class_1 = probabilities[0][1]
        
        # Step 4: Apply your custom threshold
        # If prob >= threshold, it evaluates to True (1), else False (0)
        intent = int(prob_class_1 >= settings.INTENT_THRESHOLD)
        
        logger.info(f"Predicted intent '{intent}' (Prob: {prob_class_1:.3f}) for query: '{user_query}'")
        return intent
        
    except Exception as e:
        # Log the error and return a default intent (0 means bypass query) to avoid crashing the service and caching wrong query
        logger.error(f"Error predicting intent: {e}")
        return 0