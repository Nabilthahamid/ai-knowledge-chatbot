from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )


class Citation(BaseModel):
    id: int
    document_name: str
    chunk_index: int
    page_number: int | None
    text: str
    similarity: float


class AskResponse(BaseModel):
    answer: str
    found_in_knowledge_base: bool
    citations: list[Citation]