"""
Chat Engine — connects emotion data to LLM responses.
Member 1 — Task 1.4
"""

import logging
import requests
import json
from typing import Optional
from .prompt_templates import get_system_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Rule-based fallback responses (if Ollama not available) ──────────────────
FALLBACK_RESPONSES = {
    "happy": [
        "You look so happy right now! That energy is contagious! 😊",
        "Your smile just lit up the room! What's making you so happy?",
        "Love seeing you this cheerful! Keep that amazing energy!",
    ],
    "sad": [
        "I can see you're feeling down. I'm here for you. 💙",
        "It's okay to feel sad sometimes. Want to talk about it?",
        "I notice you seem a little sad. Things will get better.",
    ],
    "angry": [
        "I can see something's frustrating you. Take a deep breath. 💨",
        "It's okay to feel frustrated. Want to talk about what's bothering you?",
        "I hear you. Let's work through this together calmly.",
    ],
    "fear": [
        "You seem a little anxious. You're safe here. 🤗",
        "It's okay to feel nervous. Take it one step at a time.",
        "I'm right here with you. There's nothing to worry about.",
    ],
    "surprise": [
        "Oh! You look surprised! What happened? 😮",
        "Something caught you off guard? Tell me about it!",
        "That surprised expression is priceless! What's going on?",
    ],
    "neutral": [
        "Hey there! How are you doing today?",
        "Good to see you! What's on your mind?",
        "Hello! Ready to chat?",
    ],
    "disgust": [
        "Something seems off for you right now. Want to talk about it?",
        "I can tell something's bothering you. I'm here to listen.",
        "Let's find something to cheer you up!",
    ],
}

import random

class ChatEngine:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url    = ollama_url
        self.model         = "phi3:mini"
        self.ollama_available = self._check_ollama()
        
        if self.ollama_available:
            logger.info("✅ ChatEngine ready — using Ollama Phi-3 mini")
        else:
            logger.warning("⚠️  Ollama not found — using rule-based fallback")

    # ── Public API ────────────────────────────────────────────────────────

    def get_response(
        self,
        user_message: str,
        emotion: str = "neutral",
        confidence: float = 0.0,
        user_name: str = "Friend",
        conversation_history: list = [],
        memories: list = [],
    ) -> dict:
        """
        Main method — returns robot response based on message + emotion.
        Called from /api/chat endpoint.
        """
        try:
            if self.ollama_available:
                response = self._ollama_response(
                    user_message, emotion, confidence,
                    user_name, conversation_history, memories
                )
            else:
                response = self._fallback_response(user_message, emotion)

            return {
                "response": response,
                "emotion_used": emotion,
                "model": self.model if self.ollama_available else "rule-based",
                "user_name": user_name,
            }

        except Exception as e:
            logger.error("ChatEngine error: %s", e)
            return {
                "response": self._fallback_response(user_message, emotion),
                "emotion_used": emotion,
                "model": "fallback",
                "error": str(e),
            }

    # ── Private Methods ───────────────────────────────────────────────────

    def _ollama_response(
        self,
        user_message: str,
        emotion: str,
        confidence: float,
        user_name: str,
        history: list,
        memories: list,
    ) -> str:
        """Call Ollama API for LLM response."""

        system_prompt = get_system_prompt(emotion, user_name, confidence)

        # Inject memories into system prompt if available
        if memories:
            memory_text = "\n".join([f"- {m}" for m in memories[:5]])
            system_prompt += f"\n\nWhat you remember about {user_name}:\n{memory_text}"

        # Build messages list
        messages = [{"role": "system", "content": system_prompt}]

        # Add last 6 conversation turns for context
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Call Ollama
        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,   # keep responses short
                }
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()

    def _fallback_response(self, user_message: str, emotion: str) -> str:
        """Rule-based response when Ollama unavailable."""
        emotion = emotion.lower()
        responses = FALLBACK_RESPONSES.get(emotion, FALLBACK_RESPONSES["neutral"])
        return random.choice(responses)

    def _check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return r.status_code == 200
        except:
            return False