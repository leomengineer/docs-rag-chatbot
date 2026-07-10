"""API tests — mock retrieval/LLM/ingest so no DB or API keys required."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from rag.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@patch("rag.api.answer")
def test_chat_returns_answer_and_sources(mock_answer):
    mock_answer.return_value = {
        "answer": "Call (951) 555-0142 for emergencies. [08_emergency_care.md]",
        "sources": [
            {
                "filename": "08_emergency_care.md",
                "snippet": "During office hours: Call (951) 555-0142.",
                "score": 0.5137,
            }
        ],
    }

    resp = client.post("/chat", json={"question": "which number to call in an emergency?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "555-0142" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "08_emergency_care.md"
    mock_answer.assert_called_once_with("which number to call in an emergency?")


@patch("rag.api.answer")
def test_chat_refusal(mock_answer):
    mock_answer.return_value = {
        "answer": "I don't know based on the clinic documents I have.",
        "sources": [],
    }

    resp = client.post("/chat", json={"question": "return policy for sneakers?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"] == []
    assert "don't know" in data["answer"].lower()


def test_chat_missing_question():
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_empty_body():
    resp = client.post("/chat")
    assert resp.status_code == 422


@patch("rag.api.ingest_folder")
def test_ingest_default_folder(mock_ingest):
    mock_ingest.return_value = 45

    resp = client.post("/ingest", json={})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "chunks": 45}
    mock_ingest.assert_called_once_with("./docs")


@patch("rag.api.ingest_folder")
def test_ingest_custom_folder(mock_ingest):
    mock_ingest.return_value = 12

    resp = client.post("/ingest", json={"folder": "./my_docs"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "chunks": 12}
    mock_ingest.assert_called_once_with("./my_docs")


@patch("rag.api.ingest_folder")
def test_ingest_empty_folder(mock_ingest):
    mock_ingest.return_value = 0

    resp = client.post("/ingest", json={"folder": "./empty"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "chunks": 0}
