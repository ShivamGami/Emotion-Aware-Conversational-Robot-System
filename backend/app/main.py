from fastapi import FastAPI
from pydantic import BaseModel
from llm.chat_engine import ChatEngine

app = FastAPI()
chat_engine = ChatEngine()

class ChatRequest(BaseModel):
    message: str
    emotion: str = "neutral"
    confidence: float = 0.0
    user_name: str = "Friend"
    conversation_history: list = []
    memories: list = []

@app.post("/api/chat")
async def chat(req: ChatRequest):
    result = chat_engine.get_response(
        user_message=req.message,
        emotion=req.emotion,
        confidence=req.confidence,
        user_name=req.user_name,
        conversation_history=req.conversation_history,
        memories=req.memories,
    )
    return result