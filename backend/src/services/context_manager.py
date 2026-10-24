"""
Context Manager Module
======================
Handles payload sanitization, token estimation, and dynamic context windows.
Prevents Out-Of-Memory (OOM) API errors and "Catastrophic Amnesia" during massive payloads.
"""

import logging

logger = logging.getLogger(__name__)

MAX_PAYLOAD_CHARS = 20000

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def sanitize_and_truncate(messages: list[dict], max_input_tokens: int = 3400) -> tuple[list[dict], int]:
    clean_messages = []

    for m in messages:
        role = m.get("role")
        content = m.get("content", "").strip() 

        if role not in ["user", "assistant"]:
            continue
        if role == "assistant" and content.startswith("Error:"):
            continue
        if not content:
            continue

        clean_messages.append({"role": role, "content": content})

    if not clean_messages:
        return [], 4096

    if clean_messages[-1]["role"] != "user":
        clean_messages.append({"role": "user", "content": "Please continue."})

    target_max_tokens = 4096
    reserved_system_tokens = 150 
    
    # Store initial token count for accurate logging
    starting_tokens = sum(estimate_tokens(m["content"]) for m in clean_messages) + reserved_system_tokens
    running_input_tokens = starting_tokens

    while clean_messages:
        if running_input_tokens <= max_input_tokens:
            break

        # FIXED: Re-added the missing subtraction operator
        excess_tokens = running_input_tokens - max_input_tokens
        oldest_tokens = estimate_tokens(clean_messages[0]["content"])

        if oldest_tokens > 2000 or len(clean_messages) <= 2:
            # FIXED: Re-added the missing multiplication operator
            excess_chars = max(0, excess_tokens * 4)
            if excess_chars > 0:
                clean_messages[0]["content"] = clean_messages[0]["content"][excess_chars:]
                running_input_tokens -= excess_tokens
            break
        else:
            oldest_msg = clean_messages.pop(0) 
            running_input_tokens -= oldest_tokens

            if clean_messages and clean_messages[0]["role"] == "assistant":
                orphaned_ai = clean_messages.pop(0) 
                running_input_tokens -= estimate_tokens(orphaned_ai["content"])

    # FIXED: Re-added the missing subtraction operator
    provider_tpm_limit = 7500 
    safe_max_tokens = min(target_max_tokens, max(512, provider_tpm_limit - running_input_tokens))

    # Real-time telemetry log for your backend terminal
    if starting_tokens > max_input_tokens:
        logger.warning(
            f"Context Pruned: Dropped from {starting_tokens} down to {running_input_tokens} tokens "
            f"to fit {max_input_tokens} limit. Retained {len(clean_messages)} messages."
        )

    return clean_messages, safe_max_tokens