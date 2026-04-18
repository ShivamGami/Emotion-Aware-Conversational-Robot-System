import requests
import base64
import time

try:
    print("Testing Face Emotion endpoint...")
    b64 = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07").decode('utf-8')
    start = time.time()
    res = requests.post("http://localhost:8000/api/detect/face", json={"image_base64": b64})
    end = time.time()
    print("Face Resp:", res.status_code, res.text)
    print("Face Time:", end - start)
except Exception as e:
    print("Face error:", e)

try:
    print("Testing Memory Store endpoint...")
    # NOTE: requires auth... skip for now, just test health
    res = requests.get("http://localhost:8000/api/health")
    print("Health:", res.status_code, res.text)
except Exception as e:
    print("Health error:", e)
