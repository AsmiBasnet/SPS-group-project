# ================================================
# FAISS Retriever
# Embeds chunks and searches for relevant content
# ================================================

import faiss
import numpy as np
import requests
import pickle
import os
from src.config import OLLAMA_URL, EMBED_MODEL, TOP_K_CHUNKS

def get_embedding(text):
    """Get embedding vector from Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        return response.json()["embedding"]
    except Exception as e:
        raise Exception(f"Embedding failed: {e}")

def build_index(chunks):
    """
    Build FAISS index from document chunks.
    Returns index and embeddings.
    """
    print(f"\nBuilding knowledge base from {len(chunks)} chunks...")
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk["text"])
        embeddings.append(emb)
        
        # Progress update every 10 chunks
        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Embedded {i+1}/{len(chunks)} chunks...")
    
    # Build FAISS index
    matrix = np.array(embeddings).astype("float32")
    faiss.normalize_L2(matrix)
    
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    
    print(f"✅ Knowledge base ready — {len(chunks)} chunks indexed")
    return index, embeddings

def save_index(index, chunks, path="logs/faiss_index"):
    """Save FAISS index to disk for persistence"""
    os.makedirs(path, exist_ok=True)
    faiss.write_index(index, f"{path}/index.faiss")
    with open(f"{path}/chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)
    print(f"✅ Index saved to {path}")

def load_index(path="logs/faiss_index"):
    """Load FAISS index from disk"""
    if not os.path.exists(f"{path}/index.faiss"):
        return None, None
    
    index = faiss.read_index(f"{path}/index.faiss")
    with open(f"{path}/chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    
    print(f"✅ Index loaded — {len(chunks)} chunks")
    return index, chunks

def search(query, index, chunks, top_k=TOP_K_CHUNKS):
    """
    Search FAISS index for relevant chunks.
    Returns list of chunks with similarity scores.
    """
    # Embed query
    qemb = np.array([get_embedding(query)]).astype("float32")
    faiss.normalize_L2(qemb)
    
    # Search
    scores, indices = index.search(qemb, top_k)
    
    # Build results
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            results.append({
                "text": chunks[idx]["text"],
                "page": chunks[idx]["page"],
                "source": chunks[idx]["source"],
                "chunk_id": chunks[idx]["chunk_id"],
                "score": float(score)
            })
    
    return results