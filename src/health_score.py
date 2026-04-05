# ================================================
# Policy Health Score
# Rates the organisation's policy library 0–100
#
# Three pillars:
#   Coverage    0–40 pts  ← gap detection
#   Freshness   0–30 pts  ← docs older than 1 yr = penalty
#   Consistency 0–30 pts  ← conflict count = penalty
# ================================================

import sqlite3
from datetime import datetime, timedelta
from src.config import DB_PATH
from src.gap_detector import detect_gaps


def _get_conflict_count():
    """Count FLAG_CONFLICT decisions logged in the DB."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM queries WHERE decision = 'FLAG_CONFLICT'"
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _get_stale_doc_info(active_docs):
    """
    Return (stale_count, stale_names) for docs uploaded > 365 days ago.
    """
    cutoff     = datetime.now() - timedelta(days=365)
    stale      = []
    for doc in active_docs:
        try:
            uploaded = datetime.fromisoformat(doc["uploaded"])
            if uploaded < cutoff:
                stale.append(doc["filename"])
        except Exception:
            pass
    return len(stale), stale


def compute_health_score(chunks, active_docs):
    """
    Compute the full policy health score.

    Args:
        chunks      : list of chunk dicts from pipeline.chunks
        active_docs : list of dicts from get_all_active_documents()

    Returns dict:
        score          int  0–100  overall score
        grade          str  A/B/C/D/F
        color          str  green/orange/red
        coverage_score int  0–40
        freshness_score int 0–30
        consistency_score int 0–30
        coverage_pct   int  % of required topics covered
        stale_count    int  number of outdated docs
        stale_names    list filenames of stale docs
        conflict_count int  number of conflicts logged
        gaps           list missing topic names
        covered        list covered topic names
        insights       list human-readable findings
    """

    # ── Pillar 1: Coverage (0–40 pts) ───────────
    if chunks:
        covered, gaps, coverage_pct = detect_gaps(chunks)
    else:
        covered, gaps, coverage_pct = [], [], 0

    coverage_score = round(coverage_pct * 0.40)   # 100% → 40 pts

    # ── Pillar 2: Freshness (0–30 pts) ──────────
    total_docs   = len(active_docs)
    stale_count, stale_names = _get_stale_doc_info(active_docs)

    if total_docs == 0:
        freshness_score = 0
    else:
        fresh_ratio     = 1 - (stale_count / total_docs)
        freshness_score = round(fresh_ratio * 30)

    # ── Pillar 3: Consistency (0–30 pts) ────────
    conflict_count = _get_conflict_count()

    if conflict_count == 0:
        consistency_score = 30
    elif conflict_count <= 2:
        consistency_score = 20
    elif conflict_count <= 5:
        consistency_score = 10
    else:
        consistency_score = 0

    # ── Total ────────────────────────────────────
    score = coverage_score + freshness_score + consistency_score

    # Grade
    if score >= 85:
        grade, color = "A", "green"
    elif score >= 70:
        grade, color = "B", "orange"
    elif score >= 55:
        grade, color = "C", "orange"
    elif score >= 40:
        grade, color = "D", "red"
    else:
        grade, color = "F", "red"

    # ── Human-readable insights ──────────────────
    insights = []

    if coverage_pct < 60:
        insights.append(
            f"🔴 Only {coverage_pct}% of standard HR topics are covered "
            f"— {len(gaps)} critical policy area(s) missing."
        )
    elif coverage_pct < 85:
        insights.append(
            f"🟡 {coverage_pct}% topic coverage — "
            f"{len(gaps)} gap(s) still need attention."
        )
    else:
        insights.append(f"🟢 Strong coverage — {coverage_pct}% of topics present.")

    if stale_count > 0:
        insights.append(
            f"🟡 {stale_count} document(s) not updated in over a year: "
            f"{', '.join(stale_names)}."
        )
    else:
        insights.append("🟢 All documents are current (uploaded within 1 year).")

    if conflict_count == 0:
        insights.append("🟢 No policy conflicts detected.")
    elif conflict_count <= 2:
        insights.append(
            f"🟡 {conflict_count} policy conflict(s) flagged — review recommended."
        )
    else:
        insights.append(
            f"🔴 {conflict_count} policy conflicts flagged — immediate review required."
        )

    if total_docs == 0:
        insights.insert(0, "🔴 No documents loaded — upload HR policies to get started.")

    return {
        "score":             score,
        "grade":             grade,
        "color":             color,
        "coverage_score":    coverage_score,
        "freshness_score":   freshness_score,
        "consistency_score": consistency_score,
        "coverage_pct":      coverage_pct,
        "stale_count":       stale_count,
        "stale_names":       stale_names,
        "conflict_count":    conflict_count,
        "gaps":              gaps,
        "covered":           covered,
        "insights":          insights
    }
