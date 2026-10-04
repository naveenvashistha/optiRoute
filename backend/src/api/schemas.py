from pydantic import BaseModel, Field
from typing import Optional

class Message(BaseModel):
    """Pydantic schema representing a single conversation turn."""
    role: str
    content: str

class ChatRequest(BaseModel):
    """Pydantic schema for the incoming POST payload. Enforces at least 1 message."""
    messages: list[Message] = Field(..., min_items=1)
    edit_index: Optional[int] = None