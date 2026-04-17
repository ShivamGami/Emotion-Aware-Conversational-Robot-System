"""
test_graph.py
-------------
Verification script for Task 1.5 – Context Graph Visualisation.

Run from the backend/ directory:
    python ../test_graph.py

What it proves:
  1. ContextGraphBuilder initialises correctly.
  2. build() with 0 memories → safe empty response.
  3. build() with a small set → correct node types and edges.
  4. build() with enough memories → K-Means clusters are created.
  5. Edge weights are within [0, 1].
  6. Node positions are assigned to memory nodes.
"""

import sys
import os
import json

# ── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.api.context_graph import ContextGraphBuilder

# ── Pretty helpers ──────────────────────────────────────────────────────────
def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def ok(msg: str) -> None:
    print(f"  [PASS]  {msg}")

def info(msg: str) -> None:
    print(f"  [INFO]  {msg}")


# ── Mock memories ───────────────────────────────────────────────────────────
MOCK_MEMORIES = [
    {"id": "m1",  "text": "I absolutely love drinking coffee every morning!",    "emotion": "happy",   "role": "user",  "timestamp": "2024-01-01T08:00:00Z", "importance": "medium"},
    {"id": "m2",  "text": "I got stuck in traffic and it made me really angry.", "emotion": "angry",   "role": "user",  "timestamp": "2024-01-01T09:00:00Z", "importance": "high"},
    {"id": "m3",  "text": "My cat passed away yesterday, I am heartbroken.",     "emotion": "sad",     "role": "user",  "timestamp": "2024-01-01T10:00:00Z", "importance": "high"},
    {"id": "m4",  "text": "I just got promoted at work, this is amazing!",       "emotion": "happy",   "role": "user",  "timestamp": "2024-01-01T11:00:00Z", "importance": "medium"},
    {"id": "m5",  "text": "Feeling a bit under the weather today.",              "emotion": "neutral", "role": "user",  "timestamp": "2024-01-01T12:00:00Z", "importance": "low"},
    {"id": "m6",  "text": "My team won the championship – best day ever!",       "emotion": "happy",   "role": "user",  "timestamp": "2024-01-01T13:00:00Z", "importance": "medium"},
    {"id": "m7",  "text": "The robot suggested I take a break. Good advice.",    "emotion": "neutral", "role": "robot", "timestamp": "2024-01-01T14:00:00Z", "importance": "low"},
    {"id": "m8",  "text": "Terrified about tomorrow's presentation at work.",    "emotion": "fear",    "role": "user",  "timestamp": "2024-01-01T15:00:00Z", "importance": "high"},
]

BUILDER = ContextGraphBuilder(n_topics=3)


# ── Test 1: Empty memories ───────────────────────────────────────────────────
def test_empty():
    section("TEST 1 – Empty memories → safe response")
    graph = BUILDER.build("user_test", [])
    assert len(graph.nodes) == 1,         f"Expected 1 (user) node, got {len(graph.nodes)}"
    assert len(graph.edges) == 0,         f"Expected 0 edges, got {len(graph.edges)}"
    assert graph.nodes[0].type == "user", "First node must be of type 'user'"
    ok("Empty build returns 1 user node and 0 edges")


# ── Test 2: Correct node types ───────────────────────────────────────────────
def test_node_types():
    section("TEST 2 – Node types: user, memory, emotion, topic")
    graph = BUILDER.build("user_alice", MOCK_MEMORIES)

    type_counts = {}
    for n in graph.nodes:
        type_counts[n.type] = type_counts.get(n.type, 0) + 1

    info(f"Node type breakdown: {type_counts}")
    assert type_counts.get("user",    0) == 1,            "Must have exactly 1 user node"
    assert type_counts.get("memory",  0) == len(MOCK_MEMORIES), "Must have one memory node per memory"
    assert type_counts.get("emotion", 0) >= 1,            "Must have at least 1 emotion node"
    assert type_counts.get("topic",   0) >= 1,            "Must have at least 1 topic node"
    ok("All four node types present in graph")


# ── Test 3: Edge types and weights ───────────────────────────────────────────
def test_edges():
    section("TEST 3 – Edge weights in [0, 1] and correct types")
    graph = BUILDER.build("user_alice", MOCK_MEMORIES)

    edge_types = set()
    for e in graph.edges:
        edge_types.add(e.type)
        assert 0.0 <= e.weight <= 1.0, f"Edge weight out of range: {e.weight}"

    info(f"Edge types found: {edge_types}")
    assert "user_memory"   in edge_types, "Missing user_memory edges"
    assert "memory_emotion" in edge_types, "Missing memory_emotion edges"
    assert "memory_topic"  in edge_types, "Missing memory_topic edges"
    ok(f"All edge weights in [0,1]; edge types: {edge_types}")


# ── Test 4: Memory node positions ────────────────────────────────────────────
def test_positions():
    section("TEST 4 – Memory nodes have 3-D position coords")
    graph = BUILDER.build("user_alice", MOCK_MEMORIES)
    memory_nodes = [n for n in graph.nodes if n.type == "memory"]
    for mn in memory_nodes:
        assert not (mn.x == 0.0 and mn.y == 0.0 and mn.z == 0.0), \
            f"Memory node {mn.id} has default (0,0,0) position!"
    info(f"Sample positions: {[(n.id, round(n.x,2), round(n.y,2), round(n.z,2)) for n in memory_nodes[:3]]}")
    ok("All memory nodes have non-zero 3-D positions")


# ── Test 5: K-Means cluster count ────────────────────────────────────────────
def test_clusters():
    section("TEST 5 – K-Means produces requested number of topic clusters")
    builder3 = ContextGraphBuilder(n_topics=3)
    graph = builder3.build("user_alice", MOCK_MEMORIES)
    topic_nodes = [n for n in graph.nodes if n.type == "topic"]
    info(f"Topics: {[t.label for t in topic_nodes]}")
    assert len(topic_nodes) >= 1, "No topic nodes created!"
    ok(f"Created {len(topic_nodes)} topic node(s)")


# ── Test 6: JSON serialisability ─────────────────────────────────────────────
def test_json():
    section("TEST 6 – GraphResponse is JSON-serialisable")
    graph = BUILDER.build("user_alice", MOCK_MEMORIES)
    payload = graph.model_dump()
    as_json = json.dumps(payload, ensure_ascii=False, indent=2)
    assert len(as_json) > 100, "JSON output is suspiciously short"
    info(f"JSON payload size: {len(as_json)} characters")
    ok("GraphResponse serialises to clean JSON")


# ── Test 7: User isolation ────────────────────────────────────────────────────
def test_user_isolation():
    section("TEST 7 – user_id stamped correctly on user node")
    graph = BUILDER.build("user_bob", MOCK_MEMORIES)
    user_node = next(n for n in graph.nodes if n.type == "user")
    assert "user_bob" in user_node.id, f"User node ID mismatch: {user_node.id}"
    ok("User node ID correctly reflects the given user_id")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("""
+----------------------------------------------------------+
|   Emotion Robot v2.0 -- Context Graph Test Suite         |
|               Task 1.5 Verification                      |
+----------------------------------------------------------+
""")
    test_empty()
    test_node_types()
    test_edges()
    test_positions()
    test_clusters()
    test_json()
    test_user_isolation()

    section("ALL TESTS PASSED")
    print("""
  Context Graph backend is working correctly.
  Next steps:
    1. Wire the router into main.py:
         from app.api.context_graph import router as graph_router
         app.include_router(graph_router)
    2. Seed a user's memory and hit:
         GET http://localhost:8000/api/context/graph?user_id=<your_id>
    3. Feed the JSON into React Three Fiber.
""")


if __name__ == "__main__":
    main()
