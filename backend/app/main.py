from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_emotion import router as emotion_router
from app.api.context_graph import router as graph_router
from app.api.explainability import router as explain_router
from app.api.routes_chat import router as chat_router
from app.memory import MemoryStore, ConversationManager
from app.llm import ChatEngine

app = FastAPI(
    title="Emotion Robot v2.0 API",
    description="AI-powered emotion-aware conversational robot backend",
    version="2.0.0",
)

from app.dependencies import memory_store, conv_manager, chat_engine

# Allow the React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(emotion_router)
app.include_router(graph_router)
app.include_router(explain_router)
app.include_router(chat_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Emotion Robot v2.0"}