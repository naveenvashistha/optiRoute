import logging

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 VOLATILE OS MEMORY STATE (Incognito Mode)
# ==========================================
GLOBAL_CONVERSATION_HISTORY = []

def clear_session_state():
    """Resets the backend memory."""
    global GLOBAL_CONVERSATION_HISTORY
    GLOBAL_CONVERSATION_HISTORY.clear()
    logger.info("Session refreshed: Backend conversation history cleared.")

def sync_session_state(messages: list, edit_index: int = None) -> list:
    """Synchronizes frontend arrays with the global backend memory using O(1) index slicing."""
    global GLOBAL_CONVERSATION_HISTORY
    
    if edit_index is not None:
        # Fast state mutation: Slice at the exact edit point and append the new message
        GLOBAL_CONVERSATION_HISTORY = GLOBAL_CONVERSATION_HISTORY[:edit_index]
        GLOBAL_CONVERSATION_HISTORY.append({"role": "user", "content": messages[-1].content})
        logger.info(f"State mutated at index {edit_index}. History truncated.")
    elif len(messages) > 1 or not GLOBAL_CONVERSATION_HISTORY:
        # Fallback full sync
        GLOBAL_CONVERSATION_HISTORY = [{"role": m.role, "content": m.content} for m in messages]
    else:
        # Standard append for normal conversation flow
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