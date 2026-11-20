# ================================================
# Phase 5 — RAGAS-inspired Evaluation Pipeline
#
# WHAT THIS MEASURES (same 3 metrics as official RAGAS):
#   - Faithfulness:       answer grounded in retrieved chunks? (0–1)
#   - Context Precision:  retrieved chunks relevant to question? (0–1)
#   - Context Recall:     retrieved chunks cover the ground truth? (0–1)
#
# HOW IT WORKS:
#   Direct Ollama prompts for each metric — same logic as official RAGAS
#   but without the instructor/structured-output layer that qwen2.5:7b
#   fails on (IncompleteOutputException). In production, swap to RAGAS
#   Collections with gpt-4o-mini/claude-haiku for 100% score coverage.
#
# PRODUCTION UPGRADE (one line in _score_one):
#   client = OpenAI(api_key="your-key")  # real OpenAI
#   model  = "gpt-4o-mini"               # handles complex schemas
# ================================================

import re
import json
import math
import requests
import pandas as pd

from src.config import OLLAMA_URL, MODEL_NAME, EMBED_MODEL


# ── Test dataset ──────────────────────────────────────────────────────────────
# 5 ground-truth Q&A pairs from the loaded policy documents.
# ground_truth = what the correct answer MUST include.

TEST_DATASET = [
    {
        "question": "How many weeks of FMLA leave are employees entitled to?",
        "ground_truth": (
            "Eligible employees are entitled to up to 12 weeks of "
            "unpaid, job-protected leave per year under FMLA."
        )
    },
    {
        "question": "What are the eligibility requirements for FMLA leave?",
        "ground_truth": (
            "Employees must have worked for the employer for at least 12 months "
            "and 1,250 hours in the past year. The employer must have 50 or more "
            "employees within 75 miles."
        )
    },
    {
        "question": "Can contractors take FMLA leave?",
        "ground_truth": (
            "No. Contractors are not eligible for FMLA leave. "
            "Only employees meeting tenure and hour requirements qualify."
        )
    },
    {
        "question": "What happens to accrued sick leave when FMLA is taken?",
        "ground_truth": (
            "Accrued sick time runs concurrently with FMLA leave, "
            "meaning it is exhausted alongside the FMLA period."
        )
    },
    {
        "question": "How much advance notice must an employee give before taking FMLA leave?",
        "ground_truth": (
            "Employees must provide 30 days advance notice when the leave "
            "is foreseeable."
        )
    },
]


# ── Core Ollama scorer ────────────────────────────────────────────────────────

def _score_one(prompt: str, label: str) -> float:
    """
    Call Ollama with a scoring prompt. Returns a float 0.0–1.0.

    WHY NO format="json":
    Ollama's format="json" returns empty string when the model can't comply.
    We ask for JSON in the prompt text and extract the score with regex as
    a fallback — much more robust with local 7B models.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "think":  False,
                "options": {"temperature": 0, "num_predict": 512}
            },
            timeout=120
        )
        raw = resp.json().get("response", "").strip()

        # Try JSON parse first
        try:
            # Find the first {...} block
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start != -1 and end > start:
                data  = json.loads(raw[start:end])
                score = float(data.get("score", -1))
                if 0.0 <= score <= 1.0:
                    return score
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Regex fallback: find "score": 0.xx or score 0.xx
        match = re.search(r'"?score"?\s*[:\s]+([01](?:\.\d+)?)', raw, re.I)
        if match:
            return float(match.group(1))

        print(f"    [{label}] could not parse score from: {raw[:120]}")
        return float("nan")

    except Exception as e:
        print(f"    [{label}] request error: {e}")
        return float("nan")


# ── Three metric scorers ──────────────────────────────────────────────────────

def _score_faithfulness(r: dict, i: int) -> float:
    """
    Faithfulness: fraction of answer claims supported by retrieved contexts.
    Same logic as RAGAS Faithfulness.
    """
    ctx = "\n---\n".join(c[:400] for c in r["contexts"])
    prompt = f"""You are an evaluator. Check if the answer is faithful to the contexts.

Question: {r['question']}
Answer: {r['answer']}
Contexts:
{ctx}

Instructions:
1. Identify the key factual claims in the answer.
2. Check if each claim is directly supported by the contexts.
3. Score = supported_claims / total_claims

Reply with ONLY this JSON (no explanation):
{{"score": 0.9}}

Where score is a decimal from 0.0 (nothing supported) to 1.0 (all supported)."""

    score = _score_one(prompt, f"faith Q{i+1}")
    print(f"    Q{i+1}: {score:.3f}" if not math.isnan(score) else f"    Q{i+1}: nan")
    return score


def _score_context_precision(r: dict, i: int) -> float:
    """
    Context Precision: fraction of retrieved chunks relevant to the question.
    Same logic as RAGAS ContextPrecisionWithReference.
    """
    ctx_list = "\n".join(
        f"[Chunk {j+1}]: {c[:300]}" for j, c in enumerate(r["contexts"])
    )
    prompt = f"""You are an evaluator. Check if the retrieved chunks are relevant to the question.

Question: {r['question']}
Reference answer: {r['ground_truth']}

Retrieved chunks:
{ctx_list}

Instructions:
Count how many chunks contain information useful for answering the question.
Score = relevant_chunks / total_chunks

Reply with ONLY this JSON (no explanation):
{{"score": 0.8}}

Where score is a decimal from 0.0 to 1.0."""

    score = _score_one(prompt, f"prec Q{i+1}")
    print(f"    Q{i+1}: {score:.3f}" if not math.isnan(score) else f"    Q{i+1}: nan")
    return score


def _score_context_recall(r: dict, i: int) -> float:
    """
    Context Recall: how much of the ground truth is covered by retrieved chunks.
    Same logic as RAGAS ContextRecall.
    """
    ctx = "\n---\n".join(c[:400] for c in r["contexts"])
    prompt = f"""You are an evaluator. Check how much of the reference answer is covered by the retrieved contexts.

Question: {r['question']}
Reference answer: {r['ground_truth']}
Retrieved contexts:
{ctx}

Instructions:
1. Break the reference answer into key facts/sentences.
2. Check if each fact is present in the retrieved contexts.
3. Score = facts_covered / total_facts

Reply with ONLY this JSON (no explanation):
{{"score": 0.75}}

Where score is a decimal from 0.0 (nothing covered) to 1.0 (fully covered)."""

    score = _score_one(prompt, f"recall Q{i+1}")
    print(f"    Q{i+1}: {score:.3f}" if not math.isnan(score) else f"    Q{i+1}: nan")
    return score


# ── Step 1: Run pipeline ───────────────────────────────────────────────────────

def run_pipeline_on_dataset(pipeline, dataset=None) -> list:
    """Run each test question through the full PolicyGuard pipeline."""
    if dataset is None:
        dataset = TEST_DATASET

    results = []
    for i, item in enumerate(dataset):
        q = item["question"]
        print(f"  [ragas] Q{i+1}/{len(dataset)}: {q[:65]}...")
        try:
            result  = pipeline.ask(q, user="ragas_eval")
            contexts = [
                c["text"] for c in result.get("retrieved_chunks", []) if c.get("text")
            ]
            if not contexts:
                contexts = ["No context retrieved."]
            answer = result.get("answer") or result.get("clarification_question") or "No answer provided."
            answer = answer.strip() if isinstance(answer, str) else "No answer provided."
            results.append({
                "question":     q,
                "answer":       answer,
                "contexts":     contexts,
                "ground_truth": item["ground_truth"],
            })
            print(f"    decision={result.get('decision')}  "
                  f"confidence={result.get('confidence')}  "
                  f"chunks={len(contexts)}")
        except Exception as e:
            print(f"  [ragas] pipeline error on Q{i+1}: {e}")
            results.append({
                "question":     q,
                "answer":       "ERROR",
                "contexts":     ["No context retrieved."],
                "ground_truth": item["ground_truth"],
            })
    return results


# ── Step 2: Score ─────────────────────────────────────────────────────────────

def evaluate_with_ragas(pipeline_results: list):
    """
    Score pipeline results with 3 RAGAS-equivalent metrics via direct Ollama.

    WHY DIRECT OLLAMA (not RAGAS Collections API):
    RAGAS 0.4.4 + instructor + qwen2.5:7b raises IncompleteOutputException
    for Faithfulness (complex nested schema) and intermittently for Recall
    (schema too long for a 7B model to complete reliably).
    Direct prompting is more reliable for local models.

    PRODUCTION UPGRADE:
    Replace _score_one() with RAGAS Collections + gpt-4o-mini/claude-haiku
    for academically rigorous NLI-based scoring.
    """
    print("  [ragas] scoring faithfulness (5 samples)...")
    faith_scores = [_score_faithfulness(r, i) for i, r in enumerate(pipeline_results)]

    print("  [ragas] scoring context_precision (5 samples)...")
    prec_scores  = [_score_context_precision(r, i) for i, r in enumerate(pipeline_results)]

    print("  [ragas] scoring context_recall (5 samples)...")
    recall_scores = [_score_context_recall(r, i) for i, r in enumerate(pipeline_results)]

    df = pd.DataFrame({
        "faithfulness":                     faith_scores,
        "context_precision_with_reference": prec_scores,
        "context_recall":                   recall_scores,
    })

    class _Result:
        def to_pandas(self):
            return df

    return _Result()


# ── Step 3: Print report ──────────────────────────────────────────────────────

def print_report(result) -> None:
    df = result.to_pandas()

    col_faith  = next((c for c in df.columns if "faith"  in c.lower()), None)
    col_prec   = next((c for c in df.columns if "precis" in c.lower()), None)
    col_recall = next((c for c in df.columns if "recall" in c.lower()), None)

    def _mean(col):
        if col is None: return float("nan")
        vals = [v for v in df[col] if v is not None and not math.isnan(float(v))]
        return sum(vals) / len(vals) if vals else float("nan")

    faith  = _mean(col_faith)
    prec   = _mean(col_prec)
    recall = _mean(col_recall)
    scores = [s for s in [faith, prec, recall] if not math.isnan(s)]
    avg    = sum(scores) / len(scores) if scores else float("nan")

    print("\n" + "=" * 56)
    print("  RAGAS EVALUATION REPORT — PolicyGuard")
    print("=" * 56)
    print(f"  Faithfulness      : {faith:.3f}   (hallucination check)")
    print(f"  Context Precision : {prec:.3f}   (retrieval quality)")
    print(f"  Context Recall    : {recall:.3f}   (retrieval completeness)")
    print("-" * 56)
    print(f"  Overall Average   : {avg:.3f}")
    print("=" * 56)

    if avg >= 0.8:
        verdict = "PASS — production ready"
    elif avg >= 0.6:
        verdict = "MARGINAL — improve before production"
    else:
        verdict = "FAIL — significant issues found"
    print(f"  Verdict: {verdict}")
    print("=" * 56)

    print("\n  Per-question scores:")
    print(f"  {'Q':<4} {'Faith':>6} {'Prec':>6} {'Recall':>7}")
    print("  " + "-" * 30)
    for i, row in df.iterrows():
        f = row[col_faith]  if col_faith  else float("nan")
        p = row[col_prec]   if col_prec   else float("nan")
        r = row[col_recall] if col_recall else float("nan")
        print(f"  Q{i+1:<3} {f:>6.3f} {p:>6.3f} {r:>7.3f}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def run_evaluation(pipeline) -> None:
    """Full evaluation: run pipeline → score → report."""
    print(f"\n🧪 RAGAS Evaluation — PolicyGuard")
    print(f"   Model: {MODEL_NAME}  |  Questions: {len(TEST_DATASET)}")
    print("=" * 56)

    print("\nStep 1 — Running pipeline on test questions...")
    pipeline_results = run_pipeline_on_dataset(pipeline)

    print("\nStep 2 — Scoring with 3 RAGAS-equivalent metrics...")
    scores = evaluate_with_ragas(pipeline_results)

    print("\nStep 3 — Report")
    print_report(scores)
