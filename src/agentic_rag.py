# ================================================
# Phase 1 — Agentic RAG with LangGraph
#
# WHAT THIS REPLACES:
#   Old: question → search() → retry_reason() → answer
#   New: question → retrieve → grade chunks →
#           if poor → rewrite question → retrieve again (max 2x)
#           if good → generate answer → grade answer →
#               if not grounded → regenerate (max 2x)
#               if grounded     → return answer
#
# KEY CONCEPTS:
#   StateGraph  — the graph that holds your whole pipeline
#   TypedDict   — the shared "memory" that flows between nodes
#   node        — one step (a plain Python function)
#   edge        — connection between nodes (can be conditional)
# ================================================

import requests
import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

from src.retriever import search
from src.reasoning import reason
from src.config import OLLAMA_URL, MODEL_NAME, SIMILARITY_THRESHOLD


# ── 1. STATE ──────────────────────────────────────────────────────────────────
# TypedDict = a dictionary with known keys and types.
# This state object is passed INTO every node and returned OUT of every node.
# Each node can read any field and update any field.
# Think of it as the "baton" being passed around the relay race.

class RAGState(TypedDict):
    question:        str           # original question from user
    rewritten:       str           # rewritten question (if retrieval was poor)
    chunks:          List[dict]    # retrieved policy chunks
    answer:          str           # final answer text
    decision:        str           # ANSWER | CLARIFY | FLAG_CONFLICT | REFUSED
    citation:        str           # which policy clause was cited
    reasoning:       str           # chain-of-thought reasoning
    clarification_question: str    # follow-up question if CLARIFY
    conflict_clause_a: str         # first conflicting clause if FLAG_CONFLICT
    conflict_clause_b: str         # second conflicting clause if FLAG_CONFLICT
    retrieval_attempts: int        # how many times we've tried retrieving
    generation_attempts: int       # how many times we've tried generating
    session_context: str           # conversation history from the session
    index:           object        # ChromaDB collection (passed in, never modified)


# ── 2. NODES ──────────────────────────────────────────────────────────────────
# Each node is a plain Python function that takes the full state and returns
# a dictionary of ONLY the fields it wants to update.
# LangGraph merges your returned dict back into the state automatically.


def retrieve_node(state: RAGState) -> dict:
    """
    NODE: retrieve
    Uses the rewritten question if available, otherwise the original.
    Calls the existing search() from retriever.py — no changes needed there.
    """
    query = state["rewritten"] if state["rewritten"] else state["question"]
    chunks = search(query, state["index"], [])  # ChromaDB doesn't need chunks list

    print(f"  [retrieve] query='{query[:60]}...' → {len(chunks)} chunks, "
          f"top score={chunks[0]['score'] if chunks else 0:.3f}")

    return {
        "chunks": chunks,
        "retrieval_attempts": state["retrieval_attempts"] + 1
    }


def grade_chunks_node(state: RAGState) -> dict:
    """
    NODE: grade_chunks
    Decides if the retrieved chunks are good enough to answer the question.
    Simple rule: if top chunk score > SIMILARITY_THRESHOLD → good.
    No LLM call needed here — keeps it fast.
    """
    chunks = state["chunks"]

    if not chunks:
        print("  [grade_chunks] no chunks found → poor")
        return {"decision": "poor_chunks"}

    top_score = chunks[0]["score"]

    if top_score >= SIMILARITY_THRESHOLD:
        print(f"  [grade_chunks] top score {top_score:.3f} ≥ {SIMILARITY_THRESHOLD} → good")
        return {"decision": "good_chunks"}
    else:
        print(f"  [grade_chunks] top score {top_score:.3f} < {SIMILARITY_THRESHOLD} → poor")
        return {"decision": "poor_chunks"}


def rewrite_question_node(state: RAGState) -> dict:
    """
    NODE: rewrite_question
    Asks the LLM to rephrase the question for better retrieval.
    This is the key upgrade over the old pipeline — if search fails,
    we don't give up. We ask the LLM: 'how should I search for this?'
    """
    prompt = f"""You are an HR policy search assistant.
The following question failed to retrieve relevant HR policy chunks.
Rewrite it to be more specific and use keywords likely found in HR policy documents.
Return ONLY the rewritten question, nothing else.

Original question: {state['question']}
Rewritten question:"""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "think":  False,
                "options": {"temperature": 0, "num_predict": 60}
            },
            timeout=60
        )
        rewritten = response.json().get("response", "").strip()
        print(f"  [rewrite] '{state['question'][:40]}' → '{rewritten[:60]}'")
        return {"rewritten": rewritten}
    except Exception as e:
        print(f"  [rewrite] failed: {e} — keeping original question")
        return {"rewritten": state["question"]}


def generate_node(state: RAGState) -> dict:
    """
    NODE: generate
    Calls the existing reason() from reasoning.py with retrieved chunks.
    Nothing changes in reasoning.py — LangGraph wraps around it.
    """
    result = reason(
        question=state["question"],
        retrieved_chunks=state["chunks"],
        session_context=state.get("session_context", "")
    )

    print(f"  [generate] decision={result.get('decision')} "
          f"attempt={state['generation_attempts'] + 1}")

    return {
        "answer":               result.get("answer", ""),
        "decision":             result.get("decision", "CLARIFY"),
        "citation":             result.get("citation", "N/A"),
        "reasoning":            result.get("reasoning", ""),
        "clarification_question": result.get("clarification_question", ""),
        "conflict_clause_a":    result.get("conflict_clause_a", ""),
        "conflict_clause_b":    result.get("conflict_clause_b", ""),
        "generation_attempts":  state["generation_attempts"] + 1
    }


def grade_answer_node(state: RAGState) -> dict:
    """
    NODE: grade_answer
    Checks if the generated answer is grounded in the retrieved chunks.
    Simple rule: ANSWER decision = grounded, anything else = not grounded.
    If the LLM returned CLARIFY it means it wasn't confident — try again.
    """
    if state["decision"] == "ANSWER":
        print("  [grade_answer] grounded ✅")
        return {"decision": "grounded"}
    elif state["decision"] in ["FLAG_CONFLICT", "CLARIFY"]:
        # FLAG_CONFLICT and CLARIFY are valid final decisions — don't retry
        print(f"  [grade_answer] valid decision: {state['decision']} → accept")
        return {"decision": "grounded"}
    else:
        print("  [grade_answer] not grounded — will retry generation")
        return {"decision": "not_grounded"}


# ── 3. ROUTING FUNCTIONS ───────────────────────────────────────────────────────
# These are the "decision makers" on conditional edges.
# They receive the current state and return a string key
# that tells LangGraph which node to go to next.


def route_after_grade_chunks(state: RAGState) -> str:
    """
    After grading chunks: go to generate if good, rewrite if poor.
    But if we've already retried twice, give up and generate anyway.
    """
    if state["decision"] == "good_chunks":
        return "generate"
    elif state["retrieval_attempts"] >= 2:
        # Tried twice — just generate with what we have
        print("  [route] max retrieval attempts reached → forcing generate")
        return "generate"
    else:
        return "rewrite_question"


def route_after_grade_answer(state: RAGState) -> str:
    """
    After grading answer: return if grounded, regenerate if not.
    But if we've already tried twice, return what we have.
    """
    if state["decision"] == "grounded":
        return END
    elif state["generation_attempts"] >= 2:
        print("  [route] max generation attempts reached → returning answer")
        return END
    else:
        return "generate"


# ── 4. BUILD THE GRAPH ────────────────────────────────────────────────────────
# This is where we wire all nodes and edges together.
# Think of this like drawing the flowchart — but in code.

def build_rag_graph():
    """
    Builds and compiles the LangGraph agentic RAG pipeline.
    Call this once at startup — returns a compiled app you can invoke.
    """
    # Create the graph with our state type
    graph = StateGraph(RAGState)

    # Add every node (name → function)
    graph.add_node("retrieve",        retrieve_node)
    graph.add_node("grade_chunks",    grade_chunks_node)
    graph.add_node("rewrite_question",rewrite_question_node)
    graph.add_node("generate",        generate_node)
    graph.add_node("grade_answer",    grade_answer_node)

    # Set the entry point — first node to run
    graph.set_entry_point("retrieve")

    # Fixed edges (always go from A to B)
    graph.add_edge("retrieve",         "grade_chunks")
    graph.add_edge("rewrite_question", "retrieve")
    graph.add_edge("generate",         "grade_answer")

    # Conditional edges (the router function decides which way to go)
    graph.add_conditional_edges(
        "grade_chunks",
        route_after_grade_chunks,
        {
            "generate":        "generate",
            "rewrite_question":"rewrite_question"
        }
    )

    graph.add_conditional_edges(
        "grade_answer",
        route_after_grade_answer,
        {
            END:       END,
            "generate":"generate"
        }
    )

    return graph.compile()


# ── 5. PUBLIC INTERFACE ───────────────────────────────────────────────────────
# This is the function pipeline.py will call instead of search() + retry_reason()
# Same inputs/outputs as before — drop-in replacement.

def agentic_ask(question: str, index, session_context: str = "") -> dict:
    """
    Main entry point for the agentic RAG pipeline.
    Replaces the search() + retry_reason() calls in pipeline.py.

    Args:
        question:        the user's HR policy question
        index:           ChromaDB collection from pipeline.py
        session_context: conversation history string

    Returns:
        dict with keys: decision, answer, citation, reasoning,
                        clarification_question, conflict_clause_a,
                        conflict_clause_b, retrieval_attempts, generation_attempts
    """
    app = build_rag_graph()

    # Initial state — every field must be present (TypedDict requirement)
    initial_state: RAGState = {
        "question":             question,
        "rewritten":            "",
        "chunks":               [],
        "answer":               "",
        "decision":             "",
        "citation":             "N/A",
        "reasoning":            "",
        "clarification_question": "",
        "conflict_clause_a":    "",
        "conflict_clause_b":    "",
        "retrieval_attempts":   0,
        "generation_attempts":  0,
        "session_context":      session_context,
        "index":                index
    }

    print(f"\n🤖 Agentic RAG — question: '{question[:60]}...'")
    final_state = app.invoke(initial_state)
    print(f"✅ Done — decision={final_state['decision']} "
          f"retrieval_attempts={final_state['retrieval_attempts']} "
          f"generation_attempts={final_state['generation_attempts']}")

    return {
        "decision":             final_state["decision"],
        "answer":               final_state["answer"],
        "citation":             final_state["citation"],
        "reasoning":            final_state["reasoning"],
        "clarification_question": final_state["clarification_question"],
        "conflict_clause_a":    final_state["conflict_clause_a"],
        "conflict_clause_b":    final_state["conflict_clause_b"],
        "retrieval_attempts":   final_state["retrieval_attempts"],
        "generation_attempts":  final_state["generation_attempts"],
        "chunks":               final_state["chunks"]
    }
