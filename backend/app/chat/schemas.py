from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = Field(
        default="New conversation",
        min_length=1,
        max_length=120,
    )


class SendMessageRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )