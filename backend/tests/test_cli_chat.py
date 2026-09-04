import httpx
import json

def run_cli_chat():
    print("===================================================")
    print("   OptiRoute Mock Frontend (CLI Chat Interface)    ")
    print("   Type 'quit' or 'exit' to end the session.       ")
    print("===================================================\n")
    
    # This acts as our "Frontend State"
    chat_history = []
    
    # We use httpx synchronously here to make the HTTP requests
    client = httpx.Client(timeout=200.0)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            print("Session ended.")
            break
            
        # 1. Append the new user message to the frontend array
        chat_history.append({"role": "user", "content": user_input})
        
        # 2. Show you EXACTLY what is being sent to FastAPI
        payload = {"messages": chat_history}
        print("\n--- [DEBUG: PAYLOAD SENT TO BACKEND] ---")
        print(json.dumps(payload, indent=2))
        print("----------------------------------------\n")
        
        # 3. Send the HTTP POST request to your FastAPI server
        try:
            response = client.post("http://127.0.0.1:8000/api/ask", json=payload)
            response.raise_for_status()
            data = response.json()
            
            answer = data.get("answer", "")
            telemetry = data.get("telemetry", {})
            
            # 4. Append the AI's response to the frontend array so the context grows
            if not answer.startswith("Error:"):
                chat_history.append({"role": "assistant", "content": answer})
            else:
                # If OpenAI fails, we pop the user's message so the array doesn't get corrupted
                chat_history.pop()
            
            # 5. Display the AI response and Naveen's Telemetry metrics
            print(f"AI: {answer}")
            print("\n--- [TELEMETRY DASHBOARD] ---")
            for key, value in telemetry.items():
                print(f" > {key}: {value}")
            print("-----------------------------\n")
                
        except Exception as e:
            print(f"\n[ERROR] Could not connect to API: {e}")
            print("Make sure your FastAPI server (uvicorn) is running in another terminal!")
            chat_history.pop()

if __name__ == "__main__":
    run_cli_chat()