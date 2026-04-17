"""
memory_store.py
---------------
Long-term, persistent vector memory for the Emotion Robot.

Responsibilities:
  - Embed text with sentence-transformers (all-MiniLM-L6-v2)
  - Persist memories per-user in ChromaDB (local disk)
  - Expose: store_memory, search_memories, get_recent_memories, delete_user_memories

Design notes:
  - ChromaDB collection is created once; subsequent calls reuse it.
  - Embeddings are generated locally (no API key required).
  - Each memory carries rich metadata so the LLM layer can construct
    natural-language references like "last Tuesday you felt happy".
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLLECTION_NAME = "emotion_robot_memories"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_CHROMA_PATH = "./data/chroma_db"          # relative to backend run dir
DEFAULT_TOP_K = 5                                  # semantic search results
MAX_MEMORIES_PER_USER = 100                        # pruning ceiling (per plan doc)


# ---------------------------------------------------------------------------
# Helper: iso timestamp
# ---------------------------------------------------------------------------
def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------
class MemoryStore:
    """
    Persistent long-term memory backed by ChromaDB + sentence-transformers.

    Usage
    -----
    store = MemoryStore()                      # singleton-friendly; init once
    store.store_memory("user_42", "I love coffee", emotion="happy")
    results = store.search_memories("user_42", "beverages")
    recent  = store.get_recent_memories("user_42", n=5)
    """

    def __init__(
        self,
        chroma_path: str = DEFAULT_CHROMA_PATH,
        embedding_model: str = EMBEDDING_MODEL,
    ) -> None:
        logger.info("Initialising MemoryStore …")

        # --- ChromaDB (persistent, local) -----------------------------------
        self._client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            # cosine is better than L2 for sentence embeddings
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection '%s' ready.", COLLECTION_NAME)

        # --- Embedding model ------------------------------------------------
        logger.info("Loading embedding model '%s' …", embedding_model)
        self._embedder = SentenceTransformer(embedding_model)
        logger.info("MemoryStore ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store_memory(
        self,
        user_id: str,
        text: str,
        *,
        emotion: str = "neutral",
        role: str = "user",          # "user" | "robot"
        importance: str = "medium",  # "low" | "medium" | "high"
        extra_metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Embed *text* and persist it as a memory for *user_id*.

        Returns
        -------
        str
            The UUID assigned to this memory (useful for linking / deletion).
        """
        memory_id = str(uuid.uuid4())
        embedding = self._embed(text)

        metadata: dict[str, Any] = {
            "user_id": user_id,
            "emotion": emotion,
            "role": role,
            "importance": importance,
            "timestamp": _utcnow_iso(),
            "text": text,           # store raw text so retrieval doesn't need
        }                           # a second DB call

        if extra_metadata:
            metadata.update(extra_metadata)

        self._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

        logger.debug("Stored memory %s for user '%s' (emotion=%s).", memory_id, user_id, emotion)

        # Prune if over ceiling
        self._prune_if_needed(user_id)

        return memory_id

    def search_memories(
        self,
        user_id: str,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        emotion_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search over *user_id*'s memories.

        Parameters
        ----------
        query:
            Natural-language search string (e.g. "beverages", "work stress").
        top_k:
            Number of results to return.
        emotion_filter:
            Optional – restrict search to memories tagged with this emotion.

        Returns
        -------
        list of dicts, each with keys:
            id, text, emotion, role, importance, timestamp, distance
        """
        if emotion_filter:
            where = {"$and": [{"user_id": user_id}, {"emotion": emotion_filter}]}
        else:
            where = {"user_id": user_id}

        # Safety: ChromaDB raises if collection is empty
        total = self._user_memory_count(user_id)
        if total == 0:
            return []

        n_results = min(top_k, total)

        query_embedding = self._embed(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return self._format_results(results)

    def get_recent_memories(
        self,
        user_id: str,
        *,
        n: int = 10,
        role_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return the *n* most-recently stored memories for *user_id*,
        sorted newest-first.

        Parameters
        ----------
        role_filter:
            Optional – "user" or "robot".
        """
        if role_filter:
            where = {"$and": [{"user_id": user_id}, {"role": role_filter}]}
        else:
            where = {"user_id": user_id}

        total = self._user_memory_count(user_id)
        if total == 0:
            return []

        # ChromaDB get() doesn't support ORDER BY; fetch all and sort in Python.
        # For ≤ 100 memories per user this is perfectly fast.
        raw = self._collection.get(
            where=where,
            include=["documents", "metadatas"],
        )

        memories = []
        for mem_id, doc, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            memories.append({
                "id": mem_id,
                "text": doc,
                **{k: v for k, v in meta.items() if k != "text"},
            })

        # Sort by ISO timestamp descending (lexicographic works for ISO-8601)
        memories.sort(key=lambda m: m.get("timestamp", ""), reverse=True)

        return memories[:n]

    def delete_user_memories(self, user_id: str) -> int:
        """
        Hard-delete ALL memories for *user_id*.

        Returns
        -------
        int
            Number of memories deleted.
        """
        total = self._user_memory_count(user_id)
        if total == 0:
            return 0

        raw = self._collection.get(where={"user_id": user_id}, include=[])
        ids_to_delete = raw["ids"]
        self._collection.delete(ids=ids_to_delete)
        logger.info("Deleted %d memories for user '%s'.", len(ids_to_delete), user_id)
        return len(ids_to_delete)

    def get_memory_count(self, user_id: str) -> int:
        """Return total stored memories for *user_id*."""
        return self._user_memory_count(user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float]:
        """Return a normalised embedding vector for *text*."""
        return self._embedder.encode(text, normalize_embeddings=True).tolist()

    def _user_memory_count(self, user_id: str) -> int:
        result = self._collection.get(where={"user_id": user_id}, include=[])
        return len(result["ids"])

    def _prune_if_needed(self, user_id: str) -> None:
        """
        Keep only the most recent MAX_MEMORIES_PER_USER memories.
        Prunes lowest-importance / oldest memories first.
        """
        total = self._user_memory_count(user_id)
        if total <= MAX_MEMORIES_PER_USER:
            return

        # Fetch all, sort by importance then timestamp, drop oldest low-importance
        raw = self._collection.get(
            where={"user_id": user_id},
            include=["metadatas"],
        )

        importance_rank = {"low": 0, "medium": 1, "high": 2}
        entries = [
            {"id": mid, **meta}
            for mid, meta in zip(raw["ids"], raw["metadatas"])
        ]
        # Sort: low importance first, oldest first → delete from front
        entries.sort(key=lambda e: (
            importance_rank.get(e.get("importance", "medium"), 1),
            e.get("timestamp", ""),
        ))

        n_to_delete = total - MAX_MEMORIES_PER_USER
        ids_to_delete = [e["id"] for e in entries[:n_to_delete]]
        self._collection.delete(ids=ids_to_delete)
        logger.info(
            "Pruned %d low-priority memories for user '%s' (kept %d).",
            n_to_delete, user_id, MAX_MEMORIES_PER_USER,
        )

    @staticmethod
    def _format_results(chroma_results: dict[str, Any]) -> list[dict[str, Any]]:
        """Flatten ChromaDB query() response into a clean list of dicts."""
        formatted = []
        ids       = chroma_results.get("ids", [[]])[0]
        docs      = chroma_results.get("documents", [[]])[0]
        metas     = chroma_results.get("metadatas", [[]])[0]
        distances = chroma_results.get("distances", [[]])[0]

        for mem_id, doc, meta, dist in zip(ids, docs, metas, distances):
            formatted.append({
                "id":         mem_id,
                "text":       doc,
                "emotion":    meta.get("emotion", "neutral"),
                "role":       meta.get("role", "user"),
                "importance": meta.get("importance", "medium"),
                "timestamp":  meta.get("timestamp", ""),
                # cosine distance → similarity score (0-1, higher = more similar)
                "similarity": round(1.0 - dist, 4),
            })

        return formatted
