"""FastAPI: POST /chat and POST /ingest."""

from fastapi import FastAPI
from pydantic import BaseModel

from rag.answer import answer
from rag.ingest import ingest_folder

app = FastAPI(title="docs-rag-chatbot")


class ChatRequest(BaseModel):
    question: str


class IngestRequest(BaseModel):
    folder: str = "./docs"


@app.post("/chat")
def chat(req: ChatRequest):
    return answer(req.question)


@app.post("/ingest")
def ingest(req: IngestRequest):
    n = ingest_folder(req.folder)
    return {"ok": True, "chunks": n}


@app.get("/health")
def health():
    return {"ok": True}
