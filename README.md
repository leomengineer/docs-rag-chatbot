# docs-rag-chatbot

A support chatbot that answers customer questions from your own docs, with cited sources.

Drop in PDFs and Markdown, ingest once, and ask questions in a chat UI. Every answer lists the source files it used. If nothing relevant is in the knowledge base, the bot says it isn't in the clinic documents instead of making something up.

## Architecture

```
docs/ (md + pdf)
   → ingest (chunk + embed)          local sentence-transformers
   → Postgres + pgvector             dense vectors + full-text (tsvector)
   → hybrid retrieve (RRF)           semantic + keyword fused
   → similarity floor gate           refuse when nothing is relevant
   → LLM (OpenAI or Anthropic)       swap with LLM_PROVIDER
   → answer + cited sources
   → Streamlit chat UI
```

Hybrid search runs in a **single Postgres** container: cosine distance via `pgvector` plus native `ts_rank` full-text, combined with Reciprocal Rank Fusion. No separate vector DB or Elasticsearch.

## Quick start

```bash
# 1. deps + env
uv sync
cp .env.example .env
# put OPENAI_API_KEY=... (or ANTHROPIC_API_KEY=... and LLM_PROVIDER=anthropic)

# 2. database
make up

# 3. index the sample dental clinic docs, then run API + UI
make ingest
make api          # terminal 1 — http://localhost:8000
make ui           # terminal 2 — Streamlit chat
```

Sample knowledge base: **BrightSmile Dental Clinic** (~20 Markdown docs + 3 PDFs covering services, pricing, insurance, booking, pre/post-op care, hours).

## Swap the knowledge base

```bash
# drop your own PDFs/Markdown into a folder, then:
make ingest DOCS=./my_docs
# or: curl -X POST localhost:8000/ingest -H 'content-type: application/json' -d '{"folder":"./my_docs"}'
```

Then ask the chat about the new content — answers cite the new filenames.

## API

- `POST /chat` `{"question": "..."}` → `{"answer": "...", "sources": [{"filename", "snippet", "score"}]}`
- `POST /ingest` `{"folder": "./docs"}` → re-chunk and re-index
- `GET /documents` → list Markdown/PDF files in the knowledge base
- `POST /documents/upload` multipart `file` → save into `docs/` and re-index
- `GET /health`

## Config (`.env`)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection string |
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | API keys |
| `SIMILARITY_FLOOR` | Cosine floor below which the bot refuses (default `0.35`) |
| `API_URL` | Where Streamlit sends chat requests |

Embeddings are local (`all-MiniLM-L6-v2`, 384-dim) — no embedding API key required.

## Features

1. Ask: *"How much is a porcelain crown without insurance?"* → show cited answer from `05_pricing_cash.md`.
2. Ask: *"What's your return policy for sneakers?"* → show the "isn't covered in the clinic documents" refusal (out of scope).
3. Sidebar: upload a new `.md`/`.pdf` → **Upload & re-index** → ask about it → answer cites the new file.


## Stack

Python · FastAPI · Postgres/`pgvector` · sentence-transformers · OpenAI/Anthropic · Streamlit · Docker Compose · [uv](https://github.com/astral-sh/uv)

## Scope (intentionally skipped)

No auth, multi-tenant, token streaming, conversation memory, or re-ranker. Production-shaped demo, not production-complete.
