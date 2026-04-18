import os
import logging
from dotenv import load_dotenv
from llm.chat_engine import ChatEngine

# Configure logging to see ChatEngine status
logging.basicConfig(level=logging.INFO)

load_dotenv()

def test_gemini():
    print("--- Initializing ChatEngine ---")
    ce = ChatEngine()
    
    if ce.gemini_client is None:
        print("FAILED: Gemini Client not initialized. Check GEMINI_API_KEY in .env")
        return

    print("--- Sending Test Message ---")
    res = ce.get_response(
        user_message="Hello! I am feeling very happy today. How are you?",
        emotion="happy",
        history=[{"role": "user", "content": "Hi bot"}]
    )
    
    print(f"Model Used: {res.get('model')}")
    print(f"Emotion Used: {res.get('emotion_used')}")
    print(f"Response: {res.get('response')}")
    
    if "happy" in res.get('response').lower() or "glad" in res.get('response').lower() or "joy" in res.get('response').lower():
        print("SUCCESS: Response sounds emotionally aware.")
    else:
        print("CHECK: Verify response tone manually.")

if __name__ == "__main__":
    test_gemini()
