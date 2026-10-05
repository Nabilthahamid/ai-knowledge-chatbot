from fastapi.testclient import TestClient
import httpx
from openai import RateLimitError

from app.chat.store import initialize_chat_tables
from app.main import app


client = TestClient(app)


def test_stream_reports_exhausted_credits(monkeypatch):
    monkeypatch.setattr("app.chat.routes.session_exists", lambda session_id: True)
    monkeypatch.setattr("app.chat.routes.load_recent_messages", lambda session_id: [])
    monkeypatch.setattr("app.chat.routes.add_message", lambda **kwargs: {"id": 1})
    monkeypatch.setattr(
        "app.chat.routes.retrieve_context",
        lambda **kwargs: {
            "found_in_knowledge_base": True,
            "search_results": [],
            "citations": [],
        },
    )

    def fail_generation(**kwargs):
        raise RateLimitError(
            "No credits remaining",
            response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses")),
            body={"code": "credit_balance_exhausted"},
        )

    monkeypatch.setattr("app.chat.routes.generate_answer_stream", fail_generation)
    response = client.post(
        "/api/v1/chat/sessions/1/messages/stream",
        json={"message": "What is FastAPI?", "top_k": 5},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "no available credits or quota" in response.text
    assert "event: done" not in response.text


def test_conversation_memory(monkeypatch):
    initialize_chat_tables()

    response = client.post(
        "/api/v1/chat/sessions",
        json={
            "title": "Memory test"
        },
    )

    assert response.status_code == 201

    session_id = response.json()["id"]
    captured_history = []

    def fake_answer_question(
        question,
        top_k,
        conversation_history,
    ):
        captured_history.append(
            conversation_history
        )

        return {
            "answer": f"Test answer for: {question}",
            "found_in_knowledge_base": True,
            "citations": [],
        }

    monkeypatch.setattr(
        "app.chat.routes.answer_question",
        fake_answer_question,
    )

    first_response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "message": "What is machine learning?",
            "top_k": 5,
        },
    )

    assert first_response.status_code == 200
    assert len(captured_history[0]) == 0

    second_response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "message": "What are its advantages?",
            "top_k": 5,
        },
    )

    assert second_response.status_code == 200

    # Previous user and assistant messages
    # should now be available.
    assert len(captured_history[1]) == 2
