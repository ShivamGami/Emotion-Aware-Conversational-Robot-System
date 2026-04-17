"""
FastAPI routes for face emotion detection.
POST /api/detect/face  — accepts base64 image from React webcam
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.emotion_detection.face import FaceEmotionDetector, EmotionResult

router = APIRouter(prefix="/api/detect", tags=["Emotion Detection"])

# Single shared instance — loads models once at startup
_detector = FaceEmotionDetector()


# ── Schemas ────────────────────────────────────────────────────────────────

class FaceEmotionRequest(BaseModel):
    image_base64: str          # data:image/jpeg;base64,... OR raw base64


class FaceEmotionResponse(BaseModel):
    dominant_emotion: str
    confidence: float
    all_emotions: dict[str, float]
    landmarks_detected: bool
    processing_time_ms: float


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/face", response_model=FaceEmotionResponse)
async def detect_face_emotion(body: FaceEmotionRequest):
    """
    Receive a base64-encoded webcam frame from the frontend,
    return the detected emotion with confidence scores.
    """
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    result: EmotionResult = _detector.detect_from_base64(body.image_base64)

    return FaceEmotionResponse(
        dominant_emotion=result.dominant_emotion,
        confidence=result.confidence,
        all_emotions=result.all_emotions,
        landmarks_detected=result.landmarks_detected,
        processing_time_ms=result.processing_time_ms,
    )