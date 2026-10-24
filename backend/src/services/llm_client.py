"""
LLM Client Services Module
==========================
This module acts as the universal adapter for all Large Language Model communications.
It abstracts the complexities of streaming (Server-Sent Events), payload formatting,
and network resilience (exponential backoff) away from the main API router.

Supports:
- Local SLMs (Ollama)
- Cloud LLMs (OpenAI, Google Gemini, Groq)
"""

import os
import json
import logging
import asyncio
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv
from src.core.config import settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ==========================================
# 🔌 CLIENT INITIALIZATION
# ==========================================
# Initialize the standard OpenAI asynchronous client
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Groq utilizes an OpenAI-compatible API schema. By pointing the OpenAI SDK 
# at the Groq base URL, we can use standard OpenAI methods to call Groq models.
groq_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

async def call_local_llm_stream(messages: list[dict], max_retries: int = 3, max_tokens: int = 4096):
    """
    Streams the response from the Local SLM.
    Dynamically adapts between cloud-hosted Groq endpoints and local GPU Ollama 
    hardware based on the SLM_PROVIDER environment variable.
    """
    attempt = 0
    delay = 1.0

    while attempt < max_retries:
        yielded_any = False 
        
        try:
            if settings.SLM_PROVIDER == "groq":
                # --- GROQ TESTING LOGIC ---
                logger.info(f"Routing to Hosted SLM (Groq) (Attempt {attempt + 1}/{max_retries})...")
                response = await groq_client.chat.completions.create(
                    model="openai/gpt-oss-20b", 
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens, 
                    stream=True 
                )
                
                async for chunk in response:
                    if not chunk.choices:
                        continue
                        
                    choice = chunk.choices[0]
                    
                    if choice.finish_reason and choice.finish_reason not in ["stop", None]:
                        if not yielded_any:
                            yield {"error": f"SLM generation failed (Finish Reason: {choice.finish_reason})"}
                        return
                        
                    content = choice.delta.content
                    if content:
                        yielded_any = True
                        yield content
                        await asyncio.sleep(0.02)
                        
                if not yielded_any:
                    yield {"error": "SLM returned a successful connection but generated no text."}
                
                return  
                
            elif settings.SLM_PROVIDER == "ollama":
                # --- ORIGINAL OLLAMA LOGIC ---
                logger.info(f"Routing to Local SLM ({settings.LOCAL_MODEL_NAME}) (Attempt {attempt + 1})...")
                url = f"{settings.OLLAMA_BASE_URL}/api/chat"
                
                # We inject options > num_ctx so Ollama actually provisions the correct VRAM
                payload = {
                    "model": settings.LOCAL_MODEL_NAME, 
                    "messages": messages, 
                    "stream": True,
                    "options": {
                        "num_ctx": max_tokens 
                    }
                }
                
                async with httpx.AsyncClient(timeout=180.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yielded_any = True
                                    yield data["message"]["content"]
                                    
                return  

            else:
                # Catch-all for misconfigured .env files
                yield {"error": f"Invalid SLM_PROVIDER configured: '{settings.SLM_PROVIDER}'"}
                return

        except Exception as e:
            error_str = str(e).lower()

            if any(term in error_str for term in ["429", "rate_limit", "rate limit", "tpm"]):
                logger.warning(f"Groq Rate Limit encountered immediately: {str(e)}")
                yield {"error": f"Rate limit reached (429): {str(e)}"}
                return

            attempt += 1
            logger.warning(f"SLM Stream Error (Attempt {attempt}): {str(e)}")
            
            if yielded_any:
                logger.error("Stream dropped mid-generation.")
                yield {"error": f"The generation was interrupted. ({str(e)})"}
                return
                
            if attempt >= max_retries:
                logger.error("Max retries exhausted for SLM.")
                yield {"error": f"Local SLM failed after {max_retries} attempts. ({str(e)})"}
                return
                
            await asyncio.sleep(delay)
            delay *= 2

async def call_cloud_llm_stream(messages: list[dict], max_retries: int = 3, max_tokens: int = 4096):
    """
    Streams the response from the designated Cloud LLM (Gemini or OpenAI).
    Implements Tier 2 Horizontal Cloud Failover: automatically pivots to Groq 
    (openai/gpt-oss-120b) if the primary cloud provider fails.
    """
    attempt = 0
    delay = 1.0
    current_provider = settings.CLOUD_PROVIDER

    while attempt < max_retries:
        yielded_any = False
        
        try:
            if current_provider == "gemini":
                # --- GOOGLE GEMINI LOGIC (PRIMARY) ---
                model_name = "gemini-3.5-flash" 
                logger.info(f"Routing to Cloud LLM (Gemini - {model_name}) (Attempt {attempt + 1}/{max_retries})...")
                api_key = os.getenv("GEMINI_API_KEY")
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?key={api_key}&alt=sse"
                
                gemini_contents = []
                system_instruction = None
                
                for m in messages:
                    if m["role"] == "system":
                        system_instruction = {"parts": [{"text": m["content"]}]}
                    else:
                        role = "model" if m["role"] == "assistant" else "user"
                        gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})
                        
                payload = {"contents": gemini_contents}
                if system_instruction:
                    payload["systemInstruction"] = system_instruction

                async with httpx.AsyncClient(timeout=300.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status() # Raises Exception on 429/503 -> Triggers Groq Fallback
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]": 
                                    continue
                                
                                try:
                                    data = json.loads(data_str)
                                    
                                    if "promptFeedback" in data and "blockReason" in data["promptFeedback"]:
                                        reason = data["promptFeedback"]["blockReason"]
                                        raise Exception(f"Google API blocked the prompt (Reason: {reason})")
                                        
                                    candidates = data.get("candidates", [])
                                    if candidates:
                                        if "finishReason" in candidates[0] and candidates[0]["finishReason"] not in ["STOP", ""]:
                                            reason = candidates[0]["finishReason"]
                                            raise Exception(f"Google API refused generation (Finish Reason: {reason})")
                                            
                                        if "content" in candidates[0]:
                                            parts = candidates[0]["content"].get("parts", [])
                                            if parts and "text" in parts[0]:
                                                content = parts[0]["text"]
                                                if content:
                                                    yielded_any = True
                                                    yield content
                                except json.JSONDecodeError:
                                    pass 
                                    
                if not yielded_any:
                    raise Exception("Gemini connected successfully but generated no text.")
                return 
                
            elif current_provider == "groq":
                # --- GROQ LOGIC (TIER 2 HORIZONTAL FALLBACK) ---
                model_name = "openai/gpt-oss-120b"
                logger.info(f"Routing to Backup Cloud LLM (Groq - {model_name}) (Attempt {attempt + 1}/{max_retries})...")
                
                response = await groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                async for chunk in response:
                    if not chunk.choices:
                        continue
                        
                    choice = chunk.choices[0]
                    if choice.finish_reason and choice.finish_reason not in ["stop", None]:
                        raise Exception(f"Groq API refused generation (Finish Reason: {choice.finish_reason})")
                        
                    content = choice.delta.content
                    if content:
                        yielded_any = True
                        yield content
                        
                if not yielded_any:
                    raise Exception("Groq connected successfully but generated no text.")
                return

            else:
                # --- ORIGINAL OPENAI LOGIC (PRIMARY ALTERNATIVE) ---
                logger.info(f"Routing to Cloud LLM (OpenAI) (Attempt {attempt + 1}/{max_retries})...")
                
                response = await openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                    stream=True
                )
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        yielded_any = True
                        yield content
                        
                return 

        except Exception as e:
            attempt += 1
            logger.warning(f"Cloud LLM Stream Error ({current_provider.upper()}, Attempt {attempt}): {str(e)}")
            
            if yielded_any:
                logger.error("Cloud stream dropped mid-generation.")
                yield {"error": f"The cloud generation was interrupted. ({str(e)})"}
                return
                
            # TIER 2 HORIZONTAL CLOUD FAILOVER
            if current_provider in ["gemini", "openai"] and attempt < max_retries:
                logger.info("Initiating Tier 2 Horizontal Failover to Groq...")
                current_provider = "groq"
                continue
                
            if attempt >= max_retries:
                logger.error("Max retries exhausted for all Cloud LLMs.")
                yield {"error": f"All Cloud LLMs (Primary & Backup) failed after {max_retries} attempts. ({str(e)})"}
                return
                
            await asyncio.sleep(delay)
            delay *= 2