"""
dependencies.py
---------------
Shared singletons and global instances for the Emotion Robot.
Used to avoid circular imports between main.py and various routers.
"""

from memory.memory_store import MemoryStore
from memory.conversation import ConversationManager
from llm.chat_engine import ChatEngine
from emotion_detection.voice_emotion import VoiceEmotionDetector
from emotion_detection.face_emotion import FaceEmotionDetector
from emotion_detection.fusion import fuse_emotions
from fastapi import Header, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import User
from auth.jwt_handler import decode_access_token

# ── Shared singletons (init once at startup) ──────────────────────────────────

# 1. Long-term memory
memory_store = MemoryStore(chroma_path="./data/chroma_db")

# 2. Short-term session manager
conv_manager = ConversationManager(memory_store=memory_store)

# 3. Conversational AI Engine
chat_engine  = ChatEngine()

# 4. Face Emotion Detector
face_detector = FaceEmotionDetector(enforce_detection=False)

# 5. Voice Emotion Detector
voice_detector = VoiceEmotionDetector()

# ── Auth Dependency ──────────────────────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Dependency to get the current authenticated user from JWT.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    
    try:
        # Extract Bearer token
        token = authorization.split(" ")[1] if " " in authorization else authorization
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Auth error: {str(e)}")
