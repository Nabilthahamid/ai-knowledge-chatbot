from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rag_answer(monkeypatch):
    fake_results = [
        {
            "id": 1,
            "document_name": "sample.txt",
            "chunk_index": 0,
            "page_number": None,
            "text": "FastAPI is a Python web framework.",
            "similarity": 0.90,
        }
    ]

    monkeypatch.setattr(
        "app.rag.routes.embed_query",
        lambda query: [0.0] * 384,
    )

    monkeypatch.setattr(
        "app.rag.routes.search_similar",
        lambda query_embedding, top_k: fake_results,
    )

    monkeypatch.setattr(
        "app.rag.routes.generate_answer",
        lambda question, results: (
            "FastAPI is a Python web framework."
        ),
    )

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "What is FastAPI?",
            "top_k": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["found_in_knowledge_base"] is True
    assert "FastAPI" in data["answer"]
    assert len(data["citations"]) == 1


def test_rag_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.rag.routes.embed_query",
        lambda query: [0.0] * 384,
    )

    monkeypatch.setattr(
        "app.rag.routes.search_similar",
        lambda query_embedding, top_k: [],
    )

    response = client.post(
        "/api/v1/rag/ask",
        json={
            "question": "What is unrelated information?",
            "top_k": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["found_in_knowledge_base"] is False
    assert data["citations"] == []