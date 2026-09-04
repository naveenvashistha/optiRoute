import sys
from pathlib import Path

# Add the 'backend' directory to the system path so Python can find the 'src' folder
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.services.router import evaluate_difficulty

def run_router_tests():
    print("--- Starting Router Tests ---")
    
    test_queries = [
        "What is 2 + 2?", 
        "Explain the ACID properties in a Database Management System and provide examples of how they handle transaction failures.",
        "Explain it in detail.",
        "Design a scalable microservices architecture for a real-time ride-sharing application."
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            # 0 = Local (Easy), 1 = Cloud (Hard)
            prediction = evaluate_difficulty(query)
            route = "LOCAL_SLM" if prediction == 0 else "CLOUD_LLM"
            print(f"Result: Class {prediction} -> Routed to {route}")
        except Exception as e:
            print(f"Test Failed for query: {e}")

if __name__ == "__main__":
    run_router_tests()