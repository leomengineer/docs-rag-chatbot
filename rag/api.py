"""FastAPI: POST /chat, POST /ingest, docs list/upload."""

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from rag.answer import answer
from rag.ingest import ingest_folder, load_docs

app = FastAPI(title="docs-rag-chatbot")

ALLOWED_SUFFIXES = {".md", ".pdf"}


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


@app.get("/documents")
def list_documents(folder: str = "./docs"):
    """List Markdown/PDF files in the knowledge-base folder."""
    path = Path(folder)
    if not path.is_dir():
        return {"ok": True, "folder": folder, "docs": [], "count": 0}

    docs = [
        {"filename": doc["source_filename"], "title": doc["doc_title"]}
        for doc in load_docs(folder)
    ]
    return {"ok": True, "folder": folder, "docs": docs, "count": len(docs)}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), folder: str = "./docs"):
    """Save an uploaded .md/.pdf into the docs folder and re-index."""
    name = Path(file.filename or "").name
    if not name:
        raise HTTPException(status_code=400, detail="missing filename")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="only .md and .pdf are supported")

    dest_dir = Path(folder)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    content = await file.read()
    dest.write_bytes(content)

    chunks = ingest_folder(str(dest_dir))
    return {
        "ok": True,
        "filename": name,
        "path": str(dest),
        "chunks": chunks,
    }


@app.get("/health")
def health():
    return {"ok": True}
