"""
face_emotion.py  (Task 1.6 — Custom CNN Integration)
-----------------------------------------------------
Updated FaceEmotionDetector that supports:
  1. Original DeepFace inference path (unchanged from Task 1.1).
  2. Custom FER-2013 CNN inference path (PyTorch .pth weights).
  3. EmotionSmoother — rolling 5-frame mode filter to eliminate flickering.

Performance Fixes (v2.1):
  - Default backend switched to "opencv" (stable on Windows, no native issues).
  - SMOOTHER_WINDOW increased to 5 for better stability.
  - Added `no_face_detected` flag so frontend can suppress noise readings.
  - DeepFace called with silent=True and minimal actions for speed.

Backend: FastAPI | Member 1 — AI & Memory Engineer
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mode
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from deepface import DeepFace

from .fer_cnn import FERCustomCNN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
FER_IMG_SIZE = 48           # FER-2013 canonical input size (48×48 grayscale)
SMOOTHER_WINDOW = 5         # 5-frame rolling window for stable output

# Default path to look for custom weights (relative to this file)
_DEFAULT_WEIGHTS = Path(__file__).parent / "fer_cnn.pth"


# ── Data classes ──────────────────────────────────────────────────────────────

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
    confidence: float                   # 0.0 – 1.0
    all_emotions: dict[str, float]      # e.g. {"happy": 0.92, "sad": 0.03, …}
    face_region: Optional[FaceRegion]
    landmarks_detected: bool
    processing_time_ms: float
    raw_frame_shape: Optional[tuple]
    smoothed: bool = False              # True when EmotionSmoother result returned
    no_face_detected: bool = False      # True when no face found in frame


# ── EmotionSmoother ───────────────────────────────────────────────────────────

class EmotionSmoother:
    """
    Rolling-window mode filter to stabilise per-frame emotion predictions.

    Instead of returning the raw label for each frame (which causes the robot's
    displayed mood to flicker), this class keeps the last `window` predictions
    and returns the most-frequent (mode) emotion across that window.
    """

    def __init__(self, window: int = SMOOTHER_WINDOW) -> None:
        self._window = window
        self._history: deque[str] = deque(maxlen=window)

    def update(self, raw_emotion: str) -> str:
        """
        Push the latest raw emotion label and return the smoothed label.
        If the window is not yet full, returns the mode of whatever is stored.
        """
        self._history.append(raw_emotion)
        try:
            return mode(self._history)
        except Exception:
            return raw_emotion

    def reset(self) -> None:
        """Clear the rolling window (e.g. on session end)."""
        self._history.clear()

    @property
    def is_warm(self) -> bool:
        """True once the window is fully populated."""
        return len(self._history) >= self._window


# ── Main detector class ───────────────────────────────────────────────────────

class FaceEmotionDetector:
    """
    Unified face-emotion detector supporting two inference backends:

    Backend: "deepface" (default)
        Uses DeepFace + OpenCV Haar Cascades. 
        DeepFace detector backend set to "opencv" for Windows stability.
    Backend: "custom_cnn"
        Uses the FER-2013 custom PyTorch CNN loaded from a .pth weights file.

    Both paths feed through EmotionSmoother for flicker-free output.
    """

    EMOTIONS = EMOTIONS

    def __init__(
        self,
        backend: str = "deepface",
        weights_path: str | Path = _DEFAULT_WEIGHTS,
        deepface_detector: str = "opencv",   # Changed from mediapipe → opencv (stable on Windows)
        enforce_detection: bool = False,
        smoother_window: int = SMOOTHER_WINDOW,
    ) -> None:

        self.deepface_backend = deepface_detector
        self.enforce_detection = enforce_detection
        self._backend = backend

        # ── OpenCV Haar Cascade (face presence check + fallback) ─────────────
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # ── Custom CNN setup ─────────────────────────────────────────────────
        self._cnn: Optional[FERCustomCNN] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if backend == "custom_cnn":
            self._cnn = self._load_cnn(Path(weights_path))
            if self._cnn is None:
                logger.warning(
                    "Custom CNN weights not found at '%s'. "
                    "Falling back to DeepFace backend.", weights_path
                )
                self._backend = "deepface"

        # ── Smoother ─────────────────────────────────────────────────────────
        self._smoother = EmotionSmoother(window=smoother_window)

        logger.info(
            "FaceEmotionDetector initialized [OK] [backend=%s | deepface_detector=%s | device=%s]",
            self._backend,
            self.deepface_backend,
            self._device,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def detect_from_frame(self, frame: np.ndarray) -> EmotionResult:
        """
        Detect emotion from a single BGR (OpenCV) frame.
        Results are automatically smoothed over the last 5 frames.
        Returns no_face_detected=True when no face is present.
        """
        start = time.perf_counter()

        if frame is None or frame.size == 0:
            return self._empty_result(0.0, no_face=True)

        # Quick face-presence check via Haar Cascade (fast, ~5ms)
        landmarks_detected, face_region = self._run_haar(frame)

        # If no face detected, return quickly without running heavy ML model
        if not landmarks_detected:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return self._empty_result(elapsed_ms, face_region=None, no_face=True)

        # Inference — only runs when a face is confirmed present
        if self._backend == "custom_cnn" and self._cnn is not None:
            emotion_data = self._run_custom_cnn(frame)
        else:
            emotion_data = self._run_deepface(frame)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if emotion_data is None:
            return self._empty_result(elapsed_ms, face_region, landmarks_detected)

        # ── Apply smoother ───────────────────────────────────────────────────
        raw_emotion = emotion_data["dominant_emotion"]
        smoothed_emotion = self._smoother.update(raw_emotion)

        # Rebuild confidence: use smoothed label's probability from all_emotions
        smoothed_confidence = emotion_data["all_emotions"].get(smoothed_emotion, emotion_data["confidence"])

        return EmotionResult(
            dominant_emotion=smoothed_emotion,
            confidence=smoothed_confidence,
            all_emotions=emotion_data["all_emotions"],
            face_region=face_region,
            landmarks_detected=landmarks_detected,
            processing_time_ms=round(elapsed_ms, 2),
            raw_frame_shape=frame.shape,
            smoothed=self._smoother.is_warm,
            no_face_detected=False,
        )

    def detect_from_base64(self, b64_string: str) -> EmotionResult:
        """
        Decode a base64-encoded JPEG/PNG from the React webcam and run detection.
        """
        try:
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
            return self._empty_result(0.0, no_face=True)

    def detect_from_image_path(self, path: str) -> EmotionResult:
        """Utility for local testing."""
        frame = cv2.imread(path)
        if frame is None:
            raise FileNotFoundError(f"Could not read image at: {path}")
        return self.detect_from_frame(frame)

    def compare_both_models(self, frame: np.ndarray) -> dict:
        """
        Run the same frame through BOTH DeepFace and Custom CNN independently.
        Returns a dict with results from each model side-by-side.
        """
        start_df = time.perf_counter()
        deepface_data = self._run_deepface(frame)
        df_ms = (time.perf_counter() - start_df) * 1000

        cnn_data = None
        cnn_ms = 0.0
        if self._cnn is not None:
            start_cnn = time.perf_counter()
            cnn_data = self._run_custom_cnn(frame)
            cnn_ms = (time.perf_counter() - start_cnn) * 1000

        df_emotion   = deepface_data["dominant_emotion"] if deepface_data else "neutral"
        df_confidence = deepface_data["confidence"]      if deepface_data else 0.0
        cnn_emotion   = cnn_data["dominant_emotion"]     if cnn_data      else "unavailable"
        cnn_confidence = cnn_data["confidence"]          if cnn_data      else 0.0

        return {
            "deepface": {
                "dominant_emotion": df_emotion,
                "confidence":       round(df_confidence, 4),
                "all_emotions":     deepface_data["all_emotions"] if deepface_data else {},
                "inference_ms":     round(df_ms, 2),
            },
            "custom_cnn": {
                "dominant_emotion": cnn_emotion,
                "confidence":       round(cnn_confidence, 4),
                "all_emotions":     cnn_data["all_emotions"] if cnn_data else {},
                "inference_ms":     round(cnn_ms, 2),
                "model_available":  self._cnn is not None,
            },
            "agreement": df_emotion == cnn_emotion,
        }

    def annotate_frame(self, frame: np.ndarray, result: EmotionResult) -> np.ndarray:
        """Draw bounding box + emotion label on a copy of the frame."""
        annotated = frame.copy()

        if result.face_region:
            r = result.face_region
            cv2.rectangle(annotated, (r.x, r.y), (r.x + r.w, r.y + r.h), (0, 255, 0), 2)

        label = f"{result.dominant_emotion.upper()}  {result.confidence:.0%}"
        cv2.putText(annotated, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        y_offset = 80
        for emotion, prob in sorted(result.all_emotions.items(), key=lambda x: -x[1]):
            bar_len = int(prob * 150)
            cv2.rectangle(annotated, (20, y_offset), (20 + bar_len, y_offset + 14), (0, 200, 255), -1)
            cv2.putText(annotated, f"{emotion[:3]} {prob:.0%}", (180, y_offset + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20

        return annotated

    def reset_smoother(self) -> None:
        """Reset the rolling window (e.g. when a new user session starts)."""
        self._smoother.reset()

    def release(self) -> None:
        """Clean-up hook (called on app shutdown)."""
        pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_cnn(self, path: Path) -> Optional[FERCustomCNN]:
        """Load FERCustomCNN weights from a .pth file. Returns None on failure."""
        if not path.exists():
            logger.warning("CNN weights file not found: %s", path)
            return None
        try:
            model = FERCustomCNN(num_classes=len(EMOTIONS))
            state_dict = torch.load(str(path), map_location=self._device, weights_only=True)
            model.load_state_dict(state_dict)
            model.to(self._device)
            model.eval()
            logger.info("Custom CNN loaded from '%s' on %s ✓", path.name, self._device)
            return model
        except Exception as exc:
            logger.error("Failed to load CNN weights: %s", exc)
            return None

    def _run_haar(self, frame: np.ndarray) -> tuple[bool, Optional[FaceRegion]]:
        """Quick face-presence check using OpenCV Haar Cascades (~5ms)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Tuned parameters: faster detection with good precision
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(48, 48),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(faces) == 0:
            return False, None

        x, y, w, h = faces[0]
        return True, FaceRegion(x=int(x), y=int(y), w=int(w), h=int(h), confidence=1.0)

    def _run_deepface(self, frame: np.ndarray) -> Optional[dict]:
        """Run DeepFace emotion analysis. Returns normalised dict or None."""
        try:
            analysis = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                detector_backend=self.deepface_backend,
                enforce_detection=self.enforce_detection,
                silent=True,
            )

            if isinstance(analysis, list):
                analysis = analysis[0]

            raw_emotions: dict = analysis["emotion"]
            dominant: str      = analysis["dominant_emotion"]

            total = sum(raw_emotions.values()) or 1
            normalised = {k: round(v / total, 4) for k, v in raw_emotions.items()}

            return {
                "dominant_emotion": dominant,
                "confidence":       normalised.get(dominant, 0.0),
                "all_emotions":     normalised,
            }

        except Exception as exc:
            logger.warning("DeepFace analysis failed: %s", exc)
            return None

    def _run_custom_cnn(self, frame: np.ndarray) -> Optional[dict]:
        """
        Pre-process frame for FER-2013 and run through the custom PyTorch CNN.
        Returns normalised dict or None.
        """
        if self._cnn is None:
            return None

        try:
            # ── Pre-process: grayscale → 48×48 → normalise to [0,1] ─────────
            gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (FER_IMG_SIZE, FER_IMG_SIZE))
            tensor  = torch.from_numpy(resized).float() / 255.0           # (48, 48)
            tensor  = tensor.unsqueeze(0).unsqueeze(0)                    # (1, 1, 48, 48)
            tensor  = tensor.to(self._device)

            # ── Inference ─────────────────────────────────────────────────────
            with torch.no_grad():
                probs = self._cnn.predict_proba(tensor)[0]                # (7,)

            probs_list  = probs.cpu().numpy().tolist()
            dominant_idx = int(np.argmax(probs_list))
            dominant     = EMOTIONS[dominant_idx]
            all_emotions = {EMOTIONS[i]: round(float(probs_list[i]), 4) for i in range(len(EMOTIONS))}

            return {
                "dominant_emotion": dominant,
                "confidence":       round(float(probs_list[dominant_idx]), 4),
                "all_emotions":     all_emotions,
            }

        except Exception as exc:
            logger.error("Custom CNN inference failed: %s", exc)
            return None

    def _empty_result(
        self,
        elapsed_ms: float,
        face_region: Optional[FaceRegion] = None,
        landmarks: bool = False,
        no_face: bool = False,
    ) -> EmotionResult:
        """Return a safe default when no face is detected or an error occurs."""
        return EmotionResult(
            dominant_emotion  = "neutral",
            confidence        = 0.0,
            all_emotions      = {e: 0.0 for e in EMOTIONS},
            face_region       = face_region,
            landmarks_detected = landmarks,
            processing_time_ms = elapsed_ms,
            raw_frame_shape    = None,
            smoothed           = False,
            no_face_detected   = no_face,
        )