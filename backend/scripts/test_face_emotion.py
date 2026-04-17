"""
Quick test for FaceEmotionDetector.
Run from backend/ directory:
    python scripts/test_face_emotion.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
from app.emotion_detection.face import FaceEmotionDetector


def test_with_webcam(num_frames: int = 5):
    """Capture frames from webcam and print detection results."""
    detector = FaceEmotionDetector()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌  Webcam not found. Trying static image test instead.")
        test_with_static_image(detector)
        return

    print("📷  Webcam opened. Press Q to quit, or wait for auto-capture.\n")

    captured = 0
    while captured < num_frames:
        ret, frame = cap.read()
        if not ret:
            break

        result = detector.detect_from_frame(frame)
        annotated = detector.annotate_frame(frame, result)

        # Console output
        print(f"Frame {captured + 1}/{num_frames}")
        print(f"  Dominant : {result.dominant_emotion.upper()}")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Landmarks : {result.landmarks_detected}")
        print(f"  Time      : {result.processing_time_ms:.1f} ms")
        print(f"  All scores: { {k: f'{v:.2f}' for k, v in result.all_emotions.items()} }")
        print()

        cv2.imshow("Emotion Detection Test — press Q to quit", annotated)
        captured += 1

        key = cv2.waitKey(800)   # 800 ms between captures
        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.release()
    print("✅  Test complete.")


def test_with_static_image(detector: FaceEmotionDetector):
    """Fallback: test with a static image file."""
    test_path = "test_face.jpg"
    if not os.path.exists(test_path):
        print(f"❌  No webcam and no '{test_path}' found.")
        print("    Place a face photo named test_face.jpg in the backend/ directory.")
        return

    result = detector.detect_from_image_path(test_path)
    print(f"✅  Static image result:")
    print(f"    Emotion   : {result.dominant_emotion}")
    print(f"    Confidence: {result.confidence:.1%}")
    print(f"    All       : {result.all_emotions}")


if __name__ == "__main__":
    test_with_webcam()