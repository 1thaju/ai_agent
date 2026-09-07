"""
Semantic RAG retrieval using LangChain + a local FAISS vector index.

Replaces the earlier keyword-matching rag.py. Keeps the SAME function
signatures (retrieve_context, format_context_for_prompt) so ws.py and
converse.py don't need any changes beyond this file.

Why LangChain + FAISS here (and not Qdrant/a hosted vector DB):
- FAISS runs fully in-process, no server to run or manage — appropriate
  for a single-business, ~20-30 entry knowledge base.
- LangChain gives a standard Retriever interface, useful both for
  correctness (this file) and as genuine hands-on framework experience.
- If/when a second real client with a much larger knowledge base shows
  up, THIS is the natural point to graduate to Qdrant/Chroma with
  persistent, filtered, multi-tenant collections — not before.

The index is built once at import time from knowledge_base.json and
kept in memory for the life of the process (fine for a single-worker
FastAPI dev/demo deployment).
"""

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

from config import GEMINI_API_KEY

KB_PATH = Path("knowledge_base.json")

with open(KB_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)

# Similarity threshold below which we treat a match as "not relevant enough".
# FAISS + LangChain returns a relevance score in [0, 1] (higher = more similar)
# when using similarity_search_with_relevance_scores.
MIN_RELEVANCE_SCORE = 0.55

_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GEMINI_API_KEY,
)


def _build_vectorstore() -> FAISS:
    """Embed every KB entry once and build an in-memory FAISS index."""
    documents = []
    for entry in KNOWLEDGE_BASE:
        # Embed the question keywords + answer together so both natural
        # questions and paraphrased ones land close to this entry in
        # vector space.
        combined_text = (
            f"Topic keywords: {', '.join(entry['question_keywords'])}\n"
            f"Answer: {entry['answer']}"
        )
        documents.append(
            Document(
                page_content=combined_text,
                metadata={"id": entry["id"], "category": entry.get("category", ""), "answer": entry["answer"]},
            )
        )
    return FAISS.from_documents(documents, _embeddings)


_vectorstore = _build_vectorstore()


def retrieve_context(query: str, top_k: int = 2, min_score: float = MIN_RELEVANCE_SCORE) -> list[dict]:
    """
    Semantic retrieval: embed the query, find the top_k most similar KB
    entries by cosine similarity, and return only those above min_score.

    Returns a list of {"answer": ...} dicts — same shape the old
    keyword-based version returned, so format_context_for_prompt and
    every caller stay unchanged.
    """
    if not query.strip():
        return []

    results = _vectorstore.similarity_search_with_relevance_scores(query, k=top_k)

    matches = []
    for doc, score in results:
        if score >= min_score:
            matches.append({"answer": doc.metadata["answer"], "id": doc.metadata["id"], "score": round(score, 3)})

    return matches


def format_context_for_prompt(entries: list[dict]) -> str:
    """Turn retrieved entries into a short context block for the LLM prompt."""
    if not entries:
        return ""
    lines = [f"- {e['answer']}" for e in entries]
    return "Relevant business information:\n" + "\n".join(lines)