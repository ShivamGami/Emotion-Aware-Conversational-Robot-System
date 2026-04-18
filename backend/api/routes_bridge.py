from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/bridge", tags=["Bridge"])
BRIDGE_URL = os.getenv("BRIDGE_URL", "http://172.21.205.94:8000/state")

class SpeechStateRequest(BaseModel):
    is_speaking: bool
    text: Optional[str] = ""

@router.post("/speech_state")
async def update_speech_state(body: SpeechStateRequest):
    """
    Notify the bridge about current speech status for lip sync trigger.
    """
    try:
        # If the bridge accepts a generic state update, we send it there.
        # Based on the teammate's email, we also have specific /speak endpoints.
        
        bridge_base = BRIDGE_URL.replace('/state', '')
        
        if body.is_speaking:
            # Trigger 'starting' to speak
            requests.post(f"{bridge_base}/speak/neutral", json={"text": body.text}, timeout=1)
        else:
            # Maybe a stop endpoint exists? If not, we just log it.
            # requests.post(f"{bridge_base}/stop", timeout=1)
            pass
            
        return {"status": "success", "is_speaking": body.is_speaking}
    except Exception as e:
        # Don't fail the whole frontend if bridge is down, just log
        print(f"⚠️ Bridge communication error: {e}")
        return {"status": "error", "message": str(e)}
