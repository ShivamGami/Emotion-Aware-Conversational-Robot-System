import requests, time

BASE = "http://localhost:8000"

print("=" * 50)
print("EMOTION ROBOT — API VERIFICATION TESTS")
print("=" * 50)

# 1. Health
r = requests.get(f"{BASE}/api/health")
print("1. Health:", r.json())

# 2. Face detect — fast path (no face → returns quickly without running DeepFace)
t0 = time.time()
r = requests.post(f"{BASE}/api/detect/face", json={"image_base64": "data:image/jpeg;base64,/9j/4AAQ"})
ms = (time.time()-t0)*1000
d = r.json()
print(f"2. Face detect: emotion={d['dominant_emotion']}, no_face={d['no_face_detected']}, total={ms:.0f}ms, api={d['processing_time_ms']}ms")

# 3. Fuse — primary route
r = requests.post(f"{BASE}/api/fuse", json={
    "face_emotion": "happy", "face_confidence": 0.85,
    "voice_emotion": "neutral", "voice_confidence": 0.6
})
print("3. Fuse (primary):", r.json()["fused_emotion"], "| status:", r.status_code)

# 4. Fuse alias — was BROKEN before fix
r = requests.post(f"{BASE}/api/fuse_emotions", json={
    "face_emotion": "angry", "face_confidence": 0.9,
    "voice_emotion": "angry", "voice_confidence": 0.75
})
print("4. Fuse (alias /api/fuse_emotions):", r.json()["fused_emotion"], "| status:", r.status_code)

# 5. Face detect alias
r = requests.post(f"{BASE}/api/detect_face_emotion", json={"image_base64": "data:image/jpeg;base64,/9j/4AAQ"})
d2 = r.json()
print("5. Face alias  (/api/detect_face_emotion): no_face_detected =", d2["no_face_detected"], "| status:", r.status_code)

# 6. Voice detect alias (bad audio = 500, but route exists — 422 would mean schema error)
r = requests.post(f"{BASE}/api/detect_voice_emotion", json={"audio_base64": "data:audio/webm;base64,AAAA"})
print("6. Voice alias (/api/detect_voice_emotion): status =", r.status_code, "(500=route OK+bad audio, 404=broken)")

# 7. Voice primary route
r = requests.post(f"{BASE}/api/detect/voice", json={"audio_base64": "data:audio/webm;base64,AAAA"})
print("7. Voice (primary /api/detect/voice): status =", r.status_code)

print()
print("=" * 50)
print("TESTS COMPLETE")
print("=" * 50)
