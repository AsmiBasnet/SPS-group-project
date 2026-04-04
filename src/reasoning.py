# ================================================
# LLM Reasoning Node
# The one agentic decision point in the pipeline
# ================================================

import requests
import json
from src.config import (
    OLLAMA_URL, MODEL_NAME,
    MAX_TOKENS, CONTEXT_SIZE, TEMPERATURE
)

def reason(question, retrieved_chunks, session_context=""):
    """
    Core reasoning node.
    
    Takes question + retrieved policy chunks.
    Returns structured JSON decision:
    ANSWER / CLARIFY / FLAG_CONFLICT
    """
    
    # Build context from retrieved chunks
    context_parts = []
    for chunk in retrieved_chunks:
        context_parts.append(
            f"[Source: {chunk['source']} | Page {chunk['page']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n".join(context_parts)
    
    # Build session context string
    session_str = ""
    if session_context:
        session_str = f"\nPrevious context: {session_context}\n"
    
    prompt = f"""You are PolicyGuard, an HR policy compliance agent.

STRICT RULES:
- Use ONLY the policy context provided below
- Never use outside knowledge or assumptions
- If context is insufficient say so
- Reply in JSON only — nothing else
- Keep answer and reasoning brief

{session_str}
User Question: {question}

Policy Context:
{context}

Decision Rules:
- ANSWER: You have clear policy evidence to answer
- CLARIFY: Critical information is missing (e.g. employee type, tenure, hours worked)
- FLAG_CONFLICT: Two or more clauses give contradicting guidance

Reply ONLY in this exact JSON:
{{
  "decision": "ANSWER or CLARIFY or FLAG_CONFLICT",
  "answer": "clear one or two sentence answer",
  "citation": "Section X.X or Policy Name Page X",
  "reasoning": "brief explanation under 20 words",
  "clarification_question": "only fill if CLARIFY decision",
  "conflict_clause_a": "only fill if FLAG_CONFLICT",
  "conflict_clause_b": "only fill if FLAG_CONFLICT"
}}"""

    # Call Ollama
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
                "num_ctx": CONTEXT_SIZE,
                "stop": ["```", "\n\n\n"]
            }
        },
        timeout=300
    )
    
    raw = response.json().get("response", "").strip()
    
    # Extract JSON cleanly
    start = raw.find("{")
    end = raw.rfind("}")
    
    if start != -1 and end != -1:
        raw = raw[start:end+1]
    elif start != -1:
        raw = raw[start:] + "}"
    
    # Parse JSON
    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        return {
            "decision": "ANSWER",
            "answer": "I was unable to parse the response. Please try again.",
            "citation": "N/A",
            "reasoning": "JSON parse error",
            "clarification_question": "",
            "conflict_clause_a": "",
            "conflict_clause_b": ""
        }

def retry_reason(question, retrieved_chunks, session_context="", max_retries=2):
    """
    Reasoning with automatic retry on JSON failure.
    Tries up to max_retries times before giving up.
    """
    for attempt in range(max_retries):
        result = reason(question, retrieved_chunks, session_context)
        
        # Check if valid decision
        if result.get("decision") in ["ANSWER", "CLARIFY", "FLAG_CONFLICT"]:
            if attempt > 0:
                print(f"✅ Succeeded on attempt {attempt + 1}")
            return result
        
        print(f"⚠️ Attempt {attempt + 1} failed — retrying...")
    
    # Final fallback
    return {
        "decision": "ANSWER",
        "answer": "Unable to generate reliable response. Please rephrase your question.",
        "citation": "N/A",
        "reasoning": "Max retries exceeded",
        "clarification_question": "",
        "conflict_clause_a": "",
        "conflict_clause_b": ""
    }