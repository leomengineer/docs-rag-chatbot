"""Retrieve + gate + prompt + LLM -> {answer, sources}."""

import os

from dotenv import load_dotenv

from rag.llm import call_llm
from rag.retrieve import hybrid_search

load_dotenv()

SIMILARITY_FLOOR = float(os.environ.get("SIMILARITY_FLOOR", "0.35"))
TOP_K = 5

SYSTEM = (
    "Answer only from the provided context. "
    "If the answer isn't in the context, say you don't know. "
    "Cite sources by filename."
)

IDK = (
    "I don't know based on the clinic documents I have. "
    "Try rephrasing, or ask about services, pricing, insurance, "
    "booking, hours, or pre/post-op care."
)


def answer(question):
    chunks, best_dense = hybrid_search(question, k=TOP_K)

    if best_dense < SIMILARITY_FLOOR or not chunks:
        return {"answer": IDK, "sources": []}

    context_parts = []
    sources = []
    seen = set()
    for c in chunks:
        context_parts.append(f"[{c['source_filename']}] {c['chunk']}")
        key = c["source_filename"]
        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "filename": c["source_filename"],
                    "snippet": c["chunk"][:200] + ("..." if len(c["chunk"]) > 200 else ""),
                    "score": round(float(c["score"]), 4),
                }
            )

    context = "\n\n".join(context_parts)
    user = f"Context:\n{context}\n\nQuestion: {question}"
    text = call_llm(SYSTEM, user)
    return {"answer": text, "sources": sources}
