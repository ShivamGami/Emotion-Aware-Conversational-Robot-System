import requests
import os
from dotenv import load_dotenv

load_dotenv()

# We need a way to generate a token or bypass auth for testing.
# Since I am an agent, I'll use the auth handler logic.
from auth.jwt_handler import create_access_token

token = create_access_token({"sub": "1"}) # User ID 1

url = "http://localhost:8000/api/chat"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
data = {
    "text": "Hello EmoBot! How are you feeling today?",
    "emotion": "happy"
}

print(f"--- Sending request to {url} ---")
try:
    resp = requests.post(url, headers=headers, json=data, timeout=15)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print(f"Response: {resp.json()}")
    else:
        print(f"Error Body: {resp.text}")
except Exception as e:
    print(f"Request FAILED: {e}")
