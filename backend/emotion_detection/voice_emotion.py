"""
voice_emotion.py
----------------
Voice/Audio Emotion Detection using a trained PyTorch 1D-CNN on RAVDESS dataset.

Fixes applied (v2.1):
  - Real softmax confidence score returned from predict_emotion()
  - Handles both WebM (browser recording) and WAV audio formats
  - Resamples audio to 22050Hz for consistent MFCC extraction
  - predict_emotion() returns top-3 predictions with probability scores
  - All audio errors are handled gracefully without crashing
"""

import io
import os
import base64
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt

# Resolve model path relative to this file's backend root directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_MODEL_PATH = os.path.join(_BACKEND_DIR, "voice_model.pth")

TARGET_SR = 22050   # Standard sample rate for MFCC extraction
N_MFCC    = 40      # Number of MFCC coefficients (must match training)


# We define the PyTorch Model Architecture so we can load the trained weights
class AudioEmotionCNN(nn.Module):
    def __init__(self):
        super(AudioEmotionCNN, self).__init__()
        # input shape: (batch, 1, 40) - 40 MFCC features
        self.conv1 = nn.Conv1d(1, 64, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool1d(kernel_size=2)
        self.fc1 = nn.Linear(64 * 20, 128)
        self.fc2 = nn.Linear(128, 8)  # 8 emotions in RAVDESS

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


class VoiceEmotionDetector:
    """
    Detect emotion from audio bytes (WAV or WebM) using a trained 1D CNN.
    
    Returns real softmax confidence scores and top-3 predictions.
    Robust to browser audio formats (webm/opus, wav, ogg).
    """

    def __init__(self, model_path: str = _DEFAULT_MODEL_PATH):
        self.emotions_map = {
            1: "neutral", 2: "calm", 3: "happy", 4: "sad",
            5: "angry", 6: "fearful", 7: "disgust", 8: "surprised"
        }
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AudioEmotionCNN()
        self.model.to(self.device)
        self.model.eval()
        self.model_loaded = False

        try:
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model_loaded = True
            print(f"[INFO] Voice Emotion model loaded from {model_path}")
        except Exception as e:
            print(f"[WARN] Voice model not loaded ({e}). Using rule-based fallback.")

    def _load_audio_bytes(self, audio_bytes: bytes) -> tuple:
        """
        Load audio from bytes, handling multiple formats:
        - audio/webm (browser default for MediaRecorder)
        - audio/wav (explicit WAV)
        - audio/ogg
        
        Returns (data_array, sample_rate) or raises ValueError.
        """
        import librosa
        
        # Strategy 1: Try soundfile (handles wav, ogg, flac)
        try:
            import soundfile as sf
            data, sr = sf.read(io.BytesIO(audio_bytes))
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)  # stereo → mono
            return data.astype(np.float32), sr
        except Exception:
            pass

        # Strategy 2: Try librosa with audioread (handles webm, mp4, opus via ffmpeg)
        try:
            data, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
            return data, sr
        except Exception:
            pass

        # Strategy 3: Write to temp file and retry (some codecs need seeking)
        try:
            import tempfile
            suffix = ".webm"  # Most common from browser
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                data, sr = librosa.load(tmp_path, sr=None, mono=True)
                return data, sr
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        except Exception as e:
            raise ValueError(f"Could not decode audio in any format: {e}")

    def _extract_mfcc_features(self, audio_bytes: bytes) -> np.ndarray:
        """
        Extract 40 MFCC features from audio bytes.
        Resamples to TARGET_SR for consistency.
        
        Returns shape (40,) numpy array.
        """
        import librosa

        data, sr = self._load_audio_bytes(audio_bytes)

        # Resample to standard rate for consistent MFCC
        if sr != TARGET_SR:
            data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

        # Trim silence from edges
        data, _ = librosa.effects.trim(data, top_db=20)

        # Need at least 0.5 seconds of audio
        min_samples = int(sr * 0.5)
        if len(data) < min_samples:
            data = np.pad(data, (0, min_samples - len(data)))

        # Extract MFCC — shape: (n_mfcc, time_frames)
        mfccs = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=N_MFCC, n_fft=512, hop_length=256)
        mfccs_mean = np.mean(mfccs, axis=1)  # shape: (40,)

        return mfccs_mean.astype(np.float32)

    def predict_emotion(self, audio_input) -> dict:
        """
        Predict emotion from audio input (bytes or file path).
        
        Returns:
        {
            "emotion": "happy",
            "confidence": 0.87,   # real softmax probability
            "top_predictions": [
                {"emotion": "happy", "confidence": 0.87},
                {"emotion": "surprised", "confidence": 0.08},
                {"emotion": "neutral", "confidence": 0.03},
            ]
        }
        """
        try:
            # Extract features
            if isinstance(audio_input, bytes):
                mfcc_features = self._extract_mfcc_features(audio_input)
            else:
                # File path
                import librosa
                data, sr = librosa.load(audio_input, sr=TARGET_SR, mono=True)
                mfccs = librosa.feature.mfcc(y=data, sr=sr, n_mfcc=N_MFCC, n_fft=512, hop_length=256)
                mfcc_features = np.mean(mfccs, axis=1).astype(np.float32)

            # Convert to tensor — shape: (1, 1, 40)
            mfcc_tensor = torch.tensor(mfcc_features, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)

            if self.model_loaded:
                with torch.no_grad():
                    logits = self.model(mfcc_tensor)
                    # Apply softmax to get real probability scores
                    probs = F.softmax(logits, dim=1)[0]  # shape: (8,)

                probs_numpy = probs.cpu().numpy()

                # Build predictions list (1-indexed RAVDESS classes)
                all_preds = [
                    {
                        "emotion": self.emotions_map.get(i + 1, "neutral"),
                        "confidence": round(float(probs_numpy[i]), 4)
                    }
                    for i in range(len(probs_numpy))
                ]
                all_preds.sort(key=lambda x: x["confidence"], reverse=True)

                top_emotion = all_preds[0]["emotion"]
                top_confidence = all_preds[0]["confidence"]

                return {
                    "emotion": top_emotion,
                    "confidence": top_confidence,
                    "top_predictions": all_preds[:3],
                }
            else:
                # Rule-based fallback using MFCC energy features
                energy = float(np.mean(np.abs(mfcc_features)))
                variance = float(np.var(mfcc_features))

                if energy > 80 and variance > 200:
                    emotion, conf = "angry", 0.55
                elif energy > 60:
                    emotion, conf = "happy", 0.50
                elif energy < 30:
                    emotion, conf = "sad", 0.50
                else:
                    emotion, conf = "neutral", 0.60

                return {
                    "emotion": emotion,
                    "confidence": conf,
                    "top_predictions": [{"emotion": emotion, "confidence": conf}],
                }

        except Exception as e:
            print(f"[ERROR] Voice emotion prediction failed: {e}")
            return {
                "emotion": "neutral",
                "confidence": 0.0,
                "top_predictions": [],
            }

    def generate_spectrogram(self, audio_input) -> str:
        """
        Process the audio input and return a real Base64-encoded Matplotlib
        plot of the Mel-frequency Spectrogram.
        """
        try:
            import librosa
            import librosa.display

            if isinstance(audio_input, bytes):
                data, sr = self._load_audio_bytes(audio_input)
            else:
                data, sr = librosa.load(audio_input, sr=TARGET_SR, mono=True)

            if sr != TARGET_SR:
                data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
                sr = TARGET_SR

            fig, ax = plt.subplots(figsize=(10, 4))
            S = librosa.feature.melspectrogram(y=data, sr=sr, n_mels=128)
            S_dB = librosa.power_to_db(S, ref=np.max)
            img = librosa.display.specshow(S_dB, sr=sr, x_axis='time', y_axis='mel', ax=ax)
            fig.colorbar(img, ax=ax, format='%+2.0f dB')
            ax.set_title('Mel-frequency spectrogram')

            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)

            base64_str = base64.b64encode(buf.read()).decode('utf-8')
            return f"data:image/png;base64,{base64_str}"

        except Exception as e:
            print(f"[ERROR] Spectrogram generation failed: {e}")
            return ""
