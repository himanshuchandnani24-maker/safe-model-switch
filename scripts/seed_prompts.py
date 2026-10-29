"""
Seed script to send 20 diverse prompts through POST /chat.
Ensures there is real-world query data for replay and evaluation.
Usage:
    python scripts/seed_prompts.py [optional_raw_api_key]
"""
import sys
import os
import httpx
import time

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import ApiKey

SAMPLE_PROMPTS = [
    # Prompts from Section 12
    "Explain what an API is in two sentences.",
    "Summarize in one line: 'Python is a popular language used for web, data, and automation.'",
    "Write a Python function that checks if a number is prime.",
    "Convert this to formal English: 'hey, send me the file asap'.",
    "Classify this review as positive or negative: 'The delivery was late but the product is great.'",
    "Give three tips to prepare for a first internship interview.",
    "What is the difference between a list and a tuple in Python?",
    "Extract the name and city as JSON: 'Riya lives in Pune and works at a bank.'",
    "Solve: a shirt costs 800 rupees with 15 percent discount. What is the final price?",
    "Explain recursion to a 10 year old.",
    
    # 10 Additional varied prompts (coding, writing, reasoning, math, extraction)
    "What is the time complexity of binary search and why?",
    "Write a SQL query to find the second highest salary from an Employee table.",
    "Rewrite this sentence in active voice: 'The report was submitted by the team yesterday.'",
    "Extract key numbers: 'The company made $4.2M revenue with 18% growth and 45 employees.'",
    "Is 91 a prime number? Answer with a brief mathematical explanation.",
    "Give two practical pros and cons of using microservices vs monolithic architecture.",
    "Classify intent: 'Can you help me reset my account password? I forgot it.'",
    "Write a Python one-liner to reverse a list.",
    "Explain the difference between authentication and authorization in simple terms.",
    "Summarize in 3 bullet points: why unit testing is essential in software development."
]


def run_seed(api_key: str = None, gateway_url: str = "http://127.0.0.1:8000"):
    # If no key passed, try fetching the first active key from database
    if not api_key:
        db = SessionLocal()
        first_key = db.query(ApiKey).first()
        db.close()
        if not first_key:
            print("ERROR: No API keys found in database. Run 'python scripts/create_key.py' first.")
            return
        print(f"Using default key ID {first_key.id} from database.")
        print("Tip: If calling over HTTP gateway, pass the plain text API key as an argument.")
        return

    headers = {"X-API-Key": api_key}
    print(f"Seeding {len(SAMPLE_PROMPTS)} prompts into {gateway_url}/chat...\n")

    success_count = 0
    with httpx.Client(timeout=30.0) as client:
        for idx, prompt in enumerate(SAMPLE_PROMPTS, 1):
            print(f"[{idx}/{len(SAMPLE_PROMPTS)}] Sending: '{prompt[:45]}...'")
            try:
                res = client.post(
                    f"{gateway_url}/chat",
                    json={"prompt": prompt},
                    headers=headers
                )
                if res.status_code == 200:
                    data = res.json()
                    print(f"    -> OK ({data['latency_ms']}ms, {data['output_tokens']} tokens, est ${data['est_cost_usd']})")
                    success_count += 1
                elif res.status_code == 429:
                    print("    -> 429 Rate limited. Waiting 10s...")
                    time.sleep(10)
                else:
                    print(f"    -> Failed with status {res.status_code}: {res.text[:80]}")
            except Exception as e:
                print(f"    -> Connection error: {e}")

            time.sleep(1)  # small pause to avoid local throttling

    print(f"\nSeeding complete: {success_count}/{len(SAMPLE_PROMPTS)} prompts logged successfully.")


if __name__ == "__main__":
    passed_key = sys.argv[1] if len(sys.argv) > 1 else None
    run_seed(api_key=passed_key)
