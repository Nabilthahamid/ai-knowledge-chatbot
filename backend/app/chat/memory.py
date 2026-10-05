import os

from dotenv import load_dotenv

from app.chat.store import get_messages


load_dotenv()


DEFAULT_MEMORY_LIMIT = int(
    os.getenv("MEMORY_MESSAGE_LIMIT", "12")
)


def load_recent_messages(
    session_id: int,
    limit: int = DEFAULT_MEMORY_LIMIT,
) -> list[dict]:
    """
    Load only the newest messages from a chat session.
    """

    messages = get_messages(session_id)

    return messages[-limit:]


def format_conversation_history(
    messages: list[dict],
) -> str:
    """
    Convert database messages into readable text.
    """

    if not messages:
        return "No previous conversation."

    formatted_messages = []

    for message in messages:
        role = message["role"].capitalize()
        content = message["content"]

        formatted_messages.append(
            f"{role}: {content}"
        )

    return "\n".join(formatted_messages)


def build_retrieval_query(
    question: str,
    conversation_history: list[dict],
) -> str:
    """
    Add recent conversation context to the
    question used for vector retrieval.
    """

    if not conversation_history:
        return question

    history_text = format_conversation_history(
        conversation_history
    )

    return f"""
Recent conversation:
{history_text}

Current question:
{question}
""".strip()