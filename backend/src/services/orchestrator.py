"""
Orchestrator Module
===================
Master pipeline for routing, caching, dynamic token budgeting, and fallback management.
Optimized for Groq gpt-oss-20b (8K TPM tier).
"""

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
    Master orchestrator generator for streaming chat completions.
    Handles network routing, caching, dynamic token budgeting, and reactive fallbacks.
    Returns a Python generator to stream Server-Sent Events (SSE) to the frontend React UI.
    """
    start_time = time.time()
    
    # --- PRE-TRUNCATION STATE EXTRACTION ---
    current_history = sync_session_state(request.messages, request.edit_index)
    
    # Validation: We must yield JSON errors instead of raising HTTPExceptions 
    # to prevent FastAPI from crashing an already-open 200 OK SSE connection.
    if not current_history:
        yield f"data: {json.dumps({'error': 'Payload contains no valid messages.'})}\n\n"
        return
        
    user_query = current_history[-1].get("content", "").strip()

    if not user_query:
        yield f"data: {json.dumps({'error': 'User query cannot be empty or whitespace.'})}\n\n"
        return

    # --- PIPELINE CLASSIFICATION ---
    intent = predict_intent(user_query)
    cachable = (intent == 1)
    difficulty = evaluate_difficulty(user_query)
    
    # --- DECOUPLE GLOBAL MEMORY FROM PAYLOAD BUDGET ---
    # Global memory stores up to 8,000 tokens in RAM to optimize network bandwidth.
    # The SLM only receives a truncated 4K window from this 8K master history.
    MAX_GLOBAL_MEMORY = 8000
    global_history, _ = sanitize_and_truncate(current_history, max_input_tokens=MAX_GLOBAL_MEMORY)
    update_global_state(global_history)

    # --- TPM-AWARE DYNAMIC BUDGETING ---
    # We restrict the SLM to 4,000 tokens. This guarantees a rich context window while 
    # mathematically preventing the generation from exceeding Groq's strict 8,000 TPM limit.
    budget_limit = 4000 if difficulty == 0 else 7000

    from src.services.context_manager import estimate_tokens
    # Calculate the raw token count of the global history BEFORE applying the strict budget limits.
    raw_global_tokens = sum(estimate_tokens(m.get("content", "")) for m in global_history)

    llm_payload_history, safe_max_tokens = sanitize_and_truncate(global_history, max_input_tokens=budget_limit)

    route_taken = "LOCAL_SLM" if difficulty == 0 else "CLOUD"

    # --- PRE-FLIGHT ESCALATION CHECK ---
    # Protection against "Catastrophic Amnesia". If the history is massively larger than the 
    # SLM budget, escalating to Cloud is mandatory to prevent the context manager from 
    # aggressively deleting conversational history to make it fit.
    if difficulty == 0 and raw_global_tokens > budget_limit:
        logger.warning(f"Context history ({raw_global_tokens} tokens) exceeds SLM {budget_limit}-token budget. Pre-flight escalating to Cloud LLM.")
        difficulty = 1
        route_taken = "CLOUD_FALLBACK"
        budget_limit = 7000
        llm_payload_history, safe_max_tokens = sanitize_and_truncate(global_history, max_input_tokens=budget_limit)

    # --- SYSTEM INSTRUCTION INJECTION ---
    system_instruction = {
        "role": "system",
        "content": (
            "You are an expert AI assistant connected through the OptiRoute Gateway. "
            "Provide highly accurate, well-formatted responses using Markdown. "
            "Whenever you give a table, list, code block always leave a hard blank line before and after tables, lists, and code blocks to ensure proper rendering. "
            "CRITICAL INSTRUCTION: Never attempt to include external image links (e.g., Imgur, Wikipedia). If a visual is requested, rely strictly on LaTeX, Markdown tables, or ASCII art. "
            "If the user asks an open-ended, analytical, creative, or educational query, "
            "you MUST conclude your response with a single, specific follow-up question but don't explicitly write 'follow-up question' "
            "to encourage further conversation."
        )
    }

    def build_payload(history: list[dict]) -> list[dict]:
        payload = list(history)
        payload.insert(0, system_instruction)
        return payload

    llm_payload = build_payload(llm_payload_history)
    
    # --- DEBUG: LOG FINAL PAYLOAD ---
    # logger.info("FINAL LLM PAYLOAD:")
    # logger.info(json.dumps(llm_payload, indent=2))
    
    full_answer = ""
    
    # 1. Semantic Cache Hit
    # Intercept queries mathematically identical to previous highly-complex (Intent 1) prompts.
    # Bypasses the network API entirely, drastically reducing cost and latency.
    if cachable:
        cached_answer = check_cache(user_query)
        if cached_answer:
            yield f"data: {json.dumps({'chunk': cached_answer})}\n\n"
            full_answer = cached_answer
            route_taken = "CACHE"
    
    # 2. Live Generation
    if not full_answer:
        if difficulty == 0:
            from src.services.llm_client import call_local_llm_stream
            
            need_fallback = False
            async for chunk in call_local_llm_stream(llm_payload, max_tokens=safe_max_tokens):
                if isinstance(chunk, dict) and "error" in chunk:
                    error_msg = chunk["error"].lower()
                    
                    # --- REACTIVE FALLBACK (Silent 429 Error Handling) ---
                    # If Groq throttles the request due to rapid subsequent requests (Tokens/Min limit),
                    # we absorb the error mid-stream, abort the generation, and flag for a silent 
                    # handoff to the Cloud LLM so the UI does not break.
                    is_token_or_rate_error = any(
                        term in error_msg 
                        for term in ["length", "too large", "rate_limit", "429", "tpm", "tokens per minute", "context window"]
                    )
                    
                    if is_token_or_rate_error and not full_answer:
                        logger.warning(f"SLM Rate/Context limit reached ({chunk['error']}). Triggering silent Cloud Fallback.")
                        need_fallback = True
                        break 
                        
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    return 
                    
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                full_answer += chunk
                
            if need_fallback:
                difficulty = 1 
                route_taken = "CLOUD_FALLBACK"
                # The SLM failed. Expand the payload back up to the Cloud LLM's larger memory capacity.
                llm_payload_history, safe_max_tokens = sanitize_and_truncate(global_history, max_input_tokens=7000)
                llm_payload = build_payload(llm_payload_history)

        # Cloud execution path (Handles direct routing, Pre-Flight Context Escapes, or 429 Reactive Fallbacks)
        if difficulty == 1:
            if route_taken != "CLOUD_FALLBACK":
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
    # Ensures the React frontend receives execution metrics to render on the dashboard UI.
    telemetry = generate_telemetry_payload(
        start_time=start_time, end_time=time.time(),
        route=route_taken, intent=intent,
        user_query=user_query, final_answer=full_answer
    )
    yield f"data: {json.dumps({'telemetry': telemetry})}\n\n"