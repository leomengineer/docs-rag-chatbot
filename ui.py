"""Streamlit chat UI — calls the /chat API and shows cited sources."""

import html
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ.get("API_URL", "http://localhost:8000")


def _render_snippet(text: str) -> None:
    """Show source text as small plain text — avoid markdown headings in snippets."""
    st.markdown(
        f'<p style="font-size:0.875rem;color:rgba(49,51,63,0.6);margin:0 0 0.75rem;">'
        f"{html.escape(text)}</p>",
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="Clinic Support Copilot", page_icon="🦷")
st.title("Clinic Support Copilot")
st.caption("Answers from your clinic docs, with cited sources. No guessing.")

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
            with st.expander("Sources", expanded=True):
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
