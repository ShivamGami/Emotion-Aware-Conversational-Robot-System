"""
conversation.py
---------------
Short-term, in-session conversation context for the Emotion Robot.

Responsibilities:
  - Hold the last N messages of an active session in memory (fast, no I/O).
  - Expose a formatted context string that can be injected directly into
    the LLM prompt.
  - Automatically flush older turns into MemoryStore (long-term) when the
    buffer exceeds its capacity.
  - Provide session-level emotion tracking (what was the dominant emotion?).

Design notes:
  - ConversationHistory is per-user; instantiate one per active session.
  - ConversationManager is a process-level registry of all active sessions,
    making it easy to retrieve or create a session from a FastAPI route.
  - Thread-safety: individual ConversationHistory objects are not lock-
    protected (single async event loop is safe); ConversationManager uses
    a plain dict (also safe in CPython's GIL).
"""

from __future__ import annotations

import logging
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .memory_store import MemoryStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_SHORT_TERM = 10          # messages kept in active buffer
FLUSH_BATCH_SIZE = 5         # how many messages to flush at once to LTM
IMPORTANCE_MAP: dict[str, str] = {
    # Emotionally charged messages get higher importance in LTM
    "happy":    "medium",
    "sad":      "high",
    "angry":    "high",
    "fear":     "high",
    "surprise": "medium",
    "disgust":  "medium",
    "neutral":  "low",
}


# ---------------------------------------------------------------------------
# Data model: a single message in the conversation
# ---------------------------------------------------------------------------
@dataclass
class Message:
    role: str                          # "user" | "robot"
    text: str
    emotion: str = "neutral"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "role":      self.role,
            "text":      self.text,
            "emotion":   self.emotion,
            "timestamp": self.timestamp,
        }

    def to_prompt_line(self) -> str:
        """Human-readable line for LLM context injection."""
        role_label = "User" if self.role == "user" else "Robot"
        return f"[{role_label} | {self.emotion}]: {self.text}"


# ---------------------------------------------------------------------------
# Per-user session
# ---------------------------------------------------------------------------
class ConversationHistory:
    """
    Manages the short-term dialogue buffer for a single user session.

    Parameters
    ----------
    user_id:
        Unique identifier for the authenticated user.
    memory_store:
        A MemoryStore instance. Pass None to disable auto-flush to LTM
        (useful for unit tests).
    max_short_term:
        Maximum number of messages to hold before flushing older ones.
    """

    def __init__(
        self,
        user_id: str,
        memory_store: MemoryStore | None = None,
        max_short_term: int = MAX_SHORT_TERM,
    ) -> None:
        self.user_id = user_id
        self._memory_store = memory_store
        self._max = max_short_term

        # deque gives O(1) append and popleft
        self._buffer: deque[Message] = deque()
        self._emotion_counts: Counter[str] = Counter()

        logger.debug("ConversationHistory created for user '%s'.", user_id)

    # ------------------------------------------------------------------
    # Adding messages
    # ------------------------------------------------------------------

    def add_message(
        self,
        role: str,
        text: str,
        emotion: str = "neutral",
    ) -> Message:
        """
        Append a new message to the short-term buffer.

        If the buffer is full the oldest messages are flushed to long-term
        memory before the new message is added.

        Returns
        -------
        Message
            The newly created Message object.
        """
        msg = Message(role=role, text=text, emotion=emotion)
        self._buffer.append(msg)
        self._emotion_counts[emotion] += 1

        # Flush if over limit
        if len(self._buffer) > self._max:
            self._flush_oldest(n=FLUSH_BATCH_SIZE)

        return msg

    def add_user_message(self, text: str, emotion: str = "neutral") -> Message:
        """Convenience wrapper for a user turn."""
        return self.add_message("user", text, emotion)

    def add_robot_message(self, text: str, emotion: str = "neutral") -> Message:
        """Convenience wrapper for a robot turn."""
        return self.add_message("robot", text, emotion)

    # ------------------------------------------------------------------
    # Retrieving context
    # ------------------------------------------------------------------

    def get_recent_messages(self, n: int | None = None) -> list[Message]:
        """
        Return the most recent *n* messages (all if n is None), newest last.
        """
        msgs = list(self._buffer)
        if n is not None:
            msgs = msgs[-n:]
        return msgs

    def get_context_for_llm(
        self,
        *,
        n: int | None = None,
        include_emotions: bool = True,
    ) -> str:
        """
        Return a formatted multi-line string ready for LLM prompt injection.

        Example output::

            [User | happy]: I love coffee!
            [Robot | happy]: That's great! Coffee is wonderful.
            [User | neutral]: Tell me a joke.
        """
        msgs = self.get_recent_messages(n)
        if include_emotions:
            return "\n".join(m.to_prompt_line() for m in msgs)
        else:
            role_label = lambda m: "User" if m.role == "user" else "Robot"
            return "\n".join(f"[{role_label(m)}]: {m.text}" for m in msgs)

    def get_session_summary(self) -> dict:
        """
        Return a lightweight summary of the current session – useful for
        analytics and for the LLM to understand session mood.
        """
        dominant_emotion = (
            self._emotion_counts.most_common(1)[0][0]
            if self._emotion_counts
            else "neutral"
        )
        return {
            "user_id":          self.user_id,
            "message_count":    len(self._buffer),
            "emotion_counts":   dict(self._emotion_counts),
            "dominant_emotion": dominant_emotion,
        }

    def get_dominant_emotion(self) -> str:
        """Return the most frequently detected emotion in this session."""
        if not self._emotion_counts:
            return "neutral"
        return self._emotion_counts.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def flush_all_to_memory(self) -> int:
        """
        Force-flush every message in the buffer to long-term memory.
        Called at session end (logout / timeout).

        Returns
        -------
        int
            Number of messages flushed.
        """
        return self._flush_oldest(n=len(self._buffer), clear=True)

    def clear(self) -> None:
        """Wipe the short-term buffer (does NOT flush to LTM)."""
        self._buffer.clear()
        self._emotion_counts.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _flush_oldest(self, n: int, clear: bool = False) -> int:
        """
        Pop the *n* oldest messages from the buffer and write them to the
        long-term MemoryStore.

        Parameters
        ----------
        n:
            Number of messages to flush.
        clear:
            If True, flush and then clear the entire remaining buffer too.

        Returns
        -------
        int
            Number of messages actually flushed.
        """
        if self._memory_store is None:
            # No LTM configured – just drop old messages silently
            to_drop = min(n, len(self._buffer) - self._max)
            for _ in range(max(0, to_drop)):
                self._buffer.popleft()
            return 0

        to_flush: list[Message] = []

        if clear:
            to_flush = list(self._buffer)
            self._buffer.clear()
        else:
            flush_count = min(n, len(self._buffer))
            for _ in range(flush_count):
                to_flush.append(self._buffer.popleft())

        for msg in to_flush:
            importance = IMPORTANCE_MAP.get(msg.emotion, "medium")
            self._memory_store.store_memory(
                user_id=self.user_id,
                text=msg.text,
                emotion=msg.emotion,
                role=msg.role,
                importance=importance,
                extra_metadata={"source": "conversation_flush"},
            )

        logger.debug(
            "Flushed %d messages to LTM for user '%s'.",
            len(to_flush), self.user_id,
        )
        return len(to_flush)

    def __len__(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return (
            f"ConversationHistory(user_id={self.user_id!r}, "
            f"messages={len(self._buffer)}, "
            f"dominant={self.get_dominant_emotion()!r})"
        )


# ---------------------------------------------------------------------------
# Process-level session registry
# ---------------------------------------------------------------------------
class ConversationManager:
    """
    Singleton-style registry that maps user_id → ConversationHistory.

    Typical FastAPI usage
    ---------------------
    manager = ConversationManager(memory_store=store)   # create once at startup

    # Inside a route:
    history = manager.get_or_create(user_id)
    history.add_user_message(text, emotion)
    context = history.get_context_for_llm()
    """

    def __init__(self, memory_store: MemoryStore | None = None) -> None:
        self._store = memory_store
        self._sessions: dict[str, ConversationHistory] = {}

    def get_or_create(self, user_id: str) -> ConversationHistory:
        """
        Return the existing ConversationHistory for *user_id*, or create a
        fresh one if this is a new session.
        """
        if user_id not in self._sessions:
            self._sessions[user_id] = ConversationHistory(
                user_id=user_id,
                memory_store=self._store,
            )
            logger.info("New session opened for user '%s'.", user_id)
        return self._sessions[user_id]

    def end_session(self, user_id: str) -> int:
        """
        Flush all remaining short-term messages to LTM and remove the session.

        Returns
        -------
        int
            Number of messages flushed to long-term memory.
        """
        history = self._sessions.pop(user_id, None)
        if history is None:
            return 0
        flushed = history.flush_all_to_memory()
        logger.info(
            "Session ended for user '%s'; flushed %d messages to LTM.",
            user_id, flushed,
        )
        return flushed

    def active_sessions(self) -> list[str]:
        """Return a list of currently active user IDs."""
        return list(self._sessions.keys())

    def get_all_summaries(self) -> list[dict]:
        """Return session summaries for all active users (useful for admin/debug)."""
        return [h.get_session_summary() for h in self._sessions.values()]

    def __repr__(self) -> str:
        return f"ConversationManager(active_sessions={len(self._sessions)})"
