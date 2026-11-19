# ================================================
# Phase 3 — mem0 Long-Term Memory
#
# WHAT THIS ADDS:
#   Old: session history lives in Python RAM — lost on restart
#   New: every Q&A is saved to disk per user via mem0
#        relevant past memories are injected into every new question
#
# HOW mem0 WORKS:
#   1. You call add() with a conversation → mem0 uses the LLM to extract
#      key facts ("user asked about FMLA", "user is a contractor")
#   2. Those facts are stored as embeddings in a local Qdrant vector store
#   3. On the next question, search() finds the most relevant past memories
#   4. Those memories are added to the LangGraph agent's context
#
# MENTAL MODEL:
#   mem0 is like a smart notepad that:
#   - reads every conversation
#   - writes down only the important facts
#   - shows you the relevant ones when you ask a new question
# ================================================

import os
from mem0 import Memory
from src.config import OLLAMA_URL, MODEL_NAME, EMBED_MODEL

# Persist memories to disk so they survive server restarts
os.makedirs("logs/mem0_qdrant", exist_ok=True)

# ── mem0 configuration ────────────────────────────────────────────────────────
# We configure mem0 to use our local Ollama models — no OpenAI key needed.
# LLM:      qwen2.5:7b  — extracts facts from conversations
# Embedder: nomic-embed-text — stores memories as vectors for semantic search
# Storage:  Qdrant on disk at logs/mem0_qdrant

_config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model":            MODEL_NAME,
            "ollama_base_url":  OLLAMA_URL,
            "temperature":      0,
            "max_tokens":       500
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model":           EMBED_MODEL,
            "ollama_base_url": OLLAMA_URL
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name":      "policyguard_memories",
            "path":                 "logs/mem0_qdrant",
            "on_disk":              True,
            "embedding_model_dims": 768   # nomic-embed-text output size
        }
    }
}

# Single shared Memory instance (lazy-loaded)
_memory = None

def _get_memory() -> Memory:
    global _memory
    if _memory is None:
        print("Initializing mem0 memory store...")
        _memory = Memory.from_config(_config)
        print("✅ mem0 ready")
    return _memory


# ── Public interface ──────────────────────────────────────────────────────────

def save_memory(user_id: str, question: str, answer: str) -> None:
    """
    Save a Q&A exchange to long-term memory for this user.

    mem0 will:
    1. Read the question + answer
    2. Use the LLM to extract key facts ("user is a contractor",
       "asked about FMLA 12-week entitlement", "policy cited: Section 2.0")
    3. Store those facts as embeddings

    Call this AFTER every successful answer in pipeline.py.
    """
    try:
        mem = _get_memory()
        messages = [
            {"role": "user",      "content": question},
            {"role": "assistant", "content": answer}
        ]
        mem.add(messages, user_id=user_id)
        print(f"  [mem0] memory saved for user={user_id}")
    except Exception as e:
        # Memory failure should never break the main pipeline
        print(f"  [mem0] warning — could not save memory: {e}")


def get_memories(user_id: str, question: str, limit: int = 3) -> str:
    """
    Retrieve the most relevant past memories for this user + question.

    Returns a formatted string ready to inject into the LangGraph session context.
    If no memories exist yet, returns an empty string.

    Example output:
        RELEVANT PAST CONTEXT:
        - User previously asked about FMLA 12-week entitlement (Section 2.0)
        - User identified as a contractor employee type
    """
    try:
        mem = _get_memory()
        results = mem.search(query=question, filters={"user_id": user_id}, limit=limit)

        # mem0 returns list of dicts with 'memory' key
        memories = []
        if isinstance(results, dict):
            memories = results.get("results", [])
        elif isinstance(results, list):
            memories = results

        if not memories:
            return ""

        lines = [m.get("memory", "") for m in memories if m.get("memory")]
        if not lines:
            return ""

        formatted = "RELEVANT PAST CONTEXT (from previous sessions):\n"
        formatted += "\n".join(f"- {line}" for line in lines)
        return formatted

    except Exception as e:
        print(f"  [mem0] warning — could not retrieve memories: {e}")
        return ""


def clear_memories(user_id: str) -> None:
    """Clear all memories for a user (useful for testing)."""
    try:
        mem = _get_memory()
        mem.delete_all(filters={"user_id": user_id})
        print(f"  [mem0] cleared all memories for user={user_id}")
    except Exception as e:
        print(f"  [mem0] warning — could not clear memories: {e}")
