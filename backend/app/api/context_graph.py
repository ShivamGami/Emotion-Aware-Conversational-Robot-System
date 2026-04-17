"""
context_graph.py
----------------
Task 1.5 – Context Graph Visualisation Data

Responsibilities
────────────────
1. Pull all memories for a user from ChromaDB (via MemoryStore).
2. Build a typed graph:
      • User node      – the authenticated user
      • Memory nodes   – individual stored memories
      • Emotion nodes  – one per distinct emotion label
      • Topic nodes    – k-means clusters of semantically similar memories
3. Compute edges with similarity-based weights.
4. Expose GET /api/context/graph  →  {"nodes": [...], "edges": [...]}

Consumed by: React Three Fiber 3-D graph on the frontend.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
DEFAULT_N_TOPICS  = 4          # K for K-Means (topic clusters)
MIN_MEMORIES_FOR_CLUSTER = 4   # need at least this many to run K-Means
MIN_EDGE_SIMILARITY = 0.30     # cosine similarity threshold for Memory↔Topic edges

# Colour palette (used by the 3-D renderer for each node type)
NODE_COLOURS: dict[str, str] = {
    "user":    "#4FC3F7",   # sky blue
    "memory":  "#A5D6A7",   # soft green
    "emotion": "#FF8A65",   # warm orange
    "topic":   "#CE93D8",   # light purple
}

# ── Shared embedder (load once per process) ────────────────────────────────
_embedder: SentenceTransformer | None = None

def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model '%s' …", EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model ready.")
    return _embedder


# ── Pydantic response schemas ──────────────────────────────────────────────

class GraphNode(BaseModel):
    id:     str
    label:  str
    type:   str               # "user" | "memory" | "emotion" | "topic"
    colour: str
    # Optional spatial hint for the 3-D layout (cluster centroid coords)
    x:  float = 0.0
    y:  float = 0.0
    z:  float = 0.0
    # Extra metadata the frontend can display on hover
    meta: dict[str, Any] = {}


class GraphEdge(BaseModel):
    id:     str
    source: str               # node id
    target: str               # node id
    weight: float             # 0.0 – 1.0  (edge thickness / opacity)
    type:   str               # "user_memory" | "memory_emotion" | "memory_topic"


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    meta:  dict[str, Any] = {}


# ── Core graph builder ─────────────────────────────────────────────────────

class ContextGraphBuilder:
    """
    Stateless graph builder – create once at startup or per-request.

    Usage
    -----
    builder = ContextGraphBuilder()
    graph   = builder.build(user_id, raw_memories)
    """

    def __init__(self, n_topics: int = DEFAULT_N_TOPICS) -> None:
        self._n_topics  = n_topics
        self._embedder  = _get_embedder()

    # ── Public ─────────────────────────────────────────────────────────────

    def build(
        self,
        user_id:      str,
        raw_memories: list[dict[str, Any]],
    ) -> GraphResponse:
        """
        Parameters
        ----------
        user_id:
            The authenticated user's ID.
        raw_memories:
            List of memory dicts as returned by MemoryStore.get_recent_memories().
            Each dict must have: id, text, emotion, role, timestamp.

        Returns
        -------
        GraphResponse
            Fully typed nodes + edges ready for JSON serialisation.
        """
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # ── 1. User node ────────────────────────────────────────────────────
        user_node = GraphNode(
            id     = f"user_{user_id}",
            label  = f"User: {user_id}",
            type   = "user",
            colour = NODE_COLOURS["user"],
            meta   = {"memory_count": len(raw_memories)},
        )
        nodes.append(user_node)

        if not raw_memories:
            return GraphResponse(nodes=nodes, edges=edges, meta={"empty": True})

        # ── 2. Memory nodes ─────────────────────────────────────────────────
        memory_nodes: list[GraphNode] = []
        for mem in raw_memories:
            mn = GraphNode(
                id     = f"mem_{mem['id']}",
                label  = mem["text"][:60] + ("…" if len(mem["text"]) > 60 else ""),
                type   = "memory",
                colour = NODE_COLOURS["memory"],
                meta   = {
                    "full_text":  mem["text"],
                    "emotion":    mem.get("emotion",    "neutral"),
                    "role":       mem.get("role",       "user"),
                    "timestamp":  mem.get("timestamp",  ""),
                    "importance": mem.get("importance", "medium"),
                },
            )
            memory_nodes.append(mn)
            nodes.append(mn)

            # Edge: user → memory
            edges.append(GraphEdge(
                id     = str(uuid.uuid4()),
                source = user_node.id,
                target = mn.id,
                weight = 0.6,
                type   = "user_memory",
            ))

        # ── 3. Emotion nodes ────────────────────────────────────────────────
        distinct_emotions: dict[str, GraphNode] = {}
        for mem, mn in zip(raw_memories, memory_nodes):
            emo = mem.get("emotion", "neutral").lower()
            if emo not in distinct_emotions:
                emo_node = GraphNode(
                    id     = f"emo_{emo}",
                    label  = emo.capitalize(),
                    type   = "emotion",
                    colour = NODE_COLOURS["emotion"],
                    meta   = {"emotion": emo},
                )
                distinct_emotions[emo] = emo_node
                nodes.append(emo_node)

            # Edge: memory → emotion
            edges.append(GraphEdge(
                id     = str(uuid.uuid4()),
                source = mn.id,
                target = distinct_emotions[emo].id,
                weight = 0.8,
                type   = "memory_emotion",
            ))

        # ── 4. Embed memories ───────────────────────────────────────────────
        texts      = [m["text"] for m in raw_memories]
        embeddings = self._embedder.encode(texts, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)

        # ── 5. Topic nodes (K-Means clustering) ────────────────────────────
        k = min(self._n_topics, len(raw_memories) // 1)
        if len(raw_memories) >= MIN_MEMORIES_FOR_CLUSTER and k >= 2:
            topic_nodes, topic_edges = self._build_topic_nodes(
                memory_nodes, embeddings, k
            )
        else:
            # Not enough memories – create a single "General" topic
            topic_nodes, topic_edges = self._single_topic_fallback(
                memory_nodes, embeddings
            )

        nodes.extend(topic_nodes)
        edges.extend(topic_edges)

        # ── 6. Spatial layout hint ──────────────────────────────────────────
        #    Reduce 384-dim embeddings to 3-D via a simple random-projection
        #    so the frontend can use these as initial positions.
        nodes = self._assign_positions(nodes, memory_nodes, embeddings)

        return GraphResponse(
            nodes = nodes,
            edges = edges,
            meta  = {
                "user_id":       user_id,
                "memory_count":  len(raw_memories),
                "topic_count":   len(topic_nodes),
                "emotion_count": len(distinct_emotions),
            },
        )

    # ── Private helpers ─────────────────────────────────────────────────────

    def _build_topic_nodes(
        self,
        memory_nodes: list[GraphNode],
        embeddings:   np.ndarray,
        k:            int,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Run K-Means and create topic nodes + edges."""
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        centroids = normalize(km.cluster_centers_, norm="l2")

        topic_nodes: list[GraphNode] = []
        topic_edges: list[GraphEdge] = []

        for cluster_idx in range(k):
            topic_id = f"topic_{cluster_idx}"
            # Pick the memory closest to the centroid as the topic label
            mask = np.where(labels == cluster_idx)[0]
            if len(mask) == 0:
                continue

            sims = cosine_similarity(
                embeddings[mask],
                centroids[cluster_idx:cluster_idx + 1],
            ).flatten()
            representative_idx = mask[int(np.argmax(sims))]
            rep_text = memory_nodes[representative_idx].label

            t_node = GraphNode(
                id     = topic_id,
                label  = f"Topic {cluster_idx + 1}: {rep_text[:40]}",
                type   = "topic",
                colour = NODE_COLOURS["topic"],
                meta   = {
                    "cluster_id":        cluster_idx,
                    "member_count":      int(len(mask)),
                    "representative":    rep_text,
                },
            )
            topic_nodes.append(t_node)

            # Edges: memory → topic  (weight = cosine similarity)
            for mem_idx in mask:
                sim = float(cosine_similarity(
                    embeddings[mem_idx:mem_idx + 1],
                    centroids[cluster_idx:cluster_idx + 1],
                ).flatten()[0])
                if sim >= MIN_EDGE_SIMILARITY:
                    topic_edges.append(GraphEdge(
                        id     = str(uuid.uuid4()),
                        source = memory_nodes[mem_idx].id,
                        target = topic_id,
                        weight = round(sim, 4),
                        type   = "memory_topic",
                    ))

        return topic_nodes, topic_edges

    def _single_topic_fallback(
        self,
        memory_nodes: list[GraphNode],
        embeddings:   np.ndarray,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """When there are too few memories for K-Means."""
        t_node = GraphNode(
            id     = "topic_0",
            label  = "General Memories",
            type   = "topic",
            colour = NODE_COLOURS["topic"],
            meta   = {"cluster_id": 0, "member_count": len(memory_nodes)},
        )
        edges = [
            GraphEdge(
                id     = str(uuid.uuid4()),
                source = mn.id,
                target = "topic_0",
                weight = 0.5,
                type   = "memory_topic",
            )
            for mn in memory_nodes
        ]
        return [t_node], edges

    @staticmethod
    def _assign_positions(
        all_nodes:    list[GraphNode],
        memory_nodes: list[GraphNode],
        embeddings:   np.ndarray,
    ) -> list[GraphNode]:
        """
        Project 384-dim embeddings to 3-D with a deterministic random projection.
        Assigns x, y, z to memory nodes; other nodes use default (0,0,0).
        """
        if len(memory_nodes) == 0:
            return all_nodes

        rng       = np.random.default_rng(seed=42)
        proj      = rng.standard_normal((embeddings.shape[1], 3)).astype(np.float32)
        proj      = proj / np.linalg.norm(proj, axis=0)
        coords    = embeddings @ proj           # (N, 3)
        # Scale to [-10, 10] range for the 3-D scene
        for axis in range(3):
            col = coords[:, axis]
            rng_val = col.max() - col.min()
            if rng_val > 0:
                coords[:, axis] = (col - col.min()) / rng_val * 20 - 10

        # Build a lookup: node_id → position
        mem_id_to_pos: dict[str, tuple[float, float, float]] = {
            mn.id: (float(coords[i, 0]), float(coords[i, 1]), float(coords[i, 2]))
            for i, mn in enumerate(memory_nodes)
        }

        updated: list[GraphNode] = []
        for node in all_nodes:
            if node.id in mem_id_to_pos:
                x, y, z = mem_id_to_pos[node.id]
                updated.append(node.model_copy(update={"x": x, "y": y, "z": z}))
            else:
                updated.append(node)
        return updated


# ── FastAPI router ──────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/context", tags=["Context Graph"])

# Shared builder instance (models loaded once)
_builder = ContextGraphBuilder()


def _get_memory_store():
    """
    Dependency-injection helper.
    Imports here to avoid circular imports at module load time.
    """
    from app.dependencies import memory_store  # noqa: PLC0415
    return memory_store


@router.get("/graph", response_model=GraphResponse, summary="Context Graph for 3-D visualisation")
async def get_context_graph(
    user_id:  str = Query(..., description="The user whose memory graph to build"),
    n_topics: int = Query(DEFAULT_N_TOPICS, ge=2, le=10, description="Number of topic clusters"),
    limit:    int = Query(50,  ge=1, le=200, description="Max memories to include"),
    memory_store = Depends(_get_memory_store),
) -> GraphResponse:
    """
    Fetch the user's long-term memories and return a structured graph
    payload containing nodes (User, Memory, Emotion, Topic) and edges
    with cosine-similarity weights.

    This endpoint is consumed by the React Three Fiber 3-D graph.
    """
    try:
        raw_memories = memory_store.get_recent_memories(user_id, n=limit)
    except Exception as exc:
        logger.error("Failed to fetch memories for user '%s': %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch memories from store.")

    builder = ContextGraphBuilder(n_topics=n_topics)
    try:
        graph = builder.build(user_id=user_id, raw_memories=raw_memories)
    except Exception as exc:
        logger.error("Graph build failed for user '%s': %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Graph generation failed.")

    logger.info(
        "Graph built for user '%s': %d nodes, %d edges.",
        user_id, len(graph.nodes), len(graph.edges),
    )
    return graph
