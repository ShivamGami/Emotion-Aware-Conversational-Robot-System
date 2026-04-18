"""
fer_cnn.py
----------
Custom CNN architecture for FER-2013 (48x48 grayscale, 7 emotion classes).

This file defines the exact same architecture that was used during training.
The weights are loaded from a .pth file via FaceEmotionDetector.

Architecture summary:
  Input  : (B, 1, 48, 48)  — grayscale normalised to [0, 1]
  Block 1: Conv(32) → BN → ReLU → Conv(32) → BN → ReLU → MaxPool → Dropout(0.25)
  Block 2: Conv(64) → BN → ReLU → Conv(64) → BN → ReLU → MaxPool → Dropout(0.25)
  Block 3: Conv(128)→ BN → ReLU → Conv(128)→ BN → ReLU → MaxPool → Dropout(0.25)
  FC     : Flatten → Dense(1024) → BN → ReLU → Dropout(0.5) → Dense(7)
  Output : 7-class softmax (applied at inference time only)

Emotion label order (must match training):
  0=angry  1=disgust  2=fear  3=happy  4=sad  5=surprise  6=neutral

NOTE: Labels use "fear" and "surprise" (not "fearful"/"surprised").
      The fusion module (emotion_fusion.py) must use the same keys.
"""

import torch
import torch.nn as nn


class FERBlock(nn.Module):
    """Two Conv-BN-ReLU layers followed by MaxPool + Dropout."""

    def __init__(self, in_ch: int, out_ch: int, dropout: float = 0.25) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),          # halves spatial dimensions
            nn.Dropout2d(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class FERCustomCNN(nn.Module):
    """
    Custom CNN for the FER-2013 dataset.

    Parameters
    ----------
    num_classes:
        Number of emotion classes (default: 7).
    dropout_fc:
        Dropout rate for the fully-connected layer (default: 0.5).

    Usage
    -----
    model = FERCustomCNN()
    model.load_state_dict(torch.load("fer_cnn.pth", map_location="cpu"))
    model.eval()

    probs = model.predict_proba(tensor)   # tensor shape: (B, 1, 48, 48)
    """

    # Canonical label order used during FER-2013 training.
    # Keys intentionally kept as "fear" / "surprise" (not "fearful"/"surprised")
    # to stay consistent with the FER library and the fusion module.
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

    def __init__(self, num_classes: int = 7, dropout_fc: float = 0.5) -> None:
        super().__init__()

        self.features = nn.Sequential(
            FERBlock(1, 32),     # (B,  1, 48, 48) → (B, 32, 24, 24)
            FERBlock(32, 64),    # (B, 32, 24, 24) → (B, 64, 12, 12)
            FERBlock(64, 128),   # (B, 64, 12, 12) → (B,128,  6,  6)
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 6 * 6, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_fc),
            nn.Linear(1024, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))

    @torch.no_grad()
    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return softmax probabilities. Input: (B, 1, 48, 48) float32 [0,1]."""
        self.eval()
        logits = self(x)
        return torch.softmax(logits, dim=-1)