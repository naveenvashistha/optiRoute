import time
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from src.services.classifier import predict_intent
from src.services.cache import check_cache, save_to_cache
from src.services.router import evaluate_difficulty
from src.services.llm_client import call_local_llm, call_cloud_llm
from src.services.metrics import generate_telemetry_payload

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_PAYLOAD_CHARS = 20000

# ── Schemas ──
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_items=1)

class ChatResponse(BaseModel):
    answer: str
    telemetry: dict


def sanitize_and_truncate(messages: list[Message]) -> list[dict]:
    """
    Enforces silent sanitization, removes error loops, and protects the SLM context window.
    """
    clean_messages = []
    
    # 1. Role Enforcement & Error Loop Removal
    for m in messages:
        if m.role not in ["user", "assistant"]:
            continue
        # Drop previous timeout error strings so the AI doesn't read its own failures
        if m.role == "assistant" and m.content.startswith("Error: Local SLM"):
            continue
        clean_messages.append({"role": m.role, "content": m.content})

    if not clean_messages:
        raise HTTPException(status_code=400, detail="Payload contains no valid user/assistant messages.")

    # 2. Sequence Correction
    if clean_messages[-1]["role"] != "user":
        clean_messages.append({"role": "user", "content": "Please continue."})

    # 3. FIFO Flush (Drop oldest message pairs if over global cap)
    def get_total_chars(msgs):
        return sum(len(m["content"]) for m in msgs)

    while get_total_chars(clean_messages) > MAX_PAYLOAD_CHARS and len(clean_messages) >= 3:
        clean_messages.pop(0)  # Pop oldest user message
        if clean_messages and clean_messages[0]["role"] == "assistant":
            clean_messages.pop(0)  # Pop associated assistant message

    # 4. Single-Prompt Guillotine (Truncate from the top to keep the bottom question)
    if get_total_chars(clean_messages) > MAX_PAYLOAD_CHARS:
        excess = get_total_chars(clean_messages) - MAX_PAYLOAD_CHARS
        # Slices off the top of the final user message, retaining the bottom 20k characters
        clean_messages[-1]["content"] = clean_messages[-1]["content"][excess:]

    # 5. System Prompt Isolation (Hardcoded securely on the backend)
    clean_messages.insert(0, {
        "role": "system",
        "content": "You are a highly capable and concise software engineering assistant. Answer directly and accurately."
    })

    return clean_messages


@router.post("/ask", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    start_time = time.time()
    
    # Run payload through the failsafe sanitizer
    sanitized_messages = sanitize_and_truncate(request.messages)
    
    # Extract the active query (guaranteed to be a 'user' role by the sanitizer)
    user_query = sanitized_messages[-1]["content"].strip()
    logger.info(f"Processing sanitized query (Length: {len(user_query)} chars)")

    # Intent & Semantic Cache Check
    # Only cache if the payload contains exactly one System prompt and one User prompt
    is_single_turn = len(sanitized_messages) == 2
    intent = predict_intent(user_query) if is_single_turn else 0
    cachable = (intent == 1) and is_single_turn

    if cachable:
        cached_answer = check_cache(user_query)
        if cached_answer:
            telemetry = generate_telemetry_payload(
                start_time=start_time, end_time=time.time(),
                route="CACHE", intent=intent,
                user_query=user_query, final_answer=cached_answer
            )
            return ChatResponse(answer=cached_answer, telemetry=telemetry)

    # Router Difficulty Evaluation
    difficulty = evaluate_difficulty(user_query)

    # Route Execution
    if difficulty == 0:
        answer = await call_local_llm(sanitized_messages)
        route_taken = "LOCAL_SLM"
    else:
        answer = await call_cloud_llm(sanitized_messages)
        route_taken = "CLOUD"

    # Populate Cache
    if cachable and not answer.startswith("Error:"):
        save_to_cache(user_query, answer)

    # Generate Telemetry
    telemetry = generate_telemetry_payload(
        start_time=start_time,
        end_time=time.time(),
        route=route_taken,
        intent=intent,
        user_query=user_query,
        final_answer=answer
    )

    return ChatResponse(answer=answer, telemetry=telemetry)