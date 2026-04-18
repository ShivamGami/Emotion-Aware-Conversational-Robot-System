import logging
import os
import random
from typing import Optional, List, Dict
from openai import OpenAI
from dotenv import load_dotenv

from .prompt_templates import get_emobot_system_prompt

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import re

def _sanitize_response(text: str) -> str:
    """Strip markdown formatting that would sound bad in TTS."""
    text = re.sub(r'[*_#`~]', '', text)  # Remove markdown chars
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [link](url) -> link
    text = re.sub(r'\n{2,}', ' ', text)  # Collapse double newlines
    text = text.strip()
    return text

class ChatEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.xai_key = os.getenv("XAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
        
        self.gemini_client = None
        self.openai_client = None

        if self.gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_key)
                logger.info(f"✅ ChatEngine ready — using Google Gemini {self.model} (Free Tier)")
            except ImportError:
                logger.error("⚠️ google-genai not installed. Falling back.")

        if not self.gemini_client and self.xai_key:
            self.openai_client = OpenAI(
                api_key=self.xai_key,
                base_url="https://api.x.ai/v1",
            )
            logger.info("✅ ChatEngine ready — using xAI (Grok)")

        if not self.gemini_client and not self.openai_client:
            logger.warning("⚠️ No valid LLM API keys found. Fallback mode enabled.")

    def get_response(
        self,
        user_message: str,
        emotion: str = "neutral",
        history: List[Dict] = [],
        user_name: str = "Friend",
    ) -> Dict:
        """
        Get empathetic response from Gemini or xAI.
        """
        # Build conversation context
        history_summary = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
        system_prompt = get_emobot_system_prompt(emotion, history_summary)

        # ── OPTION 1: GOOGLE GEMINI (Free Tier) ──
        if self.gemini_client:
            try:
                from google.genai import types
                
                # Format context: System Instructions + History
                full_content = []
                for m in history[-5:]:
                    role = "user" if m["role"] == "user" else "model"
                    full_content.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
                
                # Add the current user message
                full_content.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

                # Using generate_content (single-shot with system instruction) for maximum stability
                response = self.gemini_client.models.generate_content(
                    model=self.model,
                    contents=full_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                        max_output_tokens=256,  # Faster responses
                    )
                )
                
                content = _sanitize_response(response.text.strip())
                
                return {
                    "response": content,
                    "emotion_used": emotion,
                    "model": self.model,
                    "speak_with_emotion": emotion,
                    "voice_settings": self._get_voice_settings(emotion)
                }
            except Exception as e:
                logger.error(f"Gemini API Error: {e}")

        # ── OPTION 2: xAI (Grok) ──
        if self.openai_client:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for turn in history[-5:]:
                    messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
                messages.append({"role": "user", "content": user_message})

                response = self.openai_client.chat.completions.create(
                    model="grok-beta", # Fallback model name for xAI
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150
                )
                content = _sanitize_response(response.choices[0].message.content.strip())
                
                return {
                    "response": content,
                    "emotion_used": emotion,
                    "model": "grok-beta",
                    "speak_with_emotion": emotion,
                    "voice_settings": self._get_voice_settings(emotion)
                }
            except Exception as e:
                logger.error(f"xAI API Error: {e}")

        # ── OPTION 3: STATIC FALLBACK ──
        return self._fallback_response(emotion)

    def _get_voice_settings(self, emotion: str) -> Dict:
        """Dynamic voice settings based on emotion."""
        emotion = emotion.lower()
        if emotion == "happy":
            return {"rate": 1.1, "pitch": 1.2}
        if emotion in ["sad", "fear", "fearful"]:
            return {"rate": 0.8, "pitch": 0.9}
        if emotion == "angry":
            return {"rate": 1.2, "pitch": 0.8}
        return {"rate": 1.0, "pitch": 1.0}

    def _fallback_response(self, emotion: str) -> Dict:
        """Emergency fallback responses."""
        fallbacks = {
            "happy": "That's wonderful to hear! Your happiness is contagious.",
            "sad": "I'm here for you. It's okay to feel this way.",
            "angry": "I understand why that would be frustrating. I'm listening.",
            "neutral": "I'm here and ready to chat. What's on your mind?",
        }
        resp = fallbacks.get(emotion.lower(), fallbacks["neutral"])
        return {
            "response": resp,
            "emotion_used": emotion,
            "model": "fallback",
            "speak_with_emotion": emotion,
            "voice_settings": {"rate": 1.0, "pitch": 1.0}
        }

    def _get_api_status(self) -> bool:
        """Check if any LLM API is accessible."""
        return self.gemini_client is not None or self.openai_client is not None