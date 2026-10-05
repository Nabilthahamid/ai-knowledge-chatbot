import os

from dotenv import load_dotenv

from app.chat.memory import build_retrieval_query
from app.knowledge.embedding_service import embed_query
from app.knowledge.vector_store import search_similar
from app.rag.answer_generator import (
    FALLBACK_MESSAGE,
    generate_answer,
)


load_dotenv()


MIN_SIMILARITY = float(
    os.getenv("RAG_MIN_SIMILARITY", "0.35")
)


def retrieve_context(
    question: str,
    top_k: int = 5,
    conversation_history: list[dict] | None = None,
) -> dict:
    conversation_history = conversation_history or []

    retrieval_query = build_retrieval_query(
        question=question,
        conversation_history=conversation_history,
    )

    query_embedding = embed_query(retrieval_query)

    results = search_similar(
        query_embedding=query_embedding,
        top_k=top_k,
    )

    if not results:
        return {
            "found_in_knowledge_base": False,
            "search_results": [],
            "citations": [],
        }

    best_similarity = float(
        results[0].get("similarity", 0)
    )

    if best_similarity < MIN_SIMILARITY:
        return {
            "found_in_knowledge_base": False,
            "search_results": [],
            "citations": [],
        }

    return {
        "found_in_knowledge_base": True,
        "search_results": results,
        "citations": results,
    }


def answer_question(
    question: str,
    top_k: int = 5,
    conversation_history: list[dict] | None = None,
) -> dict:
    context = retrieve_context(
        question=question,
        top_k=top_k,
        conversation_history=conversation_history,
    )

    if not context["found_in_knowledge_base"]:
        return {
            "answer": FALLBACK_MESSAGE,
            "found_in_knowledge_base": False,
            "citations": [],
        }

    answer = generate_answer(
        question=question,
        search_results=context["search_results"],
        conversation_history=conversation_history,
    )

    return {
        "answer": answer,
        "found_in_knowledge_base": True,
        "citations": context["citations"],
    }