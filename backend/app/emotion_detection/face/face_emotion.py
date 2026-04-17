"""
Face Emotion Detector
Uses DeepFace for emotion recognition + MediaPipe for face landmark detection.
Member 1 — Task 1.1
"""

import base64
import io
import logging
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from deepface import DeepFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class FaceRegion:
    x: int
    y: int
    w: int
    h: int
    confidence: float


@dataclass
class EmotionResult:
    dominant_emotion: str
    confidence: float                    # 0.0 – 1.0
    all_emotions: dict[str, float]       # e.g. {"happy": 0.92, "sad": 0.03, …}
    face_region: Optional[FaceRegion]
    landmarks_detected: bool
    processing_time_ms: float
    raw_frame_shape: Optional[tuple]


# ── Detector Class ────────────────────────────────────────────────────────────

class FaceEmotionDetector:
    """
    Detects facial emotions from images / video frames.

    Pipeline
    --------
    1. MediaPipe FaceMesh  →  quick presence check + landmarks
    2. DeepFace            →  emotion probabilities (uses its own internal
                              face-detector so no extra crop step needed)
    3. Merge results       →  return EmotionResult
    """

    # All 7 emotions DeepFace can return
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        deepface_backend: str = "opencv",   # fastest; swap to "retinaface" for accuracy
        enforce_detection: bool = False,    # False → return neutral on no-face instead of crash
    ):
        self.deepface_backend = deepface_backend
        self.enforce_detection = enforce_detection

        # OpenCV Haar Cascade for quick face presence check
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        logger.info("FaceEmotionDetector initialised ✓")

    # ── Public API ─────────────────────────────────────────────────────────

    def detect_from_frame(self, frame: np.ndarray) -> EmotionResult:
        """
        Detect emotion from a single BGR (OpenCV) frame.
        This is the primary method called from the FastAPI endpoint.
        """
        start = time.perf_counter()

        if frame is None or frame.size == 0:
            return self._empty_result(0.0)

        # Step 1 — MediaPipe landmarks
        landmarks_detected, face_region = self._run_mediapipe(frame)

        # Step 2 — DeepFace emotion analysis
        emotion_data = self._run_deepface(frame)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if emotion_data is None:
            return self._empty_result(elapsed_ms, face_region, landmarks_detected)

        return EmotionResult(
            dominant_emotion=emotion_data["dominant_emotion"],
            confidence=emotion_data["confidence"],
            all_emotions=emotion_data["all_emotions"],
            face_region=face_region,
            landmarks_detected=landmarks_detected,
            processing_time_ms=round(elapsed_ms, 2),
            raw_frame_shape=frame.shape,
        )

    def detect_from_base64(self, b64_string: str) -> EmotionResult:
        """
        Decode a base64-encoded JPEG/PNG sent from the React webcam component
        and run detection.  Called by the FastAPI endpoint.
        """
        try:
            # Strip data-URI header if present  (data:image/jpeg;base64,...)
            if "," in b64_string:
                b64_string = b64_string.split(",", 1)[1]

            img_bytes = base64.b64decode(b64_string)
            np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                raise ValueError("cv2.imdecode returned None — bad image bytes")

            return self.detect_from_frame(frame)

        except Exception as exc:
            logger.error("detect_from_base64 failed: %s", exc)
            return self._empty_result(0.0)

    def detect_from_image_path(self, path: str) -> EmotionResult:
        """Utility for local testing."""
        frame = cv2.imread(path)
        if frame is None:
            raise FileNotFoundError(f"Could not read image at: {path}")
        return self.detect_from_frame(frame)

    def annotate_frame(self, frame: np.ndarray, result: EmotionResult) -> np.ndarray:
        """
        Draw emotion label + confidence bar on a copy of the frame.
        Useful for debugging / live-preview endpoint.
        """
        annotated = frame.copy()

        # Bounding box
        if result.face_region:
            r = result.face_region
            cv2.rectangle(
                annotated,
                (r.x, r.y),
                (r.x + r.w, r.y + r.h),
                (0, 255, 0),
                2,
            )

        # Emotion label
        label = f"{result.dominant_emotion.upper()}  {result.confidence:.0%}"
        cv2.putText(
            annotated, label, (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2,
        )

        # Mini bar chart for all emotions
        y_offset = 80
        for emotion, prob in sorted(result.all_emotions.items(), key=lambda x: -x[1]):
            bar_len = int(prob * 150)
            cv2.rectangle(annotated, (20, y_offset), (20 + bar_len, y_offset + 14), (0, 200, 255), -1)
            cv2.putText(annotated, f"{emotion[:3]} {prob:.0%}", (180, y_offset + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20

        return annotated

    def release(self):
        """Call when shutting down."""
        pass

    # ── Private Helpers ────────────────────────────────────────────────────

    def _run_mediapipe(self, frame: np.ndarray) -> tuple[bool, Optional[FaceRegion]]:
        """Quick presence check using OpenCV Haar Cascades (formerly MediaPipe)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )

        if len(faces) == 0:
            return False, None

        x, y, w, h = faces[0]
        face_region = FaceRegion(x=int(x), y=int(y), w=int(w), h=int(h), confidence=1.0)

        return True, face_region

    def _run_deepface(self, frame: np.ndarray) -> Optional[dict]:
        try:
            analysis = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                detector_backend=self.deepface_backend,
                enforce_detection=self.enforce_detection,
                silent=True,
            )

            # DeepFace returns a list when multiple faces found; take the first
            if isinstance(analysis, list):
                analysis = analysis[0]

            raw_emotions: dict = analysis["emotion"]          # raw scores (0-100)
            dominant: str = analysis["dominant_emotion"]

            # Normalise scores to 0-1
            total = sum(raw_emotions.values()) or 1
            normalised = {k: round(v / total, 4) for k, v in raw_emotions.items()}
            confidence = normalised.get(dominant, 0.0)

            return {
                "dominant_emotion": dominant,
                "confidence": confidence,
                "all_emotions": normalised,
            }

        except Exception as exc:
            logger.warning("DeepFace analysis failed: %s", exc)
            return None

    def _empty_result(
        self,
        elapsed_ms: float,
        face_region: Optional[FaceRegion] = None,
        landmarks: bool = False,
    ) -> EmotionResult:
        """Return a safe default when no face / error occurs."""
        return EmotionResult(
            dominant_emotion="neutral",
            confidence=0.0,
            all_emotions={e: 0.0 for e in self.EMOTIONS},
            face_region=face_region,
            landmarks_detected=landmarks,
            processing_time_ms=elapsed_ms,
            raw_frame_shape=None,
        )