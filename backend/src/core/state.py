# src/core/state.py

import json
import logging
from src.core.db import redis_client
from src.core.config import settings

logger = logging.getLogger(__name__)

# The volatile GLOBAL_CONVERSATION_HISTORY list has been permanently deleted.
# State is now 100% managed via external Redis keys.

def sync_session_state(session_id: str, messages: list, edit_index: int = None) -> list:
    """
    Fetches the session history from Redis, applies frontend mutations (append or slice),
    and saves the updated state back to Redis with a rolling TTL.
    """
    redis_key = f"session:{session_id}"
    
    try:
        # 1. Fetch and Deserialize
        # If the key doesn't exist (e.g., brand new session or TTL expired), initialize an empty list.
        history_json = redis_client.get(redis_key)
        history = json.loads(history_json) if history_json else []
        
        # 2. Mutate based on user action
        if edit_index is not None:
            # The user clicked Edit/Regenerate. Slice off the abandoned future timeline.
            history = history[:edit_index]
            history.append({"role": "user", "content": messages[-1].content})
            logger.info(f"State mutated for session {session_id} at index {edit_index}.")
            
        elif len(messages) > 1 or not history:
            # Fallback for unexpected payloads or initialization
            history = [{"role": m.role, "content": m.content} for m in messages]
            
        else:
            # Standard conversational flow: append the newest single message
            history.append({"role": "user", "content": messages[0].content})
        
        # 3. Serialize and Save with Rolling Expiration
        # The 'ex' parameter resets the countdown timer to 24 hours every time the user speaks.
        redis_client.set(redis_key, json.dumps(history), ex=settings.REDIS_SESSION_TTL)
        
        return history
        
    except Exception as e:
        logger.error(f"Redis connection failed during sync for session {session_id}: {e}")
        # HARD FAIL: We refuse to process the prompt if we cannot secure the state.
        raise RuntimeError("The session database is currently offline. Please try again.")


def update_global_state(session_id: str, new_history: list):
    """
    Updates the master Redis record after the Orchestrator performs 
    Global Truncation (e.g., pruning older messages to fit the 8,000 token limit).
    """
    redis_key = f"session:{session_id}"
    try:
        redis_client.set(redis_key, json.dumps(new_history), ex=settings.REDIS_SESSION_TTL)
    except Exception as e:
        logger.error(f"Failed to save truncated global state for session {session_id}: {e}")
        raise RuntimeError("Failed to update memory limits. Please try again.")


def append_assistant_response(session_id: str, content: str):
    """
    Appends the AI's finalized response to the Redis session state once 
    the Server-Sent Events stream has successfully completed.
    """
    if not content:
        return
        
    redis_key = f"session:{session_id}"
    try:
        # We must re-fetch the history here in case it was truncated by update_global_state 
        # during the orchestration pipeline.
        history_json = redis_client.get(redis_key)
        if history_json:
            history = json.loads(history_json)
            history.append({"role": "assistant", "content": content})
            
            # Save the final array and reset the 24-hour timer one last time
            redis_client.set(redis_key, json.dumps(history), ex=settings.REDIS_SESSION_TTL)
            
    except Exception as e:
        logger.error(f"Failed to append assistant response for session {session_id}: {e}")
        # We don't raise a RuntimeError here because the AI has already streamed the text 
        # to the user. We just log the failure. The next prompt will likely fail cleanly in sync_session_state.