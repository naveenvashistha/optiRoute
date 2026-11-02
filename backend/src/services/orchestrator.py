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
from src.core.config import settings

from src.services.classifier import predict_intent
from src.services.cache import check_cache, save_to_cache
from src.services.router import evaluate_difficulty
from src.services.metrics import generate_telemetry_payload
from src.core.state import sync_session_state, update_global_state, append_assistant_response
from src.services.context_manager import sanitize_and_truncate, estimate_tokens
from src.api.schemas import ChatRequest

logger = logging.getLogger(__name__)

async def process_chat_stream(request: ChatRequest):
    """
    Master orchestrator generator for streaming chat completions.
    Handles network routing, caching, dynamic token budgeting, and reactive fallbacks.
    Returns a Python generator to stream Server-Sent Events (SSE) to the frontend React UI.
    """
    start_time = time.time()
    session_id = request.session_id
    
    # --- PRE-TRUNCATION STATE EXTRACTION ---
    try:
        # Fetch or initialize the user's conversation history from Redis
        current_history = sync_session_state(session_id, request.messages, request.edit_index)
    except RuntimeError as e:
        # If Redis is offline, gracefully return the error down the open SSE pipe.
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return
    
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
    # Global memory stores up to 8,000 tokens in Redis to optimize network bandwidth.
    MAX_GLOBAL_MEMORY = 8000
    global_history, _ = sanitize_and_truncate(current_history, max_input_tokens=MAX_GLOBAL_MEMORY)
    
    try:
        # Overwrite Redis with the safely truncated 8,000 token limit
        update_global_state(session_id, global_history)
    except RuntimeError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    # --- TPM-AWARE DYNAMIC BUDGETING ---
    if difficulty == 0:
        budget_limit = settings.OLLAMA_NUM_CTX if settings.SLM_PROVIDER == "ollama" else 4000
    else:
        budget_limit = 7000
        
    raw_global_tokens = sum(estimate_tokens(m.get("content", "")) for m in global_history)
    llm_payload_history, safe_max_tokens = sanitize_and_truncate(global_history, max_input_tokens=budget_limit)

    route_taken = "LOCAL_SLM" if difficulty == 0 else "CLOUD"

    # --- PRE-FLIGHT ESCALATION CHECK ---
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
            "You are OptiRoute, an advanced conversational AI assistant. "
            "CRITICAL INSTRUCTION: Your name refers to 'routing AI queries' between different language models (SLMs and LLMs) to optimize computational speed and cost. "
            "You have absolutely nothing to do with physical travel, logistics, maps, GPS, or vehicle routing. Never introduce yourself as a travel or logistics assistant. "
            "CRITICAL INSTRUCTION: Never identify yourself as ChatGPT, an OpenAI product, or a large language model created by another company. "
            "Provide highly accurate, well-formatted responses using Markdown. "
            "If you give a table, list, code block always leave a hard blank line before and after tables, lists, and code blocks to ensure proper rendering. "
            "CRITICAL INSTRUCTION: Never attempt to include external image links. If a visual is requested, rely strictly on LaTeX, Markdown tables, or ASCII art. "
            "CRITICAL INSTRUCTION: Never use Markdown bullet points (* or -) inside table cells. If you need to list items inside a table, use the HTML <br> tag for line breaks and a literal bullet character (•) instead. "
            "If the user asks an open-ended, analytical, creative, or educational query, "
            "you MUST conclude your response with a single, specific follow-up question to encourage further conversation."
        )
    }

    def build_payload(history: list[dict]) -> list[dict]:
        payload = list(history)
        payload.insert(0, system_instruction)
        return payload

    llm_payload = build_payload(llm_payload_history)
    
    full_answer = ""
    
    # 1. Semantic Cache Hit
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
                    
                    is_token_or_rate_error = any(
                        term in error_msg 
                        for term in ["length", "too large", "rate_limit", "429", "tpm", "tokens per minute", "context window"]
                    )
                    
                    if is_token_or_rate_error and not full_answer:
                        logger.warning("SLM rate/context limit reached. Triggering cloud fallback.")
                        need_fallback = True
                        break 
                        
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                    return 
                    
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                full_answer += chunk
                
            if need_fallback:
                difficulty = 1 
                route_taken = "CLOUD_FALLBACK"
                llm_payload_history, safe_max_tokens = sanitize_and_truncate(global_history, max_input_tokens=7000)
                llm_payload = build_payload(llm_payload_history)

        # Cloud execution path
        if difficulty == 1:
            if route_taken != "CLOUD_FALLBACK":
                route_taken = "CLOUD"
                
            from src.services.llm_client import call_cloud_llm_stream
            cloud_failed_cleanly = False
            
            async for chunk in call_cloud_llm_stream(llm_payload, max_tokens=safe_max_tokens):
                if isinstance(chunk, dict) and "error" in chunk:
                    if full_answer:
                        yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                        return
                    else:
                        logger.warning("All Cloud APIs failed. Intercepting error for Tier 3 SLM Fallback...")
                        cloud_failed_cleanly = True
                        break
                        
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                full_answer += chunk

            # --- TIER 3: VERTICAL SLM DEGRADATION ---
            if cloud_failed_cleanly:
                SLM_BUDGET = settings.OLLAMA_NUM_CTX if settings.SLM_PROVIDER == "ollama" else 4000
                current_query_tokens = estimate_tokens(user_query)
                
                if current_query_tokens > SLM_BUDGET:
                    logger.error(f"Tier 3 Fallback aborted: Single prompt ({current_query_tokens} tokens) exceeds local SLM limit.")
                    yield f"data: {json.dumps({'error': 'The network is currently unavailable, try again later.'})}\n\n"
                    return

                logger.info("Executing Tier 3 Context Pruning for Emergency SLM Fallback...")
                fallback_history, safe_slm_tokens = sanitize_and_truncate(global_history, max_input_tokens=SLM_BUDGET)
                fallback_payload = build_payload(fallback_history)
                route_taken = "SLM_EMERGENCY_FALLBACK"

                from src.services.llm_client import call_local_llm_stream
                
                async for chunk in call_local_llm_stream(fallback_payload, max_tokens=safe_slm_tokens):
                    if isinstance(chunk, dict) and "error" in chunk:
                        yield f"data: {json.dumps({'error': 'The network is currently unavailable, try again later.'})}\n\n"
                        return
                        
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    full_answer += chunk

    if cachable and full_answer:
        save_to_cache(user_query, full_answer)

    # 3. Save AI response to Global State
    append_assistant_response(session_id, full_answer)

    # 4. Append Telemetry payload
    telemetry = generate_telemetry_payload(
        start_time=start_time, 
        end_time=time.time(),
        route=route_taken, 
        intent=intent,
        user_query=user_query, 
        final_answer=full_answer,
    )
    yield f"data: {json.dumps({'telemetry': telemetry})}\n\n"
