# ================================================
# LLM Reasoning Node — Chain of Thought edition
#
# Improvements over v1:
#   1. Chain of Thought prompt — model reasons step-by-step
#      before committing to a decision
#   2. Self-verification — model checks its own answer
#      against the context before returning ANSWER
#   3. Detailed reasoning field — 2-3 sentences explaining
#      WHY the decision was made (shown in Logic Trace)
#   4. Better out-of-context explanation — REFUSED tells
#      the user exactly why it can't answer
# ================================================

import requests
import json
from src.config import (
    OLLAMA_URL, MODEL_NAME,
    MAX_TOKENS, CONTEXT_SIZE, TEMPERATURE
)


def _build_context(retrieved_chunks):
    """Format retrieved chunks with section + page metadata."""
    parts = []
    for chunk in retrieved_chunks:
        section = chunk.get("section", "")
        label   = f"Section: {section} | " if section else ""
        parts.append(
            f"[{label}Source: {chunk['source']} | Page {chunk['page']}]\n"
            f"{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def reason(question, retrieved_chunks, session_context=""):
    """
    Chain of Thought reasoning node.

    The prompt instructs the model to:
      Step 1 — Identify what the employee is asking
      Step 2 — Find the most relevant policy clause
      Step 3 — Check for contradictions between clauses
      Step 4 — Verify the answer comes from context (not imagination)
      Step 5 — Return structured JSON

    Returns structured JSON:
      decision: ANSWER | CLARIFY | FLAG_CONFLICT
      answer:   clear 1-2 sentence response
      reasoning: 2-3 sentences explaining the decision logic
      citation:  exact section/page reference
    """
    context    = _build_context(retrieved_chunks)
    session_str = (
        f"Previous context: {session_context}\n" if session_context else ""
    )

    prompt = f"""You are an HR policy compliance assistant. Think step by step.

{session_str}EMPLOYEE QUESTION: {question}

POLICY CONTEXT:
{context}

Follow these steps before answering:
1. What exactly is the employee asking about?
2. Which clause in the context directly addresses this?
3. Do any clauses contradict each other on this topic?
4. Is there clear enough evidence in the context to answer? (yes/no)

Rules:
- Use ONLY information from the context above — never invent facts
- If evidence is unclear or missing → CLARIFY
- If two clauses contradict → FLAG_CONFLICT
- If clear evidence exists → ANSWER

Respond ONLY with this JSON (no extra text):
{{"decision":"ANSWER|CLARIFY|FLAG_CONFLICT","answer":"Clear 1-2 sentence answer for the employee","reasoning":"2-3 sentences explaining which clause you used and why you are confident","citation":"Section name or Page number from context","clarification_question":"Ask only if decision is CLARIFY","conflict_clause_a":"Exact quote if FLAG_CONFLICT","conflict_clause_b":"Exact quote if FLAG_CONFLICT"}}"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model":  MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "think":  False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": 250,       # slightly more for detailed reasoning
                "num_ctx":     1536,      # slightly larger context window
                "stop":        ["```", "\n\n\n"]
            }
        },
        timeout=300
    )

    raw = response.json().get("response", "").strip()

    # Extract JSON block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    elif start != -1:
        raw = raw[start:] + "}"

    try:
        result = json.loads(raw)

        # Self-verification: if model answered but reasoning is empty,
        # it likely hallucinated — downgrade to CLARIFY
        if result.get("decision") == "ANSWER":
            reasoning = result.get("reasoning", "").strip()
            citation  = result.get("citation", "").strip()
            if not reasoning or not citation or citation == "N/A":
                result["decision"] = "CLARIFY"
                result["clarification_question"] = (
                    "I found related information but could not verify "
                    "a specific clause. Could you rephrase your question "
                    "or provide more context?"
                )

        return result

    except json.JSONDecodeError:
        return {
            "decision":              "CLARIFY",
            "answer":                "I could not process the response. Please try again.",
            "citation":              "N/A",
            "reasoning":             "JSON parse error — model output was malformed.",
            "clarification_question":"Please rephrase your question.",
            "conflict_clause_a":     "",
            "conflict_clause_b":     ""
        }


def retry_reason(question, retrieved_chunks, session_context="", max_retries=2):
    """
    Reasoning with automatic retry on JSON / decision failure.
    """
    for attempt in range(max_retries):
        result = reason(question, retrieved_chunks, session_context)

        if result.get("decision") in ["ANSWER", "CLARIFY", "FLAG_CONFLICT"]:
            if attempt > 0:
                print(f"✅ Succeeded on attempt {attempt + 1}")
            return result

        print(f"⚠️ Attempt {attempt + 1} failed — retrying...")

    return {
        "decision":              "CLARIFY",
        "answer":                "Unable to generate a reliable response after multiple attempts.",
        "citation":              "N/A",
        "reasoning":             "Max retries exceeded — model output was consistently malformed.",
        "clarification_question":"Please rephrase your question more specifically.",
        "conflict_clause_a":     "",
        "conflict_clause_b":     ""
    }
