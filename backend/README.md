# Knowledge chatbot backend

FastAPI backend for document ingestion, semantic retrieval, chat sessions, and grounded answer generation. See the [main README](../README.md) for complete setup and requirement coverage.

After starting PostgreSQL and Ollama, run from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Default provider: local Ollama with `qwen3:1.7b`. For OpenAI, set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in `.env`. Restart after changing settings.

API docs: http://127.0.0.1:8000/docs (Swagger), `/redoc`, and `/openapi.json`.

Tests, with PostgreSQL available:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Tests cover health, PDF extraction, document upload/delete, unsupported formats, memory, retrieval fallback, streaming errors, and the local-provider adapter. Automated generator tests mock AI services; evaluate real model accuracy separately.
