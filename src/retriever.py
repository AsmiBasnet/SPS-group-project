# ================================================
# ChromaDB Retriever
# Replaces FAISS — index persists across restarts
# Same API as before so pipeline.py needs no changes
# ================================================

import chromadb
import numpy as np
import requests
import os
from src.config import OLLAMA_URL, EMBED_MODEL, TOP_K_CHUNKS

CHROMA_PATH = "logs/chroma_db"


def get_embedding(text):
    """Get embedding vector from Ollama nomic-embed-text."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        return response.json()["embedding"]
    except Exception as e:
        raise Exception(f"Embedding failed: {e}")


def _get_collection():
    """Get or create the persistent ChromaDB collection."""
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name="policyguard",
        metadata={"hnsw:space": "cosine"}
    )


def build_index(chunks):
    """
    Build ChromaDB collection from document chunks.
    Upserts so re-uploading the same doc doesn't duplicate.
    Returns (collection, chunks) — same shape as old FAISS API.
    """
    print(f"\nBuilding knowledge base from {len(chunks)} chunks...")
    collection = _get_collection()

    embeddings = []
    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk["text"])
        embeddings.append(emb)
        documents.append(chunk["text"])
        metadatas.append({
            "page":        chunk["page"],
            "source":      chunk["source"],
            "source_path": chunk["source_path"],
            "chunk_id":    chunk["chunk_id"]
        })
        ids.append(chunk["chunk_id"])

        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Embedded {i+1}/{len(chunks)} chunks...")

    # Upsert — safe to call multiple times
    collection.upsert(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✅ Knowledge base ready — {len(chunks)} chunks indexed")
    return collection, chunks


def save_index(collection, chunks, path=None):
    """No-op — ChromaDB auto-persists to disk."""
    print(f"✅ Index auto-saved by ChromaDB ({len(chunks)} chunks)")


def load_index(path=None):
    """
    Load existing ChromaDB collection from disk.
    Returns (collection, chunks) or (None, []) if empty.
    """
    try:
        collection = _get_collection()
        count = collection.count()

        if count == 0:
            return None, []

        # Retrieve all stored chunks
        result = collection.get(include=["documents", "metadatas"])
        chunks = []
        for doc, meta in zip(result["documents"], result["metadatas"]):
            chunks.append({
                "text":        doc,
                "page":        meta.get("page", 0),
                "source":      meta.get("source", ""),
                "source_path": meta.get("source_path", ""),
                "chunk_id":    meta.get("chunk_id", "")
            })

        print(f"✅ Index loaded — {len(chunks)} chunks")
        return collection, chunks

    except Exception as e:
        print(f"⚠️ Could not load index: {e}")
        return None, []


def search(query, collection, chunks, top_k=TOP_K_CHUNKS):
    """
    Search ChromaDB for relevant chunks.
    Returns list of chunks with similarity scores.
    ChromaDB returns cosine distance → convert to similarity (1 - distance).
    """
    qemb = get_embedding(query)

    results = collection.query(
        query_embeddings=[qemb],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        # cosine distance → similarity: 1 - distance
        score = max(0.0, 1.0 - dist)
        output.append({
            "text":     doc,
            "page":     meta.get("page", 0),
            "source":   meta.get("source", ""),
            "chunk_id": meta.get("chunk_id", ""),
            "score":    round(score, 4)
        })

    # Sort by score descending
    output.sort(key=lambda x: x["score"], reverse=True)
    return output
