import os
import json

import httpx

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5",
)


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")


def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def local_answer_stream(user_input: str):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": user_input},
        ],
        "think": False,
        "stream": True,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 512},
    }
    with httpx.Client(timeout=httpx.Timeout(180, connect=5)) as local_client:
        with local_client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as response:
            response.raise_for_status()
            completed = False
            for line in response.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError("Local model failed to generate an answer.")
                content = event.get("message", {}).get("content", "")
                if content:
                    yield content
                if event.get("done"):
                    completed = True
                    break
            if not completed:
                raise RuntimeError("Local model response ended unexpectedly.")


FALLBACK_MESSAGE = (
    "I could not find this information "
    "in the knowledge base."
)


SYSTEM_INSTRUCTIONS = """
You are a knowledge-base assistant.

Answer using only the supplied knowledge-base context.

Rules:

1. Do not use outside knowledge.
2. Do not invent facts.
3. Use conversation history only to understand
   references like "it", "they", or "that".
4. Conversation history is not factual evidence.
5. Use the knowledge-base context as the only
   factual source.
6. If the answer is not present, say that you
   could not find it in the knowledge base.
7. Be clear and concise.
"""


def build_context(
    search_results: list[dict],
) -> str:
    context_parts = []

    for index, result in enumerate(
        search_results,
        start=1,
    ):
        source = result.get(
            "document_name",
            "Unknown source",
        )

        page = result.get("page_number")

        page_text = (
            f", page {page}"
            if page is not None
            else ""
        )

        content = result.get("text", "")

        context_parts.append(
            f"[Source {index}: {source}{page_text}]\n"
            f"{content}"
        )

    return "\n\n".join(context_parts)


def build_conversation_context(
    conversation_history: list[dict] | None,
) -> str:
    if not conversation_history:
        return "No previous conversation."

    history_parts = []

    for message in conversation_history:
        role = message["role"].capitalize()
        content = message["content"]

        history_parts.append(
            f"{role}: {content}"
        )

    return "\n".join(history_parts)


def build_user_input(
    question: str,
    search_results: list[dict],
    conversation_history: list[dict] | None = None,
) -> str:
    conversation_context = (
        build_conversation_context(
            conversation_history
        )
    )

    knowledge_context = build_context(
        search_results
    )

    return f"""
Recent conversation:
{conversation_context}

Knowledge-base context:
{knowledge_context}

Current user question:
{question}
""".strip()


def generate_answer(
    question: str,
    search_results: list[dict],
    conversation_history: list[dict] | None = None,
) -> str:
    user_input = build_user_input(
        question=question,
        search_results=search_results,
        conversation_history=conversation_history,
    )

    if LLM_PROVIDER == "ollama":
        return "".join(local_answer_stream(user_input)).strip()
    if LLM_PROVIDER != "openai":
        raise ValueError("LLM_PROVIDER must be openai or ollama")

    response = get_openai_client().responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_INSTRUCTIONS,
        input=user_input,
    )

    return response.output_text.strip()


def generate_answer_stream(
    question: str,
    search_results: list[dict],
    conversation_history: list[dict] | None = None,
):
    user_input = build_user_input(
        question=question,
        search_results=search_results,
        conversation_history=conversation_history,
    )

    if LLM_PROVIDER == "ollama":
        yield from local_answer_stream(user_input)
        return
    if LLM_PROVIDER != "openai":
        raise ValueError("LLM_PROVIDER must be openai or ollama")

    stream = get_openai_client().responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_INSTRUCTIONS,
        input=user_input,
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta
