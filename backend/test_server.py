import requests

# Try to hit the welcome endpoint to see if server is alive
try:
    resp = requests.get("http://localhost:8000/api/chat/welcome")
    print(f"Server Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"FAILED to reach server: {e}")
