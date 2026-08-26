"""
Simple keyword-based RAG retrieval — no vector DB needed for a single
business's knowledge base. Loads knowledge_base.json once at startup
and scores entries against the customer's transcript.
"""

import json
from pathlib import Path

KB_PATH = Path("knowledge_base.json")

with open(KB_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)


def retrieve_context(query: str, top_k: int = 2, min_score: int = 1) -> list[dict]:
    """
    Score each knowledge base entry by how many of its keywords appear
    in the query (transcript). Return the top_k highest-scoring entries
    that meet min_score. Returns [] if nothing matches well enough.
    """
    query_lower = query.lower()
    scored = []

    for entry in KNOWLEDGE_BASE:
        score = sum(1 for kw in entry["question_keywords"] if kw.lower() in query_lower)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [entry for score, entry in scored if score >= min_score][:top_k]
    return results


def format_context_for_prompt(entries: list[dict]) -> str:
    """Turn retrieved entries into a short context block for the LLM prompt."""
    if not entries:
        return ""
    lines = [f"- {e['answer']}" for e in entries]
    return "Relevant business information:\n" + "\n".join(lines)