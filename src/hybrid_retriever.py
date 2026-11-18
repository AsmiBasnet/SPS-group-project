# ================================================
# Phase 2 — Hybrid Search + Cross-Encoder Reranking
#
# WHAT THIS REPLACES:
#   Old: vector search only (ChromaDB cosine similarity)
#   New: BM25 keyword search + vector search → fused → reranked
#
# THREE STEPS:
#   1. BM25   — exact keyword matching (finds "Section 4.2", "FMLA", "12 weeks")
#   2. Vector — semantic similarity (finds meaning, not just words)
#   3. Rerank — cross-encoder reads question + each chunk and scores them together
#
# WHY THIS MATTERS:
#   Vector search alone misses exact terms.
#   BM25 alone misses paraphrases.
#   Combined + reranked = best of both worlds.
#
# MENTAL MODEL:
#   BM25   = a librarian who searches by exact words in the index
#   Vector = a librarian who understands what you mean
#   Reranker = a senior expert who reads all candidates and picks the best
# ================================================

from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from src.retriever import search as vector_search
from src.config import TOP_K_CHUNKS

# ── Cross-encoder model ───────────────────────────────────────────────────────
# Downloaded once (~80MB), cached locally by sentence-transformers.
# This model reads the question AND a chunk together and scores their relevance.
# Much more accurate than comparing embeddings separately.
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        print("Loading cross-encoder reranker (first time only)...")
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("✅ Reranker loaded")
    return _reranker


# ── BM25 search ───────────────────────────────────────────────────────────────
def bm25_search(query: str, chunks: list, top_k: int = 10) -> list:
    """
    BM25 (Best Match 25) keyword search over all chunks.

    HOW BM25 WORKS:
    - Tokenises every chunk into words
    - Scores each chunk by how often query words appear,
      adjusted for chunk length (so long chunks don't always win)
    - Returns ranked list with BM25 scores

    WHY top_k=10 here:
    - We fetch more candidates than we need (10)
    - The reranker will cut them down to TOP_K_CHUNKS at the end
    """
    if not chunks:
        return []

    # Tokenise — split each chunk text into lowercase words
    tokenised_corpus = [chunk["text"].lower().split() for chunk in chunks]
    tokenised_query  = query.lower().split()

    bm25   = BM25Okapi(tokenised_corpus)
    scores = bm25.get_scores(tokenised_query)

    # Pair each chunk with its BM25 score, sort descending
    scored = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        {**chunk, "bm25_score": float(score)}
        for chunk, score in scored[:top_k]
        if score > 0  # skip chunks with zero keyword overlap
    ]


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────
def reciprocal_rank_fusion(
    vector_results: list,
    bm25_results:   list,
    k: int = 60
) -> list:
    """
    Merges two ranked lists into one using Reciprocal Rank Fusion (RRF).

    HOW RRF WORKS:
    - Each chunk gets a score of 1/(rank + k) from each list
    - A chunk ranked #1 in both lists scores highest
    - A chunk only in one list still gets credit

    WHY k=60:
    - Standard RRF constant that dampens the impact of very top ranks
    - Works well across most retrieval tasks

    EXAMPLE:
    - Chunk A: rank 1 in vector, rank 3 in BM25 → 1/61 + 1/63 = 0.0323
    - Chunk B: rank 1 in BM25 only              → 0 + 1/61    = 0.0164
    - Chunk A wins because it appeared in both lists
    """
    scores = {}

    for rank, chunk in enumerate(vector_results):
        cid = chunk.get("chunk_id", chunk["text"][:50])
        scores[cid] = scores.get(cid, {"chunk": chunk, "score": 0.0})
        scores[cid]["score"] += 1.0 / (rank + 1 + k)

    for rank, chunk in enumerate(bm25_results):
        cid = chunk.get("chunk_id", chunk["text"][:50])
        if cid not in scores:
            scores[cid] = {"chunk": chunk, "score": 0.0}
        scores[cid]["score"] += 1.0 / (rank + 1 + k)

    # Sort by fused score descending
    fused = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return [item["chunk"] for item in fused]


# ── Cross-encoder reranking ───────────────────────────────────────────────────
def rerank(query: str, chunks: list, top_k: int = TOP_K_CHUNKS) -> list:
    """
    Re-scores each chunk by reading question + chunk together.

    HOW THE CROSS-ENCODER WORKS:
    - Takes [question, chunk_text] as a pair
    - Runs them through a small BERT model that was trained to score relevance
    - Returns a relevance score for each pair
    - Much more accurate than cosine similarity because it sees both texts together

    WHY THIS IS THE FINAL STEP:
    - BM25 and vector search are fast but approximate
    - Cross-encoder is slower but much more accurate
    - We use fast search to get 10-20 candidates, then cross-encoder picks the best K
    """
    if not chunks:
        return []

    reranker = _get_reranker()

    # Build (question, chunk_text) pairs
    pairs  = [(query, chunk["text"]) for chunk in chunks]
    scores = reranker.predict(pairs)

    # Attach rerank score to each chunk and sort
    reranked = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    result = []
    for chunk, score in reranked[:top_k]:
        result.append({
            **chunk,
            "score":        float(score),   # rerank score replaces old cosine score
            "rerank_score": float(score)
        })

    return result


# ── Public interface ──────────────────────────────────────────────────────────
def hybrid_search(query: str, collection, chunks: list, top_k: int = TOP_K_CHUNKS) -> list:
    """
    Full hybrid search pipeline:
      1. Vector search  → top 10 candidates
      2. BM25 search    → top 10 candidates
      3. RRF fusion     → merged ranked list
      4. Cross-encoder  → final top_k results

    This replaces the plain search() call in agentic_rag.py.
    Same return shape as search() — list of dicts with text, page, source, score.
    """
    fetch_k = max(10, top_k * 3)

    # Step 1: Vector search
    vector_results = vector_search(query, collection, chunks, top_k=fetch_k)
    print(f"  [hybrid] vector={len(vector_results)} chunks")

    # Step 2: BM25 search (needs the raw chunks list)
    bm25_results = bm25_search(query, chunks, top_k=fetch_k)
    print(f"  [hybrid] bm25={len(bm25_results)} chunks")

    # Step 3: Fuse both lists
    fused = reciprocal_rank_fusion(vector_results, bm25_results)
    print(f"  [hybrid] fused={len(fused)} unique chunks")

    # Step 4: Rerank top candidates
    reranked = rerank(query, fused[:fetch_k], top_k=top_k)
    print(f"  [hybrid] reranked → top {len(reranked)} chunks, "
          f"best score={reranked[0]['score']:.3f}" if reranked else "  [hybrid] no results")

    return reranked
