# ================================================
# PolicyGuard Evaluation Script
# Runs 50-question benchmark and reports metrics
# ================================================

import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    classification_report,
    confusion_matrix
)
import time
import json
from src.pipeline import PolicyGuardPipeline

def run_evaluation(benchmark_csv="eval/benchmark.csv"):
    """
    Run full 50-question evaluation.
    Saves results to eval/results.md
    """
    
    print("=" * 60)
    print("PolicyGuard — 50 Question Evaluation")
    print("=" * 60)
    
    # Load benchmark
    df = pd.read_csv(benchmark_csv)
    print(f"\nLoaded {len(df)} test questions")
    
    # Initialize pipeline
    pipeline = PolicyGuardPipeline()
    
    # Load all policy documents
    import os
    pdf_files = [
        f"data/{f}" for f in os.listdir("data")
        if f.endswith(".pdf")
    ]
    
    if not pdf_files:
        print("❌ No PDF files found in data/ folder")
        return
    
    print(f"\nLoading {len(pdf_files)} policy documents...")
    pipeline.load_multiple_documents(pdf_files)
    
    # Run evaluation
    results = []
    
    print("\nRunning evaluation questions...")
    print("-" * 60)
    
    for i, row in df.iterrows():
        question = row["question"]
        expected_decision = row["expected_decision"]
        expected_conflict = row.get("expected_conflict", False)
        
        print(f"Q{i+1}/{len(df)}: {question[:50]}...")
        
        start = time.time()
        result = pipeline.ask(
            question,
            row.get("employee_type", None),
            row.get("issue_category", None)
        )
        latency = time.time() - start
        
        # Check results
        decision_correct = (
            result["decision"] == expected_decision
        )
        citation_present = (
            result.get("citation", "N/A") != "N/A"
        )
        conflict_detected = (
            result["decision"] == "FLAG_CONFLICT"
        )
        
        results.append({
            "question": question,
            "expected_decision": expected_decision,
            "got_decision": result["decision"],
            "decision_correct": decision_correct,
            "expected_conflict": expected_conflict,
            "conflict_detected": conflict_detected,
            "citation": result.get("citation", "N/A"),
            "citation_present": citation_present,
            "latency": round(latency, 1),
            "confidence": result.get("confidence", "N/A"),
            "top_score": result.get("top_score", 0)
        })
        
        status = "✅" if decision_correct else "❌"
        print(f"  {status} Expected: {expected_decision} | Got: {result['decision']} | {latency:.1f}s")
    
    # Calculate metrics
    results_df = pd.DataFrame(results)
    
    # Overall accuracy
    accuracy = results_df["decision_correct"].mean()
    
    # Citation accuracy (for ANSWER decisions only)
    answer_rows = results_df[
        results_df["expected_decision"] == "ANSWER"
    ]
    citation_accuracy = (
        answer_rows["citation_present"].mean()
        if len(answer_rows) > 0 else 0
    )
    
    # Conflict detection metrics
    conflict_rows = results_df[
        results_df["expected_decision"] == "FLAG_CONFLICT"
    ]
    
    if len(conflict_rows) > 0:
        y_true = results_df["expected_conflict"].astype(int)
        y_pred = results_df["conflict_detected"].astype(int)
        
        conflict_precision = precision_score(
            y_true, y_pred, zero_division=0
        )
        conflict_recall = recall_score(
            y_true, y_pred, zero_division=0
        )
    else:
        conflict_precision = 0
        conflict_recall = 0
    
    # Latency stats
    avg_latency = results_df["latency"].mean()
    p95_latency = results_df["latency"].quantile(0.95)
    
    # Print results
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total Questions:      {len(results_df)}")
    print(f"Decision Accuracy:    {accuracy:.1%}")
    print(f"Citation Accuracy:    {citation_accuracy:.1%}  (target: ≥85%)")
    print(f"Conflict Precision:   {conflict_precision:.1%}  (target: ≥80%)")
    print(f"Conflict Recall:      {conflict_recall:.1%}  (target: ≥70%)")
    print(f"Average Latency:      {avg_latency:.1f}s")
    print(f"P95 Latency:          {p95_latency:.1f}s  (target: ≤30s)")
    
    # Save results
    save_results(results_df, {
        "accuracy": accuracy,
        "citation_accuracy": citation_accuracy,
        "conflict_precision": conflict_precision,
        "conflict_recall": conflict_recall,
        "avg_latency": avg_latency,
        "p95_latency": p95_latency
    })
    
    print("\n✅ Results saved to eval/results.md")
    return results_df

def save_results(results_df, metrics):
    """Save evaluation results to markdown file"""
    
    md = f"""# PolicyGuard Evaluation Results

## Summary Metrics

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| Citation Accuracy | {metrics['citation_accuracy']:.1%} | ≥85% | {'✅' if metrics['citation_accuracy'] >= 0.85 else '❌'} |
| P95 Latency | {metrics['p95_latency']:.1f}s | ≤30s | {'✅' if metrics['p95_latency'] <= 30 else '❌'} |
| Conflict Precision | {metrics['conflict_precision']:.1%} | ≥80% | {'✅' if metrics['conflict_precision'] >= 0.80 else '❌'} |
| Conflict Recall | {metrics['conflict_recall']:.1%} | ≥70% | {'✅' if metrics['conflict_recall'] >= 0.70 else '❌'} |
| Decision Accuracy | {metrics['accuracy']:.1%} | — | — |
| Avg Latency | {metrics['avg_latency']:.1f}s | — | — |

## Decision Breakdown

{results_df['got_decision'].value_counts().to_markdown()}

## Failed Cases

{results_df[~results_df['decision_correct']][['question','expected_decision','got_decision']].to_markdown()}
"""
    
    with open("eval/results.md", "w") as f:
        f.write(md)

if __name__ == "__main__":
    run_evaluation()