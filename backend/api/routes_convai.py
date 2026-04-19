from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from llm.chat_engine import ChatEngine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
chat_engine = ChatEngine()

# --- The input schema exactly matching convai_payload_request.json ---
class ConvAIRequest(BaseModel):
    text: str
    emotion: str = "neutral"
    source: Optional[str] = "unreal_convai"

# --- The output schema exactly matching convai_payload_response.json ---
class VoiceSettings(BaseModel):
    rate: float
    pitch: float

class ConvAIResponse(BaseModel):
    response: str
    speak_with_emotion: str
    voice_settings: VoiceSettings

@router.post("/chat", response_model=ConvAIResponse)
async def convai_chat(payload: ConvAIRequest, request: Request):
    """
    Dedicated endpoint for Unreal Engine / ConvAI integration.
    This skips the frontend JWT authentication loop because the 
    Unreal Engine client acts as a standalone autonomous system.
    """
    try:
        if not payload.text or payload.text.strip() == "":
            raise HTTPException(status_code=400, detail="Text cannot be empty.")
        
        logger.info(f"ConvAI API hit! Received text: '{payload.text}' with emotion: '{payload.emotion}'")
        
        # We hook directly into the SAME brain the React frontend uses
        response_data = await chat_engine.generate_response(
            text=payload.text,
            current_emotion=payload.emotion
        )
        
        # Build the exact Response JSON requested by the UE integration guide
        return ConvAIResponse(
            response=response_data["response"],
            speak_with_emotion=response_data["speak_with_emotion"],
            voice_settings=VoiceSettings(
                rate=response_data["voice_settings"]["rate"],
                pitch=response_data["voice_settings"]["pitch"]
            )
        )
        
    except Exception as e:
        logger.error(f"Error processing ConvAI chat request: {e}")
        # Always return a safe fallback so Unreal Engine doesn't crash the simulation
        return ConvAIResponse(
            response="I seem to be having a temporary connection issue. Please give me a moment.",
            speak_with_emotion="neutral",
            voice_settings=VoiceSettings(rate=1.0, pitch=1.0)
        )
