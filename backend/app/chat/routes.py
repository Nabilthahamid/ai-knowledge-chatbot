import json
import logging
import httpx

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import AuthenticationError, RateLimitError

from app.chat.memory import load_recent_messages
from app.chat.schemas import (
    CreateSessionRequest,
    SendMessageRequest,
)
from app.chat.store import (
    add_message,
    create_session,
    get_messages,
    list_sessions,
    session_exists,
)
from app.rag.answer_generator import (
    FALLBACK_MESSAGE,
    generate_answer_stream,
)
from app.rag.service import answer_question, retrieve_context


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Chat"],
)
logger = logging.getLogger(__name__)


def answer_error_message(error: Exception) -> str:
    if isinstance(error, httpx.ConnectError):
        return "The local AI service is unavailable. Start Ollama and retry."
    if isinstance(error, httpx.TimeoutException):
        return "The local AI model took too long to respond. Please retry."
    if isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code == 404:
            return "The local AI model is not installed. Download the configured Ollama model and retry."
        return "The local AI service could not generate an answer. Check its logs and retry."
    if isinstance(error, RateLimitError):
        body = error.body if isinstance(error.body, dict) else {}
        details = body.get("error", body)
        code = details.get("code") if isinstance(details, dict) else None
        if code in {"credit_balance_exhausted", "insufficient_quota"}:
            return (
                "The AI API account has no available credits or quota. "
                "Check billing at https://platform.openai.com/settings/organization/billing/ "
                "for the account configured in backend/.env, then retry."
            )
        return "The AI API rate limit was reached. Please wait a moment and retry."
    if isinstance(error, AuthenticationError):
        return "The AI API key is invalid. Update OPENAI_API_KEY in backend/.env and restart the backend."
    return "The answer could not be generated. Please retry."


@router.post("/sessions", status_code=201)
def create_chat_session(
    request: CreateSessionRequest,
):
    return create_session(
        title=request.title
    )


@router.get("/sessions")
def get_chat_sessions():
    return {
        "sessions": list_sessions()
    }


@router.get("/sessions/{session_id}/messages")
def get_chat_history(session_id: int):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )

    return {
        "session_id": session_id,
        "messages": get_messages(session_id),
    }


@router.post("/sessions/{session_id}/messages")
def send_chat_message(
    session_id: int,
    request: SendMessageRequest,
):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )

    # Load previous messages before saving
    # the current user message.
    conversation_history = (
        load_recent_messages(session_id)
    )

    user_message = add_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )

    result = answer_question(
        question=request.message,
        top_k=request.top_k,
        conversation_history=conversation_history,
    )

    assistant_message = add_message(
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        citations=result["citations"],
    )

    return {
        "session_id": session_id,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "answer": result["answer"],
        "found_in_knowledge_base": result[
            "found_in_knowledge_base"
        ],
        "citations": result["citations"],
    }


def make_sse_event(event_name: str, data: dict) -> str:
    return (
        f"event: {event_name}\n"
        f"data: {json.dumps(data, default=str)}\n\n"
    )


@router.post("/sessions/{session_id}/messages/stream")
def stream_chat_message(
    session_id: int,
    request: SendMessageRequest,
):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )

    conversation_history = load_recent_messages(session_id)
    user_message = add_message(
        session_id=session_id,
        role="user",
        content=request.message,
    )
    context = retrieve_context(
        question=request.message,
        top_k=request.top_k,
        conversation_history=conversation_history,
    )

    def event_generator():
        if not context["found_in_knowledge_base"]:
            assistant_message = add_message(
                session_id=session_id,
                role="assistant",
                content=FALLBACK_MESSAGE,
                citations=[],
            )
            yield make_sse_event(
                "done",
                {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "answer": FALLBACK_MESSAGE,
                    "found_in_knowledge_base": False,
                    "citations": [],
                },
            )
            return

        complete_answer = []

        try:
            for token in generate_answer_stream(
                question=request.message,
                search_results=context["search_results"],
                conversation_history=conversation_history,
            ):
                complete_answer.append(token)
                yield make_sse_event("token", {"text": token})

            final_answer = "".join(complete_answer)
            assistant_message = add_message(
                session_id=session_id,
                role="assistant",
                content=final_answer,
                citations=context["citations"],
            )
            yield make_sse_event(
                "done",
                {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "answer": final_answer,
                    "found_in_knowledge_base": True,
                    "citations": context["citations"],
                },
            )
        except Exception as error:
            logger.exception("Chat answer generation failed for session %s", session_id)
            yield make_sse_event(
                "error",
                {"message": answer_error_message(error)},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
