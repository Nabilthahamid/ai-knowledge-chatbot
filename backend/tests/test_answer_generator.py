import json

import httpx
import pytest

from app.rag import answer_generator as generator


def test_local_answer_stream_uses_grounded_prompt(monkeypatch):
    def handle(request):
        payload = json.loads(request.content)
        assert payload["think"] is False
        assert payload["options"]["temperature"] == 0
        assert "only the supplied knowledge-base context" in payload["messages"][0]["content"]
        assert "FastAPI is a Python web framework." in payload["messages"][1]["content"]
        assert "Recent conversation:" in payload["messages"][1]["content"]
        return httpx.Response(200, text='{"message":{"content":"FastAPI is "},"done":false}\n{"message":{"content":"a Python web framework."},"done":true}\n')

    original_client = httpx.Client
    monkeypatch.setattr(generator, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(generator.httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs))
    results = [{"document_name": "sample.txt", "text": "FastAPI is a Python web framework."}]
    assert generator.generate_answer("What is FastAPI?", results) == "FastAPI is a Python web framework."
    assert list(generator.generate_answer_stream("What is FastAPI?", results)) == ["FastAPI is ", "a Python web framework."]


def test_local_stream_rejects_incomplete_response(monkeypatch):
    original_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text='{"message":{"content":"partial"},"done":false}\n'))
    monkeypatch.setattr(generator.httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs))
    with pytest.raises(RuntimeError, match="ended unexpectedly"):
        list(generator.local_answer_stream("test"))
