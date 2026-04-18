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

class ChatEngine:
    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "grok-beta")
        
        if not self.api_key:
            logger.warning("⚠️  XAI_API_KEY not found in environment. Fallback mode enabled.")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.x.ai/v1",
            )
            logger.info(f"✅ ChatEngine ready — using xAI {self.model}")

    def get_response(
        self,
        user_message: str,
        emotion: str = "neutral",
        history: List[Dict] = [],
        user_name: str = "Friend",
    ) -> Dict:
        """
        Get empathetic response from xAI Grok.
        """
        if not self.client:
            return self._fallback_response(emotion)

        try:
            # Build conversation history string for the system prompt if needed,
            # but usually we pass history as messages.
            history_summary = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
            system_prompt = get_emobot_system_prompt(emotion, history_summary)

            messages = [{"role": "system", "content": system_prompt}]
            # Add recent history
            for turn in history[-5:]:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )

            content = response.choices[0].message.content.strip()
            
            return {
                "response": content,
                "emotion_used": emotion,
                "model": self.model,
                "speak_with_emotion": emotion, # Echo back for voice sync
                "voice_settings": self._get_voice_settings(emotion)
            }

        except Exception as e:
            logger.error(f"xAI API Error: {e}")
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
        """Check if xAI API is accessible."""
        return self.client is not None