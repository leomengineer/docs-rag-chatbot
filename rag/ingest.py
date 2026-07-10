"""Load docs from a folder, chunk, embed, and insert into Postgres."""

import re
import sys
from pathlib import Path

from pypdf import PdfReader

from rag import db
from rag.embed import embed

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def load_md(path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    title = _title_from_md(text) or path.stem.replace("_", " ").replace("-", " ").title()
    return title, text


def load_pdf(path):
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        parts.append(t)
    text = "\n".join(parts)
    title = path.stem.replace("_", " ").replace("-", " ").title()
    return title, text


def _title_from_md(text):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def chunk_text(text):
    """Simple overlapping window chunker on whitespace-normalized text."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            # break on nearest space so we don't split mid-word
            space = text.rfind(" ", start, end)
            if space > start:
                end = space
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def load_docs(folder):
    folder = Path(folder)
    docs = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            title, text = load_md(path)
        elif suffix == ".pdf":
            title, text = load_pdf(path)
        else:
            continue
        docs.append(
            {
                "source_filename": path.name,
                "doc_title": title,
                "text": text,
            }
        )
    return docs


def ingest_folder(folder):
    docs = load_docs(folder)
    if not docs:
        print(f"no .md/.pdf files found in {folder}")
        return 0

    db.ensure_schema()
    db.execute("DELETE FROM chunks")

    rows = []
    texts = []
    meta = []
    for doc in docs:
        for piece in chunk_text(doc["text"]):
            texts.append(piece)
            meta.append((doc["source_filename"], doc["doc_title"], piece))

    print(f"embedding {len(texts)} chunks from {len(docs)} docs...")
    vectors = embed(texts)

    for (filename, title, piece), vec in zip(meta, vectors):
        rows.append((filename, title, piece, vec))

    db.executemany(
        "INSERT INTO chunks (source_filename, doc_title, chunk, embedding) VALUES (%s, %s, %s, %s)",
        rows,
    )
    print(f"ingested {len(rows)} chunks")
    return len(rows)


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "./docs"
    ingest_folder(folder)
