"""
Chat API Router Module
======================
Handles the core conversational endpoint and orchestrates the Server-Sent Events stream.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatRequest
from src.core.state import clear_session_state
from src.services.orchestrator import process_chat_stream

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/clear")
async def clear_history():
    """
    Resets the backend memory when the frontend browser tab is refreshed.
    Triggered by the React `useEffect` mount hook.
    """
    clear_session_state()
    return {"status": "cleared"}

@router.post("/ask")
async def chat_endpoint(request: ChatRequest):
    """
    The primary gateway endpoint for streaming chat completions.
    Delegates all routing, caching, and stream processing to the orchestrator.
    """
    return StreamingResponse(process_chat_stream(request), media_type="text/event-stream")