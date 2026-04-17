"""
chat_engine.py  —  Task 1.7
-----------------------------
Polished ChatEngine that integrates:
  1. Ollama Phi-3 mini inference (streaming-ready).
  2. Dynamic emotion-aware system prompts (via prompt_templates.py).
  3. Automatic memory extraction after each turn (regex + keyword heuristics).
  4. Importance scoring before saving to ChromaDB.
  5. Short-term ConversationHistory → long-term MemoryStore pipeline.

Backend: FastAPI  |  Member 1 — AI & Memory Engineer
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import AsyncGenerator, Optional

import ollama

from app.llm.prompt_templates import build_system_prompt, build_welcome_message
from app.memory.conversation import ConversationManager
from app.memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
OLLAMA_MODEL     = "phi3"          # alias for phi3:mini in Ollama
MAX_CONTEXT_MEMORIES = 5           # how many past memories to inject into the prompt
MAX_HISTORY_TURNS    = 6           # how many conversation turns to include

# ── Regex patterns for auto-extraction ────────────────────────────────────────
# These patterns pull factual statements about the user from their messages.
_EXTRACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "I love/like/enjoy X"  → "User loves X"
    (re.compile(r"\bi (?:love|like|enjoy|adore|really like)\s+(.+?)(?:[.!?]|$)", re.I),
     "User loves {0}"),
    # "I hate/dislike X"
    (re.compile(r"\bi (?:hate|dislike|can't stand|despise)\s+(.+?)(?:[.!?]|$)", re.I),
     "User dislikes {0}"),
    # "I work as / I am a X"
    (re.compile(r"\bi (?:work as|am a|am an)\s+(.+?)(?:[.!?]|$)", re.I),
     "User works as {0}"),
    # "I have a / I own a X"
    (re.compile(r"\bi (?:have|own)\s+(?:a |an )?(.+?)(?:[.!?]|$)", re.I),
     "User has {0}"),
    # "My X is / My X are"
    (re.compile(r"\bmy\s+(\w+)\s+is\s+(.+?)(?:[.!?]|$)", re.I),
     "User's {0} is {1}"),
    # "I live in X"
    (re.compile(r"\bi live in\s+(.+?)(?:[.!?]|$)", re.I),
     "User lives in {0}"),
    # "I feel/am feeling X" — emotional state memory
    (re.compile(r"\bi(?:'m| am) feeling\s+(.+?)(?:[.!?]|$)", re.I),
     "User felt {0}"),
]

# Importance scoring heuristics
_HIGH_IMPORTANCE_KEYWORDS   = {"died", "death", "love", "hate", "family", "depressed",
                                "promoted", "married", "divorced", "fired", "cancer", "hospital"}
_MEDIUM_IMPORTANCE_KEYWORDS = {"work", "job", "hobby", "likes", "dislikes", "lives", "has", "enjoy"}


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class ChatResponse:
    reply:       str
    emotion:     str
    user_name:   str
    memories_used: int
    extracted_facts: list[str]      # what was auto-extracted this turn


# ── Auto-extraction helpers ────────────────────────────────────────────────────

def extract_facts(text: str) -> list[str]:
    """
    Apply regex patterns to extract factual statements about the user
    from their raw message text.

    Returns a list of short, normalised fact strings ready to store in ChromaDB.
    """
    facts: list[str] = []
    for pattern, template in _EXTRACTION_PATTERNS:
        for match in pattern.finditer(text):
            groups = [g.strip().rstrip(".,!?") for g in match.groups() if g]
            try:
                fact = template.format(*groups)
                facts.append(fact)
            except IndexError:
                continue
    return facts


def score_importance(fact: str, emotion: str) -> str:
    """
    Assign an importance level (high / medium / low) to a memory fact.

    Rules (in priority order):
      - High emotion (sad, angry, fear)           → high
      - Fact contains high-importance keywords    → high
      - Fact contains medium-importance keywords  → medium
      - Default                                   → low
    """
    fact_lower = fact.lower()
    emo_lower  = emotion.lower()

    if emo_lower in {"sad", "angry", "fear"}:
        return "high"
    if any(kw in fact_lower for kw in _HIGH_IMPORTANCE_KEYWORDS):
        return "high"
    if any(kw in fact_lower for kw in _MEDIUM_IMPORTANCE_KEYWORDS):
        return "medium"
    return "low"


# ── ChatEngine ─────────────────────────────────────────────────────────────────

class ChatEngine:
    """
    Orchestrates a full conversation turn:

    1. Retrieve relevant memories from ChromaDB.
    2. Build an emotion-aware system prompt.
    3. Call Ollama Phi-3 mini for the LLM reply.
    4. Add the turn to short-term ConversationHistory.
    5. Auto-extract facts from the user message & save to MemoryStore.

    Usage
    -----
    engine = ChatEngine(memory_store, conv_manager)
    response = await engine.chat(
        user_id="alice_42",
        user_name="Alice",
        user_message="I love morning coffee!",
        emotion="happy",
    )
    print(response.reply)
    """

    def __init__(
        self,
        memory_store:   MemoryStore,
        conv_manager:   ConversationManager,
        ollama_model:   str = OLLAMA_MODEL,
        max_memories:   int = MAX_CONTEXT_MEMORIES,
        max_history:    int = MAX_HISTORY_TURNS,
    ) -> None:
        self._store        = memory_store
        self._conv_manager = conv_manager
        self._model        = ollama_model
        self._max_mem      = max_memories
        self._max_history  = max_history
        logger.info("ChatEngine ready [model=%s]", ollama_model)

    # ── Primary public method ─────────────────────────────────────────────────

    async def chat(
        self,
        user_id:      str,
        user_name:    str,
        user_message: str,
        emotion:      str = "neutral",
    ) -> ChatResponse:
        """
        Process one conversational turn and return the robot's reply.

        This is the method your FastAPI route should call.
        """
        # 1. Short-term history
        history_obj = self._conv_manager.get_or_create(user_id)
        history_str = history_obj.get_context_for_llm(n=self._max_history)

        # 2. Retrieve relevant long-term memories
        raw_memories = self._store.search_memories(
            user_id, user_message, top_k=self._max_mem
        )
        memory_texts = [m["text"] for m in raw_memories]

        # 3. Build dynamic system prompt
        system_prompt = build_system_prompt(
            user_name = user_name,
            emotion   = emotion,
            memories  = memory_texts,
            history   = history_str,
        )

        # 4. Call Ollama
        reply = await self._call_ollama(system_prompt, user_message)

        # 5. Update short-term buffer
        history_obj.add_user_message(user_message, emotion)
        history_obj.add_robot_message(reply, "neutral")

        # 6. Auto-extract facts & save to long-term memory
        extracted = extract_facts(user_message)
        for fact in extracted:
            importance = score_importance(fact, emotion)
            self._store.store_memory(
                user_id    = user_id,
                text       = fact,
                emotion    = emotion,
                role       = "user",
                importance = importance,
                extra_metadata = {"source": "auto_extraction"},
            )
            logger.debug("Extracted [%s]: %s", importance, fact)

        return ChatResponse(
            reply           = reply,
            emotion         = emotion,
            user_name       = user_name,
            memories_used   = len(memory_texts),
            extracted_facts = extracted,
        )

    async def chat_stream(
        self,
        user_id:      str,
        user_name:    str,
        user_message: str,
        emotion:      str = "neutral",
    ) -> AsyncGenerator[str, None]:
        """
        Streaming variant — yields reply tokens one-by-one.
        Use with FastAPI's StreamingResponse.
        """
        history_obj = self._conv_manager.get_or_create(user_id)
        history_str = history_obj.get_context_for_llm(n=self._max_history)
        raw_memories = self._store.search_memories(user_id, user_message, top_k=self._max_mem)
        memory_texts = [m["text"] for m in raw_memories]

        system_prompt = build_system_prompt(
            user_name = user_name,
            emotion   = emotion,
            memories  = memory_texts,
            history   = history_str,
        )

        full_reply = ""
        client = ollama.AsyncClient()
        async for chunk in await client.chat(
            model    = self._model,
            messages = [
                {"role": "system",    "content": system_prompt},
                {"role": "user",      "content": user_message},
            ],
            stream = True,
        ):
            token = chunk["message"]["content"]
            full_reply += token
            yield token

        # Post-stream: update history + extract facts
        history_obj.add_user_message(user_message, emotion)
        history_obj.add_robot_message(full_reply, "neutral")
        extracted = extract_facts(user_message)
        for fact in extracted:
            importance = score_importance(fact, emotion)
            self._store.store_memory(
                user_id    = user_id,
                text       = fact,
                emotion    = emotion,
                role       = "user",
                importance = importance,
                extra_metadata = {"source": "auto_extraction_stream"},
            )

    def get_welcome_message(
        self,
        user_id:   str,
        user_name: str,
        emotion:   str,
    ) -> str:
        """Return a personalised welcome/greeting string (not an LLM call)."""
        count = self._store.get_memory_count(user_id)
        return build_welcome_message(user_name, emotion, is_returning=count > 0)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _call_ollama(self, system_prompt: str, user_message: str) -> str:
        """
        Send a single non-streaming request to Ollama.
        Falls back to a canned message if Ollama is not running.
        """
        try:
            client   = ollama.AsyncClient()
            response = await client.chat(
                model    = self._model,
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
            )
            return response["message"]["content"].strip()
        except Exception as exc:
            logger.error("Ollama call failed: %s", exc)
            return (
                "I'm having a little trouble connecting right now, but I'm here for you! "
                "Please try again in a moment."
            )
