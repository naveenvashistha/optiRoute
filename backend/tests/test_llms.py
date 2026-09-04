import sys
import asyncio
import time
from pathlib import Path

print("[1/3] Loading LLM service modules... (this may take a second)")
# Add the 'backend' directory to the system path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.services.llm_client import call_local_llm, call_cloud_llm
print("[1/3] Modules loaded successfully!\n")

async def run_llm_tests():
    print("--- Starting LLM Client Tests ---")
    
    test_messages = [
        {"role": "user", "content": "Explain what an Operating System is in exactly one short sentence."}
    ]

    # 1. Test Local Ollama
    print("\n[2/3] Connecting to Local SLM (Ollama)...")
    print("      Waiting for model generation (usually 2-10 seconds)...")
    start_time = time.time()
    try:
        local_response = await call_local_llm(test_messages)
        elapsed = time.time() - start_time
        print(f"      Success! ({elapsed:.2f}s) Local Output:")
        print(f"      -> {local_response}")
    except Exception as e:
        print(f"      [FAILED] Local SLM Test: {e}")

    # 2. Test Cloud OpenAI
    print("\n[3/3] Connecting to Cloud LLM (OpenAI API)...")
    print("      Waiting for network response...")
    start_time = time.time()
    try:
        cloud_response = await call_cloud_llm(test_messages)
        elapsed = time.time() - start_time
        print(f"      Success! ({elapsed:.2f}s) Cloud Output:")
        print(f"      -> {cloud_response}")
    except Exception as e:
        print(f"      [FAILED] Cloud LLM Test: {e}")
        
    print("\n--- Testing Complete ---")

if __name__ == "__main__":
    asyncio.run(run_llm_tests())