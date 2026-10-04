"""
Context Manager Module
======================
Handles payload sanitization, token estimation, and dynamic context windows.
Prevents Out-Of-Memory (OOM) API errors and "Catastrophic Amnesia" during massive payloads.
"""

# Maximum character limit for the LLM context window to prevent Out-Of-Memory (OOM) errors
MAX_PAYLOAD_CHARS = 20000

# Defined at the global scope so it can be safely imported by orchestrator.py 
# for pre-flight escalation checks.
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def sanitize_and_truncate(messages: list[dict], max_input_tokens: int = 3400) -> tuple[list[dict], int]:
    """
    Enforces silent sanitization, removes error loops, and implements a Sliding Token Budget.
    Dynamically shrinks the payload based on the assigned model's context window.
    """
    clean_messages = []
    
    # 1. Role Enforcement, Error Loop Removal, and Whitespace Trimming
    for m in messages:
        role = m.get("role")
        content = m.get("content", "").strip() 
        
        # API safety: Only standard roles are allowed
        if role not in ["user", "assistant"]:
            continue
        # Prevents the AI from reading past UI errors and hallucinating further errors
        if role == "assistant" and content.startswith("Error:"):
            continue
        # API safety: Rejects empty strings which cause hard 400 Bad Request errors from LLM providers
        if not content:
            continue
            
        clean_messages.append({"role": role, "content": content})

    if not clean_messages:
        return [], 4096

    # 2. Sequence Correction
    # Cloud LLM APIs expect the payload to strictly terminate with a user prompt.
    if clean_messages[-1]["role"] != "user":
        clean_messages.append({"role": "user", "content": "Please continue."})

    target_max_tokens = 4096
    reserved_system_tokens = 150 
    
    # 3. Sliding Token Budget (O(n) Math Optimization)
    # We calculate the initial token weight exactly once to act as a running ledger.
    # This prevents an expensive O(n^2) re-calculation inside the while loop.
    running_input_tokens = sum(estimate_tokens(m["content"]) for m in clean_messages) + reserved_system_tokens
    
    while clean_messages:
        if running_input_tokens <= max_input_tokens:
            break
            
        excess_tokens = running_input_tokens - max_input_tokens
        oldest_tokens = estimate_tokens(clean_messages[0]["content"])
        
        # 4. Smart Truncation (Anti-Amnesia Logic)
        # If dropping the oldest message destroys a massive document (>2000 tokens), 
        # or we are down to the final user prompt, we do NOT pop the entire message.
        # Instead, we cleanly slice characters off the TOP (the oldest part) of the oldest message.
        if oldest_tokens > 2000 or len(clean_messages) <= 2:
            excess_chars = max(0, excess_tokens * 4)
            if excess_chars > 0:
                clean_messages[0]["content"] = clean_messages[0]["content"][excess_chars:]
                running_input_tokens -= excess_tokens
            break
        else:
            # Standard conversational sliding window: pop oldest complete turns to save space.
            oldest_msg = clean_messages.pop(0) 
            running_input_tokens -= oldest_tokens
            
            # Check for the orphaned AI response (Double Pop)
            # If we delete a user's question, the AI's subsequent answer loses its conversational context.
            # We pop the AI's answer as well to maintain clean contextual pairs.
            if clean_messages and clean_messages[0]["role"] == "assistant":
                orphaned_ai = clean_messages.pop(0) 
                running_input_tokens -= estimate_tokens(orphaned_ai["content"])

    # 5. Calculate safe max_tokens using the instantly available running total
    # We subtract the payload size from the hard TPM limit so the LLM doesn't 
    # get forcefully cut off mid-sentence by the provider's API token ceiling.
    provider_tpm_limit = 7500 
    safe_max_tokens = min(target_max_tokens, max(512, provider_tpm_limit - running_input_tokens))

    return clean_messages, safe_max_tokens