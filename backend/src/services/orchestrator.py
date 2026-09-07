import time
import json
import logging
from fastapi import HTTPException

from src.services.classifier import predict_intent
from src.services.cache import check_cache, save_to_cache
from src.services.router import evaluate_difficulty
from src.services.metrics import generate_telemetry_payload
from src.core.state import sync_session_state, update_global_state, append_assistant_response
from src.services.context_manager import sanitize_and_truncate
from src.api.schemas import ChatRequest

logger = logging.getLogger(__name__)

async def process_chat_stream(request: ChatRequest):
    """
    The master orchestrator generator for streaming chat completions.
    Handles network routing, caching, proactive overrides, and reactive fallbacks.
    """
    start_time = time.time()
    
    # --- SMART STATE SYNCHRONIZATION ---
    current_history = sync_session_state(request.messages)
    clean_history, safe_max_tokens = sanitize_and_truncate(current_history)
    update_global_state(clean_history)
    
    if not clean_history:
        raise HTTPException(status_code=400, detail="Payload contains no valid messages.")

    llm_payload = list(clean_history)
    system_instruction = {
        "role": "system",
        "content": (
            "You are an expert AI assistant connected through the OptiRoute Gateway. "
            "Provide highly accurate, well-formatted responses using Markdown. "
            "Always leave a hard blank line before and after tables, lists, and code blocks to ensure proper rendering. "
            "CRITICAL INSTRUCTION: If the user asks an open-ended, analytical, creative, or educational query, "
            "you MUST conclude your response with a single, specific follow-up question but don't explicitly write 'follow-up question' "
            "to encourage further conversation."
        )
    }
    llm_payload.insert(0, system_instruction)

    user_query = llm_payload[-1]["content"].strip()
    
    # --- PIPELINE CLASSIFICATION ---
    intent = predict_intent(user_query)
    cachable = (intent == 1)
    difficulty = evaluate_difficulty(user_query)

    # --- PHASE 1: PROACTIVE OVERRIDE ---
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)
        
    total_payload_tokens = sum(estimate_tokens(m["content"]) for m in llm_payload)
    if total_payload_tokens > 1500:
        difficulty = 1
        logger.info(f"Payload ({total_payload_tokens} tokens) exceeded SLM threshold. Forcing Cloud LLM.")

    full_answer = ""
    route_taken = "LOCAL_SLM"
    
    # 1. Semantic Cache Hit
    if cachable:
        cached_answer = check_cache(user_query)
        if cached_answer:
            yield f"data: {json.dumps({'chunk': cached_answer})}\n\n"
            full_answer = cached_answer
            route_taken = "CACHE"
    
    # 2. Live Generation (Routing path)
    if not full_answer:
        if difficulty == 0:
            route_taken = "LOCAL_SLM"
            from src.services.llm_client import call_local_llm_stream
            
            need_fallback = False
            async for chunk in call_local_llm_stream(llm_payload, max_tokens=safe_max_tokens):
                if isinstance(chunk, dict) and "error" in chunk:
                    error_msg = chunk["error"].lower()
                    
                    # --- PHASE 2: REACTIVE FALLBACK ---
                    is_token_error = any(term in error_msg for term in ["length", "too large", "rate_limit_exceeded", "context window"])
                    if is_token_error and not full_answer:
                        logger.info("SLM hit token limits. Initiating silent fallback to Cloud LLM.")
                        need_fallback = True
                        break 
                        
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    return 
                    
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                full_answer += chunk
                
            if need_fallback:
                difficulty = 1 
                
        # Cloud block executes either from DistilBERT, Proactive Override, or Reactive Fallback
        if difficulty == 1:
            if route_taken == "LOCAL_SLM":
                route_taken = "CLOUD_FALLBACK" 
            else:
                route_taken = "CLOUD"
                
            from src.services.llm_client import call_cloud_llm_stream
            
            async for chunk in call_cloud_llm_stream(llm_payload, max_tokens=safe_max_tokens):
                if isinstance(chunk, dict) and "error" in chunk:
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    return
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                full_answer += chunk

        if cachable and full_answer:
            save_to_cache(user_query, full_answer)

    # 3. Save AI response to Global State
    append_assistant_response(full_answer)

    # 4. Append Telemetry payload
    telemetry = generate_telemetry_payload(
        start_time=start_time, end_time=time.time(),
        route=route_taken, intent=intent,
        user_query=user_query, final_answer=full_answer
    )
    yield f"data: {json.dumps({'telemetry': telemetry})}\n\n"