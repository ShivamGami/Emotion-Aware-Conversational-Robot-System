"""
m2_tasks.py
-----------
Implementation of missing tasks for Member 2:
- Task 2.5: TTS Endpoint
- Task 2.7: User Statistics
- Task 2.8: Multimodal Fusion
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from database.db import get_db
from database.models import User, Session as UserSession, Interaction
from dependencies import get_current_user
from emotion_detection.fusion import fuse_emotions

router = APIRouter(prefix="/api/m2", tags=["Member 2 Features"])

# ── Task 2.5: TTS Settings ────────────────────────────────────────────────────

EMOTION_VOICE_CONFIG = {
    "happy":     {"pitch": 1.2, "rate": 1.1, "voice_type": "energetic"},
    "sad":       {"pitch": 0.8, "rate": 0.9, "voice_type": "soft"},
    "angry":     {"pitch": 1.1, "rate": 1.2, "voice_type": "firm"},
    "surprised": {"pitch": 1.3, "rate": 1.1, "voice_type": "excited"},
    "neutral":   {"pitch": 1.0, "rate": 1.0, "voice_type": "calm"},
}

@router.get("/tts")
def get_tts_settings(emotion: str = "neutral"):
    """
    Returns text-to-speech configuration based on the current emotion.
    Frontend uses these values for the Web Speech API.
    """
    config = EMOTION_VOICE_CONFIG.get(emotion.lower(), EMOTION_VOICE_CONFIG["neutral"])
    return {
        "emotion": emotion,
        "config": config,
        "supported_api": "Web Speech API"
    }

# ── Task 2.7: User Stats ─────────────────────────────────────────────────────

@router.get("/user/stats")
def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Calculates and returns user interaction statistics.
    Includes total_memories count from ChromaDB memory store.
    """
    try:
        # Total sessions
        total_sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).count()
        
        # Total interactions (join with sessions for this user)
        total_interactions = db.query(Interaction).join(UserSession).filter(UserSession.user_id == current_user.id).count()
        
        # Favorite/Most detected emotion
        emotion_counts = db.query(
            Interaction.emotion_detected, 
            func.count(Interaction.emotion_detected)
        ).join(UserSession).filter(UserSession.user_id == current_user.id).group_by(Interaction.emotion_detected).all()
        
        counts_dict = {e: c for e, c in emotion_counts if e}
        # Ensure all standard emotions are present for the radar chart
        STANDARD_EMOTIONS = ["happy", "sad", "angry", "fearful", "surprised", "calm", "neutral"]
        full_breakdown = {e: counts_dict.get(e, 0) for e in STANDARD_EMOTIONS}
        
        favorite_emotion = "neutral"
        if emotion_counts:
            valid_counts = [x for x in emotion_counts if x[0]]
            if valid_counts:
                favorite_emotion = max(valid_counts, key=lambda x: x[1])[0]

        # Total long-term memories from ChromaDB
        total_memories = 0
        try:
            from dependencies import memory_store
            total_memories = memory_store.get_memory_count(str(current_user.id))
        except Exception:
            total_memories = 0

        return {
            "user_id": current_user.id,
            "username": current_user.username,
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
            "total_memories": total_memories,
            "favorite_emotion": favorite_emotion,
            "emotion_breakdown": full_breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

# ── Task 2.8: Multimodal Fusion ──────────────────────────────────────────────

@router.get("/fuse")
def get_fused_emotion(
    face_emo: str, 
    face_conf: float, 
    voice_emo: str, 
    voice_conf: float
):
    """
    Combines face and voice emotions using weighted confidence.
    """
    return fuse_emotions(face_emo, face_conf, voice_emo, voice_conf)
