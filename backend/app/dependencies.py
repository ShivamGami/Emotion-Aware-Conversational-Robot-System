"""
dependencies.py
---------------
Shared singletons and global instances for the Emotion Robot.
Used to avoid circular imports between main.py and various routers.
"""

from app.memory import MemoryStore, ConversationManager
from app.llm import ChatEngine

# ── Shared singletons (init once at startup) ──────────────────────────────────

# 1. Long-term memory
memory_store = MemoryStore()

# 2. Short-term session manager
conv_manager = ConversationManager(memory_store=memory_store)

# 3. Conversational AI Engine
chat_engine  = ChatEngine(memory_store=memory_store, conv_manager=conv_manager)
