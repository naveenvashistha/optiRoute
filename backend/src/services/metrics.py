# src/services/telemetry.py

import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Blazing fast token estimation heuristic.
    Roughly 1 word = 1.33 tokens for English text.
    """
    if not text:
        return 0
    # text.split() runs extremely fast in C underneath Python
    word_count = len(text.split())
    return int(word_count * 1.33)

def calculate_cost_saved(input_tokens: int, output_tokens: int) -> float:
    """
    Calculates the dollar amount saved based on the pricing in config.py.
    """
    input_cost = (input_tokens / 1_000_000) * settings.PRICE_PER_1M_INPUT_TOKENS
    output_cost = (output_tokens / 1_000_000) * settings.PRICE_PER_1M_OUTPUT_TOKENS
    
    return input_cost + output_cost

def generate_telemetry_payload(
    start_time: float, 
    end_time: float, 
    route: str, 
    intent: int, 
    user_query: str, 
    final_answer: str
) -> dict:
    """
    Assembles the final telemetry metadata to send back to the React frontend.
    
    Args:
        start_time: time.time() before the request started
        end_time: time.time() after the response was generated
        route: "CACHE", "LOCAL_SLM", or "CLOUD"
        intent: 0 (Cacheable) or 1 (Bypass)
    """
    try:
        # 1. Calculate time taken
        latency_ms = (end_time - start_time) * 1000
        
        # 2. Estimate tokens
        input_tokens = estimate_tokens(user_query)
        output_tokens = estimate_tokens(final_answer)
        total_tokens = input_tokens + output_tokens
        
        # 3. Calculate savings (We only save money if we didn't hit the Cloud!)
        if route in ["CACHE", "LOCAL_SLM"]:
            tokens_offloaded = total_tokens
            cost_saved_usd = calculate_cost_saved(input_tokens, output_tokens)
        else:
            tokens_offloaded = 0
            cost_saved_usd = 0.0
            
        # 4. Return the clean dictionary for the frontend
        return {
            "route": route,
            "latency_ms": round(latency_ms, 2),
            "tokens_offloaded": tokens_offloaded,
            "cost_saved_usd": round(cost_saved_usd, 6),
            "intent": intent
        }
        
    except Exception as e:
        logger.error(f"Error generating telemetry: {e}")
        # Safe fallback so the API never crashes due to telemetry math
        return {
            "route": route,
            "latency_ms": 0.0,
            "tokens_offloaded": 0,
            "cost_saved_usd": 0.0,
            "intent": intent
        }