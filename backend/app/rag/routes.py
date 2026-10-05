from fastapi import APIRouter

from app.knowledge.embedding_service import embed_query
from app.knowledge.vector_store import search_similar
from app.rag.answer_generator import FALLBACK_MESSAGE, generate_answer
from app.rag.schemas import AskRequest, AskResponse
from app.rag.service import MIN_SIMILARITY


router = APIRouter(
    prefix="/api/v1/rag",
    tags=["RAG"],
)


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    query_embedding = embed_query(request.question)
    results = search_similar(
        query_embedding=query_embedding,
        top_k=request.top_k,
    )

    if (
        not results
        or float(results[0].get("similarity", 0)) < MIN_SIMILARITY
    ):
        return {
            "answer": FALLBACK_MESSAGE,
            "found_in_knowledge_base": False,
            "citations": [],
        }

    answer = generate_answer(request.question, results)

    return {
        "answer": answer,
        "found_in_knowledge_base": True,
        "citations": results,
    }
