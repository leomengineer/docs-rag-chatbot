DOCS ?= ./docs

.PHONY: up down ingest api ui sync

sync:
	uv sync

up:
	docker compose up -d

down:
	docker compose down

ingest:
	uv run python -m rag.ingest $(DOCS)

api:
	uv run uvicorn rag.api:app --reload --port 8000

ui:
	uv run streamlit run ui.py
