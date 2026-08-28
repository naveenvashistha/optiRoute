import logging
import httpx
from openai import AsyncOpenAI
from src.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI Client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def call_local_llm(messages: list[dict]) -> str:
    """Sends the conversation history to the local Ollama SLM."""
    logger.info(f"Routing to Local SLM ({settings.LOCAL_MODEL_NAME})...")
    
    # Strip non-standard keys to prevent API validation errors
    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": settings.LOCAL_MODEL_NAME,
        "messages": clean_messages,
        "stream": False
    }
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Local SLM call failed: {e}")
        return "Error: Local SLM is currently unavailable."

async def call_cloud_llm(messages: list[dict]) -> str:
    """Sends the conversation history to the Cloud LLM."""
    logger.info(f"Routing to Cloud LLM ({settings.OPENAI_MODEL})...")
    
    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    
    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=clean_messages,
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Cloud LLM call failed: {e}")
        return "Error: Cloud LLM is currently unavailable."