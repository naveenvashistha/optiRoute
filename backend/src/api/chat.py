"""
Chat API Router Module
======================
Handles the core conversational endpoint, ephemeral state management, 
payload sanitization, and routing logic (Local SLM vs Cloud LLM).

Architecture Note: 
This module intentionally uses volatile OS process memory (a global list) 
instead of a Database Management System (DBMS) to achieve an "incognito" 
ephemeral session state, fulfilling the strict single-user lab requirements.
"""

import time
import logging
import json
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from src.services.classifier import predict_intent
from src.services.cache import check_cache, save_to_cache
from src.services.router import evaluate_difficulty
from src.services.metrics import generate_telemetry_payload

logger = logging.getLogger(__name__)
router = APIRouter()

# Maximum character limit for the LLM context window to prevent Out-Of-Memory (OOM) errors
MAX_PAYLOAD_CHARS = 20000

# ==========================================
# 🧠 VOLATILE OS MEMORY STATE (Incognito Mode)
# ==========================================
# Acts as our ephemeral database. Exists only as long as the FastAPI worker is alive.
GLOBAL_CONVERSATION_HISTORY = []


# ── Schemas ──
class Message(BaseModel):
    """Pydantic schema representing a single conversation turn."""
    role: str
    content: str

class ChatRequest(BaseModel):
    """Pydantic schema for the incoming POST payload. Enforces at least 1 message."""
    messages: list[Message] = Field(..., min_items=1)


@router.post("/clear")
async def clear_history():
    """
    Resets the backend memory when the frontend browser tab is refreshed.
    Triggered by the React `useEffect` mount hook.
    """
    global GLOBAL_CONVERSATION_HISTORY
    GLOBAL_CONVERSATION_HISTORY.clear()
    logger.info("Session refreshed: Backend conversation history cleared.")
    return {"status": "cleared"}


def sanitize_and_truncate(messages: list[dict]) -> list[dict]:
    """
    Enforces silent sanitization, removes error loops, and protects the context window.
    Operates entirely on standard Python dicts stored in the global memory.

    Args:
        messages (list[dict]): The raw conversation history.

    Returns:
        list[dict]: A clean, token-safe conversation history ready for the LLM.
    """
    clean_messages = []
    
    # 1. Role Enforcement & Error Loop Removal
    # Strips out any accidental internal metadata and prevents the AI from reading 
    # its own network failure messages (which causes hallucination loops).
    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role not in ["user", "assistant"]:
            continue
        if role == "assistant" and content.startswith("Error:"):
            continue
        clean_messages.append({"role": role, "content": content})

    if not clean_messages:
        return []

    # 2. Sequence Correction
    # LLMs require the final prompt to be from a 'user'. If history manipulation 
    # leaves an 'assistant' message at the bottom, we append a generic prompt.
    if clean_messages[-1]["role"] != "user":
        clean_messages.append({"role": "user", "content": "Please continue."})

    # 3. FIFO Flush (First-In, First-Out)
    # If the conversation exceeds the character cap, we drop the oldest Q&A pairs 
    # to protect the context window while maintaining recent context.
    def get_total_chars(msgs):
        return sum(len(m["content"]) for m in msgs)

    while get_total_chars(clean_messages) > MAX_PAYLOAD_CHARS and len(clean_messages) >= 3:
        clean_messages.pop(0)  # Pop oldest user message
        if clean_messages and clean_messages[0]["role"] == "assistant":
            clean_messages.pop(0)  # Pop associated assistant message

    # 4. Single-Prompt Guillotine
    # If a single user prompt is overwhelmingly massive (e.g., pasting a whole codebase),
    # we slice off the top of the prompt to keep the end of it (where the actual question usually is).
    if get_total_chars(clean_messages) > MAX_PAYLOAD_CHARS:
        excess = get_total_chars(clean_messages) - MAX_PAYLOAD_CHARS
        clean_messages[-1]["content"] = clean_messages[-1]["content"][excess:]

    return clean_messages


@router.post("/ask")
async def chat_endpoint(request: ChatRequest):
    """
    The primary gateway endpoint for streaming chat completions.
    Handles state synchronization, dynamic routing, caching, and Server-Sent Events (SSE).
    """
    global GLOBAL_CONVERSATION_HISTORY
    start_time = time.time()
    
    # --- SMART STATE SYNCHRONIZATION ---
    # Network Optimization: The frontend normally only sends the single newest message.
    # However, if the user edits history, the frontend sends the whole sliced array.
    # We detect this divergence and overwrite the global state when necessary.
    if len(request.messages) > 1 or not GLOBAL_CONVERSATION_HISTORY:
        GLOBAL_CONVERSATION_HISTORY = [{"role": m.role, "content": m.content} for m in request.messages]
    else:
        GLOBAL_CONVERSATION_HISTORY.append({"role": "user", "content": request.messages[0].content})

    # Sanitize the global memory array
    GLOBAL_CONVERSATION_HISTORY = sanitize_and_truncate(GLOBAL_CONVERSATION_HISTORY)
    
    if not GLOBAL_CONVERSATION_HISTORY:
        raise HTTPException(status_code=400, detail="Payload contains no valid messages.")

    # Create a temporary payload for the LLM that includes the System Instruction.
    # We use list() to create a shallow copy so we don't pollute the actual history state.
    llm_payload = list(GLOBAL_CONVERSATION_HISTORY)
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
    is_single_turn = len(GLOBAL_CONVERSATION_HISTORY) == 1
    intent = predict_intent(user_query) if is_single_turn else 0
    cachable = (intent == 1) and is_single_turn
    difficulty = evaluate_difficulty(user_query)

    # --- ASYNC GENERATOR (Server-Sent Events) ---
    async def event_generator():
        full_answer = ""
        route_taken = "LOCAL_SLM"
        
        # 1. Semantic Cache Hit (Fast path)
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
                
                async for chunk in call_local_llm_stream(llm_payload):
                    # Intercept backend errors and broadcast them on a dedicated JSON key for the frontend Toast
                    if isinstance(chunk, dict) and "error" in chunk:
                        yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                        break
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    full_answer += chunk
            else:
                route_taken = "CLOUD"
                from src.services.llm_client import call_cloud_llm_stream
                
                async for chunk in call_cloud_llm_stream(llm_payload):
                    # Intercept backend errors and broadcast them on a dedicated JSON key for the frontend Toast
                    if isinstance(chunk, dict) and "error" in chunk:
                        yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                        break
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    full_answer += chunk

            # Populate the semantic cache on successful completion
            if cachable and full_answer:
                save_to_cache(user_query, full_answer)

        # 3. Save AI response to Global State
        # If the string is empty, it means the network failed immediately, so we don't save it.
        if full_answer:
            GLOBAL_CONVERSATION_HISTORY.append({"role": "assistant", "content": full_answer})

        # 4. Append Telemetry payload at the very end of the stream
        telemetry = generate_telemetry_payload(
            start_time=start_time, end_time=time.time(),
            route=route_taken, intent=intent,
            user_query=user_query, final_answer=full_answer
        )
        yield f"data: {json.dumps({'telemetry': telemetry})}\n\n"

    # Return the stream with the specific media type required for SSE
    return StreamingResponse(event_generator(), media_type="text/event-stream")