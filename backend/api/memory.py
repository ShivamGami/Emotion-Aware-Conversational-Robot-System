"""
memory.py
---------
FastAPI routers for memory management.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from dependencies import memory_store, get_current_user
from database.models import User
from database.db import get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["Memory"])

@router.get("/recent")
def get_recent_memories(n: int = 10, current_user: User = Depends(get_current_user)):
    """Returns recent memories from ChromaDB."""
    try:
        user_id = str(current_user.id)
        memories = memory_store.get_recent_memories(user_id, n=n)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Failed to get recent memories: {e}")
        return {"memories": [], "error": str(e)}

@router.post("/store")
def store_memory(
    text: str,
    importance: str = "medium",
    emotion: str = "neutral",
    current_user: User = Depends(get_current_user)
):
    """Store a memory in ChromaDB for the current user."""
    try:
        user_id = str(current_user.id)
        memory_id = memory_store.store_memory(
            user_id=user_id,
            text=text,
            emotion=emotion,
            importance=importance
        )
        return {"status": "stored", "id": memory_id}
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/count")
def get_memory_count(current_user: User = Depends(get_current_user)):
    """Returns total number of memories for the current user from ChromaDB."""
    try:
        user_id = str(current_user.id)
        count = memory_store.get_memory_count(user_id)
        return {"count": count, "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to count memories: {e}")
        return {"count": 0, "error": str(e)}
