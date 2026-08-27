"""
logger.py

Logs every chatbot interaction to a file for later review:
    - what the user asked
    - what chunks were retrieved and their similarity scores
    - what answer was given
    - whether it came from cache or a fresh Groq call
    - timestamp

This is useful for:
    - Debugging bad answers
    - Showing real usage data in your project report
    - Identifying common questions to improve the knowledge base later
"""

import json
import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "interaction_log.jsonl")


def log_interaction(question: str, chunks: list, answer: str, source: str):
    """
    source: one of "cache", "groq", "no_match"
    chunks: the list of retrieved chunks (can be empty)
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "source": source,
        "top_similarity": chunks[0]["similarity"] if chunks else None,
        "num_chunks_used": len(chunks),
        "retrieved_questions": [c["question"] for c in chunks]
    }

    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[logger.py] WARNING: failed to write log: {e}")


def read_all_logs():
    """
    Returns a list of all logged interactions. Useful for building
    an analytics view later (most asked questions, low-confidence
    questions, etc.)
    """
    if not os.path.exists(LOG_FILE):
        return []

    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return logs


# Quick manual test - only runs if you execute this file directly:
#   python logger.py
if __name__ == "__main__":
    log_interaction(
        question="what is the fee for btech",
        chunks=[{"question": "What is the fee for B.Tech?", "similarity": 0.62}],
        answer="The B.Tech fee is ₹94,800/year.",
        source="groq"
    )
    print("Test log entry written.")

    logs = read_all_logs()
    print(f"\nTotal logged interactions: {len(logs)}")
    for entry in logs:
        print(entry)