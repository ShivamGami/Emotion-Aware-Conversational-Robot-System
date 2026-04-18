import os
import sys
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from llm.chat_engine import ChatEngine

def test():
    load_dotenv()
    ce = ChatEngine()
    print("--- Testing 'hello' with 'happy' emotion ---")
    res = ce.get_response("hello", "happy")
    print(f"RESPONSE: {res['response']}")
    print("-" * 30)

if __name__ == "__main__":
    test()
