from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.rag.routes import router as rag_router
from app.knowledge.routes import router as knowledge_router
from app.chat.routes import router as chat_router
from app.admin.routes import router as admin_router

app = FastAPI(
    title="AI Knowledge Chatbot API",
    description="Backend API for the AI knowledge-base chatbot",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(admin_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "message": "AI Knowledge Chatbot API is running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok"
    }
