import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("XAI_API_KEY")
model = os.getenv("LLM_MODEL", "grok-beta")

print(f"API Key: {api_key[:10]}...")
print(f"Model: {model}")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1",
)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        timeout=10
    )
    print("SUCCESS")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"FAILED: {e}")
