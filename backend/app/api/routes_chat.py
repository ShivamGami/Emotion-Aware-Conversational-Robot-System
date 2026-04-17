"""
routes_chat.py
--------------
FastAPI routes for the emotion-aware conversational engine.
Exposes the ChatEngine to the frontend.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.llm import ChatEngine, ChatResponse
from app.dependencies import chat_engine  # Use the singleton from dependencies

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# ── Schemas ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id:      str
    user_name:    str
    user_message: str
    emotion:      str = "neutral"


class ChatResultResponse(BaseModel):
    reply:           str
    emotion:         str
    user_name:       str
    memories_used:   int
    extracted_facts: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResultResponse)
async def chat_with_robot(body: ChatRequest):
    """
    Primary endpoint for chatting with the Emotion Robot.
    Takes user message and current emotion, returns a personalized response.
    """
    if not body.user_message:
        raise HTTPException(status_code=400, detail="user_message is required")

    try:
        response: ChatResponse = await chat_engine.chat(
            user_id      = body.user_id,
            user_name    = body.user_name,
            user_message = body.user_message,
            emotion      = body.emotion,
        )

        return ChatResultResponse(
            reply           = response.reply,
            emotion         = response.emotion,
            user_name       = response.user_name,
            memories_used   = response.memories_used,
            extracted_facts = response.extracted_facts,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")


@router.get("/welcome")
async def get_welcome(user_id: str, user_name: str, emotion: str = "neutral"):
    """
    Returns a personalized welcome message based on user history.
    """
    message = chat_engine.get_welcome_message(user_id, user_name, emotion)
    return {"message": message}
