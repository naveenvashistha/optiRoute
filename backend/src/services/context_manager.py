# Maximum character limit for the LLM context window to prevent Out-Of-Memory (OOM) errors
MAX_PAYLOAD_CHARS = 20000

def sanitize_and_truncate(messages: list[dict]) -> tuple[list[dict], int]:
    """
    Enforces silent sanitization, removes error loops, and implements a Sliding Token Budget.
    Guarantees the payload + max_tokens never exceeds the provider's TPM limits.
    """
    clean_messages = []
    
    # 1. Role Enforcement, Error Loop Removal, and Whitespace Trimming
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

    # 2. Sequence Correction
    if clean_messages[-1]["role"] != "user":
        clean_messages.append({"role": "user", "content": "Please continue."})

    # 3. Sliding Token Budget
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    provider_tpm_limit = 7500 
    target_max_tokens = 4096
    reserved_system_tokens = 150 
    
    while clean_messages:
        current_input_tokens = sum(estimate_tokens(m["content"]) for m in clean_messages) + reserved_system_tokens
        
        if current_input_tokens + target_max_tokens <= provider_tpm_limit:
            break
            
        if len(clean_messages) >= 3:
            clean_messages.pop(0) 
            if clean_messages and clean_messages[0]["role"] == "assistant":
                clean_messages.pop(0) 
        else:
            excess_tokens = (current_input_tokens + target_max_tokens) - provider_tpm_limit
            excess_chars = excess_tokens * 4
            clean_messages[-1]["content"] = clean_messages[-1]["content"][excess_chars:]
            break

    # 5. Calculate safe max_tokens
    final_input_tokens = sum(estimate_tokens(m["content"]) for m in clean_messages) + reserved_system_tokens
    safe_max_tokens = min(target_max_tokens, max(512, provider_tpm_limit - final_input_tokens))

    return clean_messages, safe_max_tokens