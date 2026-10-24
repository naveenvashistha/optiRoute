"""
Chat API Router Module
======================
Handles the core conversational endpoint and orchestrates the Server-Sent Events stream.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatRequest
from src.services.orchestrator import process_chat_stream

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ask")
async def chat_endpoint(request: ChatRequest):
    """
    The primary gateway endpoint for streaming chat completions.
    Delegates all routing, caching, and stream processing to the orchestrator.
    Requires a valid session_id from the frontend to manage stateless Redis history.
    """
    return StreamingResponse(process_chat_stream(request), media_type="text/event-stream")