"""Hybrid retrieval: dense (pgvector) + full-text (tsvector), fused with RRF."""

from rag import db
from rag.embed import embed_one

RRF_K = 60
CANDIDATES = 20


def dense_search(query_vec, n=CANDIDATES):
    return db.fetchall(
        """
        SELECT id, source_filename, doc_title, chunk,
               1 - (embedding <=> %s::vector) AS score
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_vec, query_vec, n),
    )


def keyword_search(query, n=CANDIDATES):
    return db.fetchall(
        """
        SELECT id, source_filename, doc_title, chunk,
               ts_rank(tsv, plainto_tsquery('english', %s)) AS score
        FROM chunks
        WHERE tsv @@ plainto_tsquery('english', %s)
        ORDER BY score DESC
        LIMIT %s
        """,
        (query, query, n),
    )


def rrf_fuse(lists, k=RRF_K):
    scores = {}
    payloads = {}
    for results in lists:
        for rank, row in enumerate(results):
            cid = row["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            payloads[cid] = row
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    out = []
    for cid, rrf_score in ranked:
        row = dict(payloads[cid])
        row["rrf_score"] = rrf_score
        out.append(row)
    return out


def hybrid_search(query, k=5):
    """
    Returns (chunks, best_dense_score).
    best_dense_score is the top cosine similarity — used as the anti-hallucination gate.
    """
    query_vec = embed_one(query)
    dense = dense_search(query_vec)
    keyword = keyword_search(query)

    best_dense = float(dense[0]["score"]) if dense else 0.0
    fused = rrf_fuse([dense, keyword])[:k]

    # attach the dense score when available for citation display
    dense_by_id = {r["id"]: float(r["score"]) for r in dense}
    for row in fused:
        row["score"] = dense_by_id.get(row["id"], float(row.get("score") or 0.0))

    return fused, best_dense
