import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-pro"
]

for model in models_to_try:
    print(f"Trying model: {model}...")
    try:
        response = client.models.generate_content(
            model=model,
            contents="hi"
        )
        print(f"SUCCESS with {model}: {response.text}")
        break
    except Exception as e:
        print(f"FAILED with {model}: {e}")
