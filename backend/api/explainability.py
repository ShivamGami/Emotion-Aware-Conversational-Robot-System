"""
explainability.py  —  Task 1.7
--------------------------------
Grad-CAM explainability endpoint for the custom FER-2013 CNN.

What is Grad-CAM?
  Gradient-weighted Class Activation Mapping visualises which spatial regions
  of the input image most influenced the CNN's predicted emotion class.
  It hooks into the last convolutional layer's gradients to produce a heatmap.

Endpoint
--------
POST /api/explain_emotion
  Body : { "image_base64": "...", "emotion": "happy" (optional) }
  Returns : { "heatmap_base64": "...", "predicted_emotion": "...",
              "confidence": 0.xx, "target_emotion": "..." }

The returned heatmap_base64 is a JPEG with the Grad-CAM overlay rendered on
top of the original image — ready to display in the React frontend or show
to hackathon judges.
"""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel

from emotion_detection.fer_cnn import FERCustomCNN

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
EMOTIONS      = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
FER_SIZE      = 48
_WEIGHTS_PATH = Path(__file__).parent.parent / "emotion_detection" / "face" / "fer_cnn.pth"

# ── Router ─────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api", tags=["Explainability"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    image_base64: str                   # data-URI or raw base64 JPEG/PNG
    emotion: Optional[str] = None       # target class; if None → use predicted class


class ExplainResponse(BaseModel):
    heatmap_base64:    str              # JPEG overlay as base64 string
    predicted_emotion: str
    target_emotion:    str
    confidence:        float
    model_available:   bool


# ── Grad-CAM implementation ────────────────────────────────────────────────────

class GradCAM:
    """
    Hooks into a PyTorch model to compute Grad-CAM heatmaps.

    Parameters
    ----------
    model:
        The FERCustomCNN instance (must be in eval mode).
    target_layer:
        The convolutional layer to hook (we use the last conv block).
    """

    def __init__(self, model: FERCustomCNN, target_layer: torch.nn.Module) -> None:
        self._model        = model
        self._target_layer = target_layer
        self._activations: Optional[torch.Tensor] = None
        self._gradients:   Optional[torch.Tensor] = None

        # Register forward & backward hooks
        self._fwd_hook = target_layer.register_forward_hook(self._save_activation)
        self._bwd_hook = target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _, __, output: torch.Tensor) -> None:
        self._activations = output.detach()

    def _save_gradient(self, _, __, grad_output: tuple) -> None:
        self._gradients = grad_output[0].detach()

    def generate(self, input_tensor: torch.Tensor, target_class: int) -> np.ndarray:
        """
        Compute the Grad-CAM heatmap for *target_class*.

        Parameters
        ----------
        input_tensor:
            Shape (1, 1, 48, 48) float32 [0, 1].
        target_class:
            Integer index of the emotion class to explain.

        Returns
        -------
        np.ndarray
            Heatmap in [0, 1], shape (48, 48), float32.
        """
        self._model.eval()
        self._model.zero_grad()

        # Forward pass
        logits = self._model(input_tensor)           # (1, 7)
        score  = logits[0, target_class]

        # Backward pass (compute gradients w.r.t. target class score)
        score.backward()

        # Pool gradients over spatial dimensions
        grads  = self._gradients                      # (1, C, H, W)
        acts   = self._activations                    # (1, C, H, W)
        weights = grads.mean(dim=(2, 3), keepdim=True)  # (1, C, 1, 1)

        # Weighted combination of feature maps
        cam = (weights * acts).sum(dim=1, keepdim=True)  # (1, 1, H, W)
        cam = F.relu(cam)
        cam = cam.squeeze().cpu().numpy()

        # Normalise to [0, 1]
        cam_min, cam_max = cam.min(), cam.max()
        if cam_max > cam_min:
            cam = (cam - cam_min) / (cam_max - cam_min)
        else:
            cam = np.zeros_like(cam)

        # Resize to input size
        cam = cv2.resize(cam, (FER_SIZE, FER_SIZE))
        return cam.astype(np.float32)

    def remove_hooks(self) -> None:
        """Clean up hooks after use."""
        self._fwd_hook.remove()
        self._bwd_hook.remove()


# ── Helper: overlay heatmap on original image ──────────────────────────────────

def _overlay_heatmap(
    original_bgr: np.ndarray,
    heatmap: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Blend a Grad-CAM heatmap (jet colormap) onto the original image.

    Parameters
    ----------
    original_bgr:
        Original OpenCV frame (BGR, any size).
    heatmap:
        Float32 array [0, 1], shape (48, 48).
    alpha:
        Blend weight for the heatmap overlay (0 = original, 1 = heatmap only).

    Returns
    -------
    np.ndarray
        BGR image with heatmap overlay, same size as original_bgr.
    """
    h, w = original_bgr.shape[:2]

    # Scale heatmap to 0-255 and apply jet colormap
    heatmap_uint8 = (heatmap * 255).astype(np.uint8)
    jet = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)     # (48, 48, 3)
    jet = cv2.resize(jet, (w, h))                                  # upscale to original

    # Convert original to BGR if needed
    if len(original_bgr.shape) == 2:
        original_bgr = cv2.cvtColor(original_bgr, cv2.COLOR_GRAY2BGR)

    overlay = cv2.addWeighted(original_bgr, 1 - alpha, jet, alpha, 0)
    return overlay


def _frame_to_base64(frame_bgr: np.ndarray, quality: int = 85) -> str:
    """Encode a BGR numpy frame to base64 JPEG string."""
    _, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _decode_base64_image(b64: str) -> np.ndarray:
    """Decode a base64 image string to a BGR numpy array."""
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    img_bytes = base64.b64decode(b64)
    np_arr    = np.frombuffer(img_bytes, dtype=np.uint8)
    frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image bytes")
    return frame


# ── Model loader (lazy singleton) ─────────────────────────────────────────────

_cnn_model: Optional[FERCustomCNN] = None


def _get_model() -> Optional[FERCustomCNN]:
    """Load the CNN model once and cache it. Returns None if weights not found."""
    global _cnn_model
    if _cnn_model is not None:
        return _cnn_model

    if not _WEIGHTS_PATH.exists():
        logger.warning("CNN weights not found at %s — explainability unavailable.", _WEIGHTS_PATH)
        return None

    try:
        model = FERCustomCNN()
        state = torch.load(str(_WEIGHTS_PATH), map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval()
        _cnn_model = model
        logger.info("Grad-CAM model loaded from %s.", _WEIGHTS_PATH.name)
        return _cnn_model
    except Exception as exc:
        logger.error("Failed to load CNN weights: %s", exc)
        return None


# ── FastAPI endpoint ───────────────────────────────────────────────────────────

@router.post("/explain_emotion", response_model=ExplainResponse,
             summary="Grad-CAM explainability for the FER-2013 CNN")
async def explain_emotion(body: ExplainRequest) -> ExplainResponse:
    """
    Generate a Grad-CAM heatmap showing **which facial regions** the custom
    FER-2013 CNN focused on when predicting the emotion.

    - If `emotion` is provided, the heatmap highlights regions for that class.
    - If `emotion` is omitted, the predicted class is used automatically.

    The response includes `heatmap_base64` — a JPEG overlay image — which the
    React frontend can display directly using:
    ```html
    <img src="data:image/jpeg;base64,{heatmap_base64}" />
    ```
    """
    # ── Decode input image ────────────────────────────────────────────────────
    try:
        original_bgr = _decode_base64_image(body.image_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    # ── Prepare input tensor ──────────────────────────────────────────────────
    gray    = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (FER_SIZE, FER_SIZE))
    tensor  = torch.from_numpy(resized).float() / 255.0
    tensor  = tensor.unsqueeze(0).unsqueeze(0).requires_grad_(True)   # (1,1,48,48)

    # ── Load model ────────────────────────────────────────────────────────────
    model = _get_model()

    if model is None:
        # No weights available — return a mock/unavailable response
        logger.warning("Grad-CAM requested but CNN weights not loaded.")
        return ExplainResponse(
            heatmap_base64    = _frame_to_base64(original_bgr),
            predicted_emotion = "unavailable",
            target_emotion    = body.emotion or "unavailable",
            confidence        = 0.0,
            model_available   = False,
        )

    # ── Run prediction ────────────────────────────────────────────────────────
    with torch.no_grad():
        probs        = model.predict_proba(tensor.detach())[0]
    probs_list       = probs.cpu().numpy().tolist()
    predicted_idx    = int(np.argmax(probs_list))
    predicted_emotion = EMOTIONS[predicted_idx]
    confidence        = round(float(probs_list[predicted_idx]), 4)

    # ── Resolve target class ──────────────────────────────────────────────────
    target_emotion = (body.emotion or predicted_emotion).lower()
    if target_emotion not in EMOTIONS:
        target_emotion = predicted_emotion
    target_idx = EMOTIONS.index(target_emotion)

    # ── Grad-CAM ──────────────────────────────────────────────────────────────
    # Target the last convolutional block (features.2 = FERBlock with 128 filters)
    target_layer = model.features[2].layers[1]    # second Conv2d in block 3

    grad_cam = GradCAM(model, target_layer)
    try:
        # Re-run forward with gradients enabled
        tensor_grad = tensor.clone().detach().requires_grad_(True)
        heatmap = grad_cam.generate(tensor_grad, target_class=target_idx)
    finally:
        grad_cam.remove_hooks()

    # ── Overlay and encode ─────────────────────────────────────────────────────
    overlay = _overlay_heatmap(original_bgr, heatmap, alpha=0.45)
    heatmap_b64 = _frame_to_base64(overlay)

    logger.info(
        "Grad-CAM generated: predicted=%s target=%s confidence=%.3f",
        predicted_emotion, target_emotion, confidence,
    )

    return ExplainResponse(
        heatmap_base64    = heatmap_b64,
        predicted_emotion = predicted_emotion,
        target_emotion    = target_emotion,
        confidence        = confidence,
        model_available   = True,
    )
