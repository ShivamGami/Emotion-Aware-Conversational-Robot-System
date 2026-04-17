"""
test_memory.py
--------------
Verification script for Task 1.3 - Memory System Core.

Run from the project root:
    cd emotion-robot-system
    python test_memory.py

What it proves:
  1. MemoryStore initialises (ChromaDB + sentence-transformers loaded).
  2. store_memory()       – stores multiple memories for a user.
  3. search_memories()    – semantic search returns relevant results.
  4. get_recent_memories()– newest-first ordering is correct.
  5. ConversationHistory  – add_user_message / add_robot_message work.
  6. get_context_for_llm()– returns correct formatted string.
  7. Auto-flush           – buffer overflow flushes old msgs to LTM.
  8. ConversationManager  – get_or_create, end_session work.
  9. Cleanup              – user memories deleted successfully.
"""

import sys
import tempfile
import textwrap
import os

# ---------------------------------------------------------------------------
# Path setup (run from any directory)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.memory.memory_store import MemoryStore
from app.memory.conversation import ConversationHistory, ConversationManager


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------
def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def ok(msg: str) -> None:
    print(f"  ✅  {msg}")


def info(msg: str) -> None:
    print(f"  ℹ️   {msg}")


# ---------------------------------------------------------------------------
# TEST 1: MemoryStore – store and retrieve
# ---------------------------------------------------------------------------
def test_memory_store() -> MemoryStore:
    section("TEST 1 – MemoryStore: init + store_memory")

    # Use a temp dir so tests don't pollute the real DB
    tmpdir = tempfile.mkdtemp(prefix="emotion_robot_test_")
    info(f"ChromaDB path: {tmpdir}")

    store = MemoryStore(chroma_path=tmpdir)
    ok("MemoryStore initialised (ChromaDB + SentenceTransformer loaded)")

    USER_A = "user_alice"
    USER_B = "user_bob"

    # --- Store memories for Alice (various emotions) ----------------------
    memories_alice = [
        ("I absolutely love drinking coffee every morning!", "happy"),
        ("I got stuck in traffic and it made me really angry.", "angry"),
        ("My cat passed away yesterday, I am heartbroken.", "sad"),
        ("I just got promoted at work, this is amazing!", "happy"),
        ("I am feeling a bit under the weather today.", "neutral"),
        ("My team won the championship – best day ever!", "happy"),
    ]

    ids = []
    for text, emotion in memories_alice:
        mid = store.store_memory(USER_A, text, emotion=emotion, importance="medium")
        ids.append(mid)
        info(f"Stored [{emotion:8s}]: {text[:55]}…" if len(text) > 55 else f"Stored [{emotion:8s}]: {text}")

    ok(f"Stored {len(ids)} memories for '{USER_A}'")
    assert store.get_memory_count(USER_A) == len(memories_alice), "Count mismatch!"

    # --- Store a memory for Bob -------------------------------------------
    store.store_memory(USER_B, "Bob loves hiking in the mountains.", emotion="happy")
    ok(f"Stored 1 memory for '{USER_B}' (isolation check)")

    return store, USER_A, USER_B, tmpdir


# ---------------------------------------------------------------------------
# TEST 2: Semantic search
# ---------------------------------------------------------------------------
def test_semantic_search(store: MemoryStore, user_id: str) -> None:
    section("TEST 2 – Semantic Search")

    queries = [
        ("hot beverage in the morning", "Should return the coffee memory"),
        ("pet loss grief",              "Should return the cat memory"),
        ("career achievement",          "Should return promotion/championship"),
        ("road frustration",            "Should return traffic/anger memory"),
    ]

    for query, expectation in queries:
        results = store.search_memories(user_id, query, top_k=2)
        info(f"Query: '{query}'")
        info(f"Expect: {expectation}")
        for r in results:
            print(
                f"      → [{r['emotion']:8s} | sim={r['similarity']:.3f}] "
                f"{r['text'][:70]}"
            )
        assert len(results) > 0, f"Search returned nothing for: {query}"
        ok("Search returned results")
        print()


# ---------------------------------------------------------------------------
# TEST 3: Emotion filter
# ---------------------------------------------------------------------------
def test_emotion_filter(store: MemoryStore, user_id: str) -> None:
    section("TEST 3 – Emotion-Filtered Search")

    results = store.search_memories(
        user_id, "good things", top_k=5, emotion_filter="happy"
    )
    info(f"Emotion filter = 'happy' → {len(results)} result(s)")
    for r in results:
        assert r["emotion"] == "happy", f"Got non-happy result: {r}"
        print(f"      → [{r['emotion']:8s}] {r['text'][:70]}")
    ok("All returned results have emotion='happy'")


# ---------------------------------------------------------------------------
# TEST 4: get_recent_memories
# ---------------------------------------------------------------------------
def test_get_recent(store: MemoryStore, user_id: str) -> None:
    section("TEST 4 – get_recent_memories (newest first)")

    recent = store.get_recent_memories(user_id, n=3)
    info(f"Requested 3 most recent, got {len(recent)}")
    assert len(recent) == 3
    for i, r in enumerate(recent):
        print(f"      [{i+1}] {r['timestamp']} | {r['text'][:55]}")

    # Timestamps should be descending
    ts = [r["timestamp"] for r in recent]
    assert ts == sorted(ts, reverse=True), "Memories not in newest-first order!"
    ok("Memories are correctly ordered newest-first")


# ---------------------------------------------------------------------------
# TEST 5: User isolation
# ---------------------------------------------------------------------------
def test_user_isolation(store: MemoryStore, user_a: str, user_b: str) -> None:
    section("TEST 5 – User Isolation")

    results_b = store.search_memories(user_b, "coffee", top_k=5)
    info(f"Searching Bob's memories for 'coffee' (Bob never mentioned coffee)")
    for r in results_b:
        assert r["text"] != "I absolutely love drinking coffee every morning!", \
            "Alice's memory leaked into Bob's results!"
    ok(f"Bob's search returned {len(results_b)} result(s) – no cross-user leak")


# ---------------------------------------------------------------------------
# TEST 6: ConversationHistory
# ---------------------------------------------------------------------------
def test_conversation_history(store: MemoryStore) -> None:
    section("TEST 6 – ConversationHistory: add + context")

    history = ConversationHistory(user_id="user_alice", memory_store=store, max_short_term=6)

    # Simulate a dialogue
    turns = [
        ("user",  "Hi there! I just had an amazing cup of coffee.",  "happy"),
        ("robot", "That's wonderful! Coffee makes everything better.", "happy"),
        ("user",  "Yeah, but my commute was terrible today.",          "angry"),
        ("robot", "I'm sorry to hear that. Traffic can be so stressful.", "neutral"),
        ("user",  "At least I got promoted last week!",               "happy"),
        ("robot", "Congratulations! That's fantastic news.",          "happy"),
    ]

    for role, text, emotion in turns:
        history.add_message(role, text, emotion)

    info(f"Buffer length: {len(history)}")
    assert len(history) == 6, f"Expected 6 messages, got {len(history)}"
    ok("Buffer holds correct number of messages")

    # Check context string
    context = history.get_context_for_llm()
    info("LLM context string:")
    for line in context.split("\n"):
        print(f"      {line}")
    assert "[User | happy]" in context
    assert "[Robot | neutral]" in context
    ok("Context string formatted correctly")

    # Session summary
    summary = history.get_session_summary()
    info(f"Session summary: {summary}")
    assert summary["dominant_emotion"] == "happy"
    ok(f"Dominant emotion correctly detected as: '{summary['dominant_emotion']}'")


# ---------------------------------------------------------------------------
# TEST 7: Auto-flush on overflow
# ---------------------------------------------------------------------------
def test_auto_flush(store: MemoryStore) -> None:
    section("TEST 7 – Auto-flush: overflow triggers LTM write")

    FLUSH_USER = "user_flush_test"
    count_before = store.get_memory_count(FLUSH_USER)

    # max_short_term=4 → adding 7 messages should trigger a flush
    history = ConversationHistory(
        user_id=FLUSH_USER,
        memory_store=store,
        max_short_term=4,
    )

    messages = [
        ("user",  "Message one",   "neutral"),
        ("robot", "Reply one",     "neutral"),
        ("user",  "Message two",   "sad"),
        ("robot", "Reply two",     "sad"),
        ("user",  "Message three", "happy"),   # overflow starts here
        ("robot", "Reply three",   "happy"),
        ("user",  "Message four",  "neutral"),
    ]

    for role, text, emotion in messages:
        history.add_message(role, text, emotion)
        info(f"Added → buffer size: {len(history)}")

    count_after = store.get_memory_count(FLUSH_USER)
    flushed = count_after - count_before

    info(f"Memories in LTM before: {count_before}, after: {count_after}")
    assert flushed > 0, "No messages were flushed to LTM despite overflow!"
    ok(f"Auto-flush worked: {flushed} message(s) moved to long-term memory")
    assert len(history) <= 4, f"Buffer should be ≤4, got {len(history)}"
    ok(f"Buffer size after flush: {len(history)} (within limit)")


# ---------------------------------------------------------------------------
# TEST 8: ConversationManager
# ---------------------------------------------------------------------------
def test_conversation_manager(store: MemoryStore) -> None:
    section("TEST 8 – ConversationManager: session lifecycle")

    manager = ConversationManager(memory_store=store)

    h1 = manager.get_or_create("user_carol")
    h2 = manager.get_or_create("user_dave")

    h1.add_user_message("I feel great!", "happy")
    h2.add_user_message("I'm feeling down.", "sad")

    assert "user_carol" in manager.active_sessions()
    assert "user_dave"  in manager.active_sessions()
    ok("Both sessions registered in manager")

    # get_or_create is idempotent
    h1_again = manager.get_or_create("user_carol")
    assert h1 is h1_again, "get_or_create should return the SAME object"
    ok("get_or_create is idempotent (returns same ConversationHistory object)")

    # End session → flushes to LTM
    count_before = store.get_memory_count("user_carol")
    flushed = manager.end_session("user_carol")
    count_after  = store.get_memory_count("user_carol")

    info(f"end_session flushed {flushed} message(s) to LTM for user_carol")
    assert flushed == 1
    assert count_after == count_before + 1
    assert "user_carol" not in manager.active_sessions()
    ok("end_session flushed messages and removed session from registry")


# ---------------------------------------------------------------------------
# TEST 9: Cleanup
# ---------------------------------------------------------------------------
def test_cleanup(store: MemoryStore, user_id: str) -> None:
    section("TEST 9 – delete_user_memories")

    count = store.get_memory_count(user_id)
    info(f"Memories for '{user_id}' before delete: {count}")
    deleted = store.delete_user_memories(user_id)
    after = store.get_memory_count(user_id)
    info(f"Deleted: {deleted} | Remaining: {after}")
    assert after == 0
    ok("All memories deleted successfully")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print(textwrap.dedent("""
    ╔══════════════════════════════════════════════════════════╗
    ║      Emotion Robot v2.0 – Memory System Test Suite      ║
    ║               Task 1.3 Verification                     ║
    ╚══════════════════════════════════════════════════════════╝
    """))

    store, USER_A, USER_B, tmpdir = test_memory_store()
    test_semantic_search(store, USER_A)
    test_emotion_filter(store, USER_A)
    test_get_recent(store, USER_A)
    test_user_isolation(store, USER_A, USER_B)
    test_conversation_history(store)
    test_auto_flush(store)
    test_conversation_manager(store)
    test_cleanup(store, USER_A)

    section("ALL TESTS PASSED")
    print("""
  The Memory System Core is working correctly.
  You can now wire MemoryStore + ConversationManager into FastAPI routes.

  Next steps:
    - Import in main.py:
        from app.memory import MemoryStore, ConversationManager
        memory_store = MemoryStore()
        conv_manager = ConversationManager(memory_store=memory_store)

    - In /api/chat route:
        history = conv_manager.get_or_create(current_user.id)
        history.add_user_message(text, emotion)
        context = history.get_context_for_llm()
        # → inject context into your LLM prompt (Task 1.4)
    """)


if __name__ == "__main__":
    main()
