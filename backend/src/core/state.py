import logging

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 VOLATILE OS MEMORY STATE (Incognito Mode)
# ==========================================
# Acts as our ephemeral database. Exists only as long as the FastAPI worker is alive.
GLOBAL_CONVERSATION_HISTORY = []

def clear_session_state():
    """Resets the backend memory."""
    global GLOBAL_CONVERSATION_HISTORY
    GLOBAL_CONVERSATION_HISTORY.clear()
    logger.info("Session refreshed: Backend conversation history cleared.")

def sync_session_state(messages: list) -> list:
    """Synchronizes frontend array slices with the global backend memory."""
    global GLOBAL_CONVERSATION_HISTORY
    if len(messages) > 1 or not GLOBAL_CONVERSATION_HISTORY:
        GLOBAL_CONVERSATION_HISTORY = [{"role": m.role, "content": m.content} for m in messages]
    else:
        GLOBAL_CONVERSATION_HISTORY.append({"role": "user", "content": messages[0].content})
    return GLOBAL_CONVERSATION_HISTORY

def update_global_state(new_history: list):
    """Updates the global state after sanitization."""
    global GLOBAL_CONVERSATION_HISTORY
    GLOBAL_CONVERSATION_HISTORY = new_history

def append_assistant_response(content: str):
    """Saves the AI's response to the global state."""
    global GLOBAL_CONVERSATION_HISTORY
    if content:
        GLOBAL_CONVERSATION_HISTORY.append({"role": "assistant", "content": content})