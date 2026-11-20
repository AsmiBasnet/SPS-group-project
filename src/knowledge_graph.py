# ================================================
# Phase 4 — GraphRAG: Knowledge Graph
#
# WHAT THIS ADDS:
#   Old: vector + BM25 retrieval → rerank → answer
#   New: vector + BM25 retrieval → graph expand → rerank → answer
#
# HOW IT WORKS:
#   1. BUILD: LLM reads each chunk and extracts triples:
#              (subject, relation, object)
#              e.g. ("FMLA", "requires", "12 months tenure")
#   2. STORE: triples become nodes + edges in a networkx DiGraph
#              each node knows which chunks mention it
#   3. EXPAND: at query time, find which graph nodes appear in
#              retrieved chunks, walk 1 hop, add those chunks
#
# MENTAL MODEL:
#   Vector search = librarian who knows similar-sounding sections
#   Graph expand  = librarian who knows "if you care about X,
#                   you probably also need to see Y and Z"
#
# EXAMPLE:
#   Query: "What is the FMLA leave policy?"
#   Vector finds: chunk about "12-week entitlement" (high score)
#   Graph shows:  "12 weeks" → connected to → "eligibility criteria"
#   Graph adds:   the eligibility section chunk automatically
# ================================================

import json
import pickle
import os
import requests
import networkx as nx

from src.config import OLLAMA_URL, MODEL_NAME

GRAPH_PATH = "logs/knowledge_graph.pkl"


# ── Triple extraction ─────────────────────────────────────────────────────────

def extract_triples(chunk_text: str, source: str) -> list:
    """
    Ask the LLM to extract (subject, relation, object) triples from one chunk.

    WHY TRIPLES:
    - A triple is the smallest unit of a knowledge graph
    - It captures ONE relationship between TWO entities
    - Many triples together = a graph of how concepts relate

    EXAMPLE TRIPLES FROM FMLA POLICY:
    - ("FMLA", "entitles", "12 weeks unpaid leave")
    - ("employee", "must have", "12 months tenure")
    - ("contractor", "not eligible for", "FMLA")
    - ("employer", "must have", "50+ employees")
    """
    prompt = f"""Extract key entities and relationships from this HR policy text.
Return a JSON array of triples. Each triple has exactly three keys: subject, relation, object.
Focus on: leave types, eligibility rules, durations, roles, sections, and exceptions.
Return ONLY valid JSON — no explanation, no markdown.

Example:
[
  {{"subject": "FMLA", "relation": "provides", "object": "12 weeks unpaid leave"}},
  {{"subject": "employee", "relation": "must have", "object": "12 months tenure"}},
  {{"subject": "contractor", "relation": "not eligible for", "object": "FMLA"}}
]

Policy text:
{chunk_text[:800]}

JSON:"""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "think":  False,
                "options": {"temperature": 0, "num_predict": 400}
            },
            timeout=60
        )
        raw = response.json().get("response", "").strip()
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        triples = json.loads(raw[start:end])
        return triples if isinstance(triples, list) else []
    except Exception as e:
        print(f"  [graph] extraction failed ({source}): {e}")
        return []


# ── Build graph ───────────────────────────────────────────────────────────────

def build_knowledge_graph(chunks: list) -> nx.DiGraph:
    """
    Build a directed knowledge graph from all policy chunks.

    NODES:  entities (lowercase strings like "fmla", "12 months tenure")
            each node carries a set of chunk indices that mention it

    EDGES:  directed relation from subject → object
            e.g. "employee" -[must have]-> "12 months tenure"
            each edge carries the chunk index it came from

    DIRECTED vs UNDIRECTED:
    - DiGraph lets us say "A causes B" (not just "A and B are related")
    - For HR policy, directionality matters:
      "employer must have 50+ employees" ≠ "50+ employees must have employer"
    """
    G = nx.DiGraph()
    total_triples = 0

    for i, chunk in enumerate(chunks):
        source = chunk.get("source", "unknown")
        print(f"  [graph] chunk {i+1}/{len(chunks)} from {source}...")

        triples = extract_triples(chunk["text"], source)

        for t in triples:
            subj = str(t.get("subject", "")).strip().lower()
            rel  = str(t.get("relation", "")).strip().lower()
            obj  = str(t.get("object",  "")).strip().lower()

            if not subj or not rel or not obj:
                continue

            # Add/update nodes — each node accumulates the set of chunk indices
            for entity in [subj, obj]:
                if not G.has_node(entity):
                    G.add_node(entity, chunk_indices=set())
                G.nodes[entity]["chunk_indices"].add(i)

            # Add directed edge
            G.add_edge(subj, obj, relation=rel, chunk_idx=i)
            total_triples += 1

    print(f"  [graph] ✅ {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges from {total_triples} triples")
    return G


# ── Persist ───────────────────────────────────────────────────────────────────

def save_graph(G: nx.DiGraph) -> None:
    os.makedirs("logs", exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)
    print(f"  [graph] saved → {GRAPH_PATH}")


def load_graph():
    if not os.path.exists(GRAPH_PATH):
        return None
    try:
        with open(GRAPH_PATH, "rb") as f:
            G = pickle.load(f)
        print(f"  [graph] loaded: {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges")
        return G
    except Exception as e:
        print(f"  [graph] could not load: {e}")
        return None


# ── Graph-expand retrieval ────────────────────────────────────────────────────

def graph_expand(
    retrieved_chunks: list,
    G,
    all_chunks: list,
    hops: int = 1
) -> list:
    """
    Expand the retrieved chunk pool by following edges in the knowledge graph.

    STEPS:
    1. Find chunk indices of the retrieved chunks (match by text)
    2. Find all graph nodes whose chunk_indices overlap with retrieved indices
       → these are the "seed nodes" (entities mentioned in retrieved text)
    3. Walk 1 hop: get all neighbors (both directions) of seed nodes
    4. Collect chunk indices from those neighbor nodes
    5. Add the new chunks to the pool (without duplicates)

    WHY BOTH DIRECTIONS:
    - Outgoing: "if chunk mentions FMLA, also look at what FMLA requires"
    - Incoming: "if chunk mentions 12-month rule, also look at who references it"

    RESULT:
    - The reranker now has a richer candidate pool
    - Multi-hop reasoning becomes possible without extra LLM calls
    """
    if G is None or not retrieved_chunks:
        return retrieved_chunks

    # Map retrieved chunks to their indices in all_chunks (by text match)
    retrieved_texts  = {c["text"] for c in retrieved_chunks}
    retrieved_idxs   = {
        i for i, c in enumerate(all_chunks)
        if c["text"] in retrieved_texts
    }

    # Seed nodes = graph nodes that touch retrieved chunks
    seed_nodes = set()
    for node, data in G.nodes(data=True):
        if data.get("chunk_indices", set()) & retrieved_idxs:
            seed_nodes.add(node)

    if not seed_nodes:
        return retrieved_chunks

    # 1-hop traversal (outgoing + incoming)
    neighbor_nodes = set()
    for node in seed_nodes:
        neighbor_nodes.update(G.neighbors(node))
        neighbor_nodes.update(G.predecessors(node))

    # Chunk indices from neighbors only (exclude seeds)
    expand_idxs = set()
    for node in neighbor_nodes - seed_nodes:
        expand_idxs.update(G.nodes[node].get("chunk_indices", set()))

    new_idxs = expand_idxs - retrieved_idxs
    if not new_idxs:
        return retrieved_chunks

    # Append new chunks, tagging them so we know they came from the graph
    expanded = list(retrieved_chunks)
    for idx in sorted(new_idxs):
        if idx < len(all_chunks):
            chunk = dict(all_chunks[idx])
            chunk["graph_expanded"] = True
            chunk.setdefault("score", 0.0)
            expanded.append(chunk)

    added = len(expanded) - len(retrieved_chunks)
    print(f"  [graph] expanded {len(retrieved_chunks)} → {len(expanded)} chunks "
          f"(+{added} via 1-hop traversal)")
    return expanded
