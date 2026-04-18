import cv2
import numpy as np
from deepface import DeepFace
import time

# Create a blank image (simulating a face or just a frame)
frame = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(frame, "Test Face", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

print("Starting DeepFace analysis...")
start = time.time()
try:
    # Use opencv detector backend as it's more robust for headless/simulated environments
    analysis = DeepFace.analyze(img_path=frame, actions=['emotion'], detector_backend='opencv', enforce_detection=False)
    print(f"Analysis successful in {time.time() - start:.2f}s")
    print(analysis)
except Exception as e:
    print(f"Analysis failed: {e}")
