# ================================================
# Proactive Conflict Scanner
# Phase D — runs automatically after every upload
#
# Strategy (CPU-friendly):
#   1. Sample up to MAX_SAMPLE_CHUNKS representative chunks
#      from the newly added document
#   2. For each sampled chunk, search ChromaDB for semantically
#      similar chunks from DIFFERENT documents
#   3. If similarity ≥ CONFLICT_THRESHOLD, call LLM with a
#      minimal conflict-check prompt
#   4. Return structured results immediately — no manual query needed
# ================================================

import requests
import json
from src.retriever import get_embedding, _get_collection
from src.config import OLLAMA_URL, MODEL_NAME, TEMPERATURE

# How many new chunks to spot-check (keeps scan fast on CPU)
MAX_SAMPLE_CHUNKS = 5

# Minimum semantic similarity to warrant an LLM conflict check
CONFLICT_THRESHOLD = 0.72

# Max tokens for the tiny conflict-check prompt
CONFLICT_MAX_TOKENS = 80


def _conflict_prompt(text_a, text_b):
    """Build a minimal conflict-check prompt."""
    # Truncate each clause to ~120 chars to stay within context
    a = text_a[:120].replace("\n", " ").strip()
    b = text_b[:120].replace("\n", " ").strip()
    return (
        f'Do these two HR policy clauses contradict each other? '
        f'JSON only.\n'
        f'A: "{a}"\n'
        f'B: "{b}"\n'
        f'{{"conflict":true/false,"reason":"under 10 words"}}'
    )


def _ask_llm_conflict(text_a, text_b):
    """
    Ask the local LLM whether two clauses contradict.
    Returns (conflict: bool, reason: str).
    """
    prompt = _conflict_prompt(text_a, text_b)
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "think":  False,
                "options": {
                    "temperature": TEMPERATURE,
                    "num_predict": CONFLICT_MAX_TOKENS,
                    "num_ctx":     512,
                    "stop":        ["```", "\n\n"]
                }
            },
            timeout=120
        )
        raw = response.json().get("response", "").strip()

        # Extract JSON
        start = raw.find("{")
        end   = raw.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(raw[start:end + 1])
            conflict = bool(data.get("conflict", False))
            reason   = str(data.get("reason", ""))
            return conflict, reason

    except Exception as e:
        print(f"⚠️ Conflict LLM call failed: {e}")

    return False, "scan error"


def scan_for_conflicts(new_chunks, new_doc_name, existing_chunks):
    """
    Scan a newly uploaded document against the existing knowledge base.

    Args:
        new_chunks    : list of chunk dicts for the new document only
        new_doc_name  : filename string (used to exclude self-matches)
        existing_chunks: ALL chunks currently in the pipeline (incl. new ones)

    Returns:
        list of dicts:
            new_text      str   clause from the new document
            new_source    str   filename of new doc
            new_page      int
            existing_text str   conflicting clause from existing doc
            existing_src  str   filename of existing doc
            existing_page int
            similarity    float
            reason        str   LLM explanation
    """
    if not new_chunks or not existing_chunks:
        return []

    # Sample evenly across the new document
    step     = max(1, len(new_chunks) // MAX_SAMPLE_CHUNKS)
    sampled  = new_chunks[::step][:MAX_SAMPLE_CHUNKS]

    collection = _get_collection()
    if collection.count() == 0:
        return []

    conflicts_found = []
    seen_pairs      = set()   # avoid duplicate pair reports

    for chunk in sampled:
        try:
            emb = get_embedding(chunk["text"])
        except Exception:
            continue

        # Query ChromaDB — fetch more than we need so we can filter by source
        n_results = min(6, collection.count())
        results   = collection.query(
            query_embeddings=[emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            src = meta.get("source", "")

            # Only cross-document comparisons
            if src == new_doc_name:
                continue

            similarity = max(0.0, 1.0 - dist)
            if similarity < CONFLICT_THRESHOLD:
                continue

            # Deduplicate pairs
            pair_key = (chunk["chunk_id"], meta.get("chunk_id", doc[:30]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # LLM conflict check
            conflict, reason = _ask_llm_conflict(chunk["text"], doc)

            if conflict:
                conflicts_found.append({
                    "new_text":      chunk["text"],
                    "new_source":    new_doc_name,
                    "new_page":      chunk.get("page", "?"),
                    "existing_text": doc,
                    "existing_src":  src,
                    "existing_page": meta.get("page", "?"),
                    "similarity":    round(similarity, 3),
                    "reason":        reason
                })

    return conflicts_found
