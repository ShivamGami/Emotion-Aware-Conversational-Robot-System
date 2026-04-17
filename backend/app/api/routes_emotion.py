"""
routes_emotion.py  (Task 1.6 updated)
--------------------------------------
FastAPI routes for face emotion detection.

Endpoints
─────────
POST /api/detect/face         — base64 image → smoothed emotion (Task 1.1)
POST /api/compare_models      — base64 image → DeepFace vs Custom CNN side-by-side (Task 1.6)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.emotion_detection.face import FaceEmotionDetector, EmotionResult

router = APIRouter(prefix="/api", tags=["Emotion Detection"])

# ── Shared detector instances ──────────────────────────────────────────────
# Primary detector: DeepFace + smoother (used for normal webcam stream)
_detector_deepface = FaceEmotionDetector(backend="deepface")

# Comparison detector: Custom CNN (falls back to DeepFace if .pth not found)
_detector_cnn = FaceEmotionDetector(backend="custom_cnn")


# ── Request / Response schemas ─────────────────────────────────────────────

class FaceEmotionRequest(BaseModel):
    image_base64: str           # data:image/jpeg;base64,... OR raw base64


class FaceEmotionResponse(BaseModel):
    dominant_emotion:   str
    confidence:         float
    all_emotions:       dict[str, float]
    landmarks_detected: bool
    processing_time_ms: float
    smoothed:           bool    # True when smoother window is warm


class ModelResult(BaseModel):
    dominant_emotion:  str
    confidence:        float
    all_emotions:      dict[str, float]
    inference_ms:      float
    model_available:   bool = True


class CompareModelsResponse(BaseModel):
    deepface:    ModelResult
    custom_cnn:  ModelResult
    agreement:   bool           # True when both models agree on the emotion


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/detect/face", response_model=FaceEmotionResponse)
async def detect_face_emotion(body: FaceEmotionRequest):
    """
    Receive a base64-encoded webcam frame from the frontend and return the
    smoothed (5-frame rolling mode) dominant emotion with confidence scores.
    """
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    result: EmotionResult = _detector_deepface.detect_from_base64(body.image_base64)

    return FaceEmotionResponse(
        dominant_emotion   = result.dominant_emotion,
        confidence         = result.confidence,
        all_emotions       = result.all_emotions,
        landmarks_detected = result.landmarks_detected,
        processing_time_ms = result.processing_time_ms,
        smoothed           = result.smoothed,
    )


@router.post("/compare_models", response_model=CompareModelsResponse)
async def compare_models(body: FaceEmotionRequest):
    """
    Run the same base64 webcam frame through **both** DeepFace and the Custom
    FER-2013 CNN and return their results side-by-side.

    This endpoint is intended for hackathon judges to visually compare how the
    two models differ on the same input.
    """
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    # Decode image once, reuse the numpy array for both models
    import base64
    import cv2
    import numpy as np

    try:
        b64 = body.image_base64
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        img_bytes = base64.b64decode(b64)
        np_arr    = np.frombuffer(img_bytes, dtype=np.uint8)
        frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            raise ValueError("Could not decode image")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {exc}")

    # Run both models
    comparison = _detector_cnn.compare_both_models(frame)

    df  = comparison["deepface"]
    cnn = comparison["custom_cnn"]

    return CompareModelsResponse(
        deepface=ModelResult(
            dominant_emotion = df["dominant_emotion"],
            confidence       = df["confidence"],
            all_emotions     = df["all_emotions"],
            inference_ms     = df["inference_ms"],
            model_available  = True,
        ),
        custom_cnn=ModelResult(
            dominant_emotion = cnn["dominant_emotion"],
            confidence       = cnn["confidence"],
            all_emotions     = cnn["all_emotions"],
            inference_ms     = cnn["inference_ms"],
            model_available  = cnn["model_available"],
        ),
        agreement = comparison["agreement"],
    )