from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_emotion import router as emotion_router
from app.memory import MemoryStore, ConversationManager   # ✅ ADD THIS

app = FastAPI(
    title="Emotion Robot v2.0 API",
    description="AI-powered emotion-aware conversational robot backend",
    version="2.0.0",
)

# ✅ ADD THIS BLOCK
memory_store = MemoryStore()
conv_manager = ConversationManager(memory_store=memory_store)

# Allow the React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(emotion_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Emotion Robot v2.0"}