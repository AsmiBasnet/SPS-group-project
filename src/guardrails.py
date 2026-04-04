# ================================================
# Guardrails
# Safety checks before and after LLM call
# ================================================

from src.config import SIMILARITY_THRESHOLD

def check_evidence_strength(retrieved_chunks):
    """
    Stage 1 — Retrieval similarity check
    Refuses if all chunks score below threshold
    """
    if not retrieved_chunks:
        return False, "No relevant content found"
    
    top_score = retrieved_chunks[0]["score"]
    
    if top_score < SIMILARITY_THRESHOLD:
        return False, (
            f"Evidence too weak — "
            f"best match score: {top_score:.3f} "
            f"(minimum required: {SIMILARITY_THRESHOLD})"
        )
    
    return True, "Evidence sufficient"

def check_citation_present(result):
    """
    Stage 2 — Output validation check
    Ensures every ANSWER has a citation
    """
    citation = result.get("citation", "")
    
    if not citation:
        return False
    if citation in ["N/A", "None", "null", ""]:
        return False
    if len(citation.strip()) < 3:
        return False
    
    return True

def get_confidence_level(top_score):
    """
    Returns confidence level based on similarity score
    HIGH: above 0.80
    MEDIUM: 0.70 to 0.80
    LOW: 0.65 to 0.70
    """
    if top_score >= 0.80:
        return "HIGH"
    elif top_score >= 0.70:
        return "MEDIUM"
    else:
        return "LOW"

def get_conflict_severity(result, retrieved_chunks):
    """
    Three-level conflict severity scoring
    RED: Direct contradiction between clauses
    YELLOW: Conditional difference — context dependent
    GREEN: Consistent — clauses agree
    """
    decision = result.get("decision", "")
    
    if decision != "FLAG_CONFLICT":
        return "GREEN", "Clauses are consistent"
    
    reasoning = result.get("reasoning", "").lower()
    
    # Check for direct contradiction keywords
    red_keywords = [
        "contradict", "conflict", "opposite",
        "inconsistent", "disagree", "cannot both"
    ]
    yellow_keywords = [
        "depends", "conditional", "subject to",
        "may vary", "case by case", "unclear"
    ]
    
    for keyword in red_keywords:
        if keyword in reasoning:
            return "RED", "Direct policy contradiction detected"
    
    for keyword in yellow_keywords:
        if keyword in reasoning:
            return "YELLOW", "Policy has conditional requirements"
    
    return "RED", "Policy conflict detected"