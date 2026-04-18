from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import requests
import os
from dotenv import load_dotenv

from sqlalchemy.orm import Session
from database.db import get_db
from llm.chat_engine import ChatEngine
from dependencies import chat_engine, get_current_user
from database.models import User

load_dotenv()

router = APIRouter(prefix="/api/chat", tags=["Chat"])
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://172.21.205.94:8000/state")

# ── Schemas ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    text: str
    emotion: str = "neutral"
    user_id: Optional[int] = None


class ChatResultResponse(BaseModel):
    response: str
    speak_with_emotion: str
    voice_settings: Dict[str, float]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResultResponse)
async def chat_with_robot(
    body: ChatRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Overhauled chat endpoint: LLM + Bridge Sync + Interaction Logging.
    """
    if not body.text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        from dependencies import conv_manager
        user_id_str = str(current_user.id)
        history_obj = conv_manager.get_or_create(user_id_str)
        
        # 0. Ensure user has an active interaction session
        from database.models import Interaction, Session as UserSession
        session = db.query(UserSession).filter(UserSession.user_id == current_user.id).order_by(UserSession.start_time.desc()).first()
        if not session:
            session = UserSession(user_id=current_user.id)
            db.add(session)
            db.commit()
            db.refresh(session)

        # 1. Get LLM response
        history_msgs = [
            {"role": msg.role, "content": msg.text} 
            for msg in history_obj.get_recent_messages(5)
        ]

        llm_result = chat_engine.get_response(
            user_message=body.text,
            emotion=body.emotion,
            history=history_msgs,
            user_name=current_user.username or "Friend"
        )
        
        reply_text = llm_result["response"]
        
        # 2. Sync with Bridge (MetaHuman / ROS2)
        try:
            requests.post(f"{BRIDGE_URL.replace('/state', '')}/test/emotion/{body.emotion}", timeout=1)
            requests.post(f"{BRIDGE_URL.replace('/state', '')}/speak/{body.emotion}", timeout=1)
        except Exception as e:
            print(f"⚠️  Bridge sync failed: {e}")

        # 3. Update local history
        history_obj.add_user_message(body.text, body.emotion)
        history_obj.add_robot_message(reply_text, body.emotion)

        # 4. Save to Database for Analytics
        interaction = Interaction(
            session_id=session.id,
            user_message=body.text,
            robot_response=reply_text,
            emotion_detected=body.emotion
        )
        db.add(interaction)
        db.commit()

        # 5. Save to Long-Term Memory (ChromaDB)
        try:
            from dependencies import memory_store
            memory_store.store_memory(
                user_id=user_id_str,
                text=body.text,
                emotion=body.emotion,
                importance="medium"
            )
        except Exception as e:
            print(f"⚠️  Memory storage failed: {e}")

        return ChatResultResponse(
            response=reply_text,
            speak_with_emotion=body.emotion,
            voice_settings=llm_result["voice_settings"]
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")


@router.get("/welcome")
async def get_welcome(current_user: User = Depends(get_current_user), emotion: str = "neutral"):
    """
    Returns a personalized welcome message based on user history.
    """
    user_id = str(current_user.id)
    user_name = current_user.username
    # Simple logic for now as ChatEngine doesn't have get_welcome_message in view
    return {"message": f"Welcome back, {user_name}! You look {emotion} today."}
