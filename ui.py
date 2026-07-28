"""Streamlit chat UI — knowledge-base sidebar + cited answers."""

import html
import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DOCS_DIR = Path("./docs")


def _render_snippet(text: str) -> None:
    """Show source text as small plain text — avoid markdown headings in snippets."""
    st.markdown(
        f'<p style="font-size:0.875rem;color:rgba(49,51,63,0.6);margin:0 0 0.75rem;">'
        f"{html.escape(text)}</p>",
        unsafe_allow_html=True,
    )


def _api(method: str, path: str, **kwargs):
    try:
        r = getattr(httpx, method)(f"{API_URL}{path}", timeout=300.0, **kwargs)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        st.error(
            f"Cannot reach the API at `{API_URL}`. "
            "Start it with `make api` (and `make up` for Postgres)."
        )
        st.stop()
    except httpx.HTTPError as exc:
        st.error(f"API error: {exc}")
        return None


st.set_page_config(page_title="Clinic Support Copilot", page_icon="🦷", layout="wide")
st.title("Clinic Support Copilot")
st.caption("Answers from your clinic docs, with cited sources. No guessing.")

# --- Sidebar: knowledge base ---
with st.sidebar:
    st.header("Knowledge base")
    st.caption("Docs the bot answers from. Upload → auto re-index.")

    listed = _api("get", "/documents", params={"folder": str(DOCS_DIR)})
    docs = (listed or {}).get("docs") or []
    st.markdown(f"**{len(docs)}** docs indexed from `{DOCS_DIR}/`")

    if docs:
        for d in docs:
            st.markdown(f"- `{d['filename']}` — {d.get('title') or ''}")
    else:
        st.info("No docs yet. Upload a Markdown or PDF below.")

    st.divider()
    uploaded = st.file_uploader(
        "Add a doc",
        type=["md", "pdf"],
        help="Saved into docs/ and the knowledge base is re-indexed.",
    )
    if st.button("Upload & re-index", type="primary", disabled=uploaded is None, use_container_width=True):
        with st.spinner(f"Saving {uploaded.name} and re-indexing…"):
            files = {
                "file": (
                    uploaded.name,
                    uploaded.getvalue(),
                    uploaded.type or "application/octet-stream",
                )
            }
            try:
                r = httpx.post(
                    f"{API_URL}/documents/upload",
                    params={"folder": str(DOCS_DIR)},
                    files=files,
                    timeout=300.0,
                )
                r.raise_for_status()
                data = r.json()
                st.success(
                    f"Added `{data['filename']}` — {data['chunks']} chunks indexed."
                )
                st.rerun()
            except httpx.ConnectError:
                st.error(f"Cannot reach the API at `{API_URL}`.")
            except httpx.HTTPError as exc:
                st.error(f"Upload failed: {exc}")

    if st.button("Re-index folder only", use_container_width=True):
        with st.spinner("Re-indexing…"):
            data = _api("post", "/ingest", json={"folder": str(DOCS_DIR)})
            if data:
                st.success(f"Re-indexed — {data.get('chunks', 0)} chunks.")

# --- Main: chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.markdown(f"**{s['filename']}** (score {s['score']})")
                    _render_snippet(s["snippet"])

prompt = st.chat_input("Ask about services, pricing, booking, care...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching docs..."):
            try:
                r = httpx.post(
                    f"{API_URL}/chat",
                    json={"question": prompt},
                    timeout=120.0,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                data = {"answer": f"Error talking to API: {e}", "sources": []}

        st.markdown(data["answer"])
        sources = data.get("sources") or []
        if sources:
            with st.expander("Sources", expanded=False):
                for s in sources:
                    st.markdown(f"**{s['filename']}** (score {s['score']})")
                    _render_snippet(s["snippet"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": data["answer"],
            "sources": sources,
        }
    )
