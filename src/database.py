# ================================================
# SQLite Database
# Stores all queries and decisions for audit trail
# and admin dashboard analytics
# ================================================

import sqlite3
import json
import os
from datetime import datetime
from src.config import DB_PATH


def init_database():
    """Create database and tables if they don't exist."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                question TEXT NOT NULL,
                employee_type TEXT,
                issue_category TEXT,
                decision TEXT NOT NULL,
                answer TEXT,
                citation TEXT,
                confidence TEXT,
                top_score REAL,
                latency_seconds REAL,
                guardrail_triggered INTEGER DEFAULT 0,
                conflict_severity TEXT,
                sources TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                pages INTEGER,
                chunks INTEGER,
                file_size_kb REAL,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Database initialized")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


def log_query(
    question,
    employee_type,
    issue_category,
    decision_result,
    latency,
    session_id=None,
    guardrail_triggered=False,
    conflict_severity=None,
    retrieved_chunks=None
):
    """Log every query to SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Collect unique source filenames from retrieved chunks
        sources = []
        if retrieved_chunks:
            sources = list(set([c["source"] for c in retrieved_chunks]))

        cursor.execute("""
            INSERT INTO queries (
                timestamp, session_id, question,
                employee_type, issue_category,
                decision, answer, citation,
                confidence, top_score, latency_seconds,
                guardrail_triggered, conflict_severity, sources
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            session_id,
            question,
            employee_type,
            issue_category,
            decision_result.get("decision"),
            decision_result.get("answer"),
            decision_result.get("citation"),
            decision_result.get("confidence"),
            decision_result.get("top_score"),
            round(latency, 2),
            1 if guardrail_triggered else 0,
            conflict_severity,
            json.dumps(sources)
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"❌ log_query failed: {e}")
        # Re-raise so the pipeline's try/except can decide whether to surface it
        raise


def log_document(filename, pages, chunks, file_size_kb):
    """
    Log uploaded document metadata with auto versioning.
    Each re-upload of the same filename gets version + 1.
    Previous versions are marked as 'superseded'.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check how many times this file has been uploaded before
        cursor.execute(
            "SELECT COUNT(*) FROM documents WHERE filename = ?",
            (filename,)
        )
        previous_count = cursor.fetchone()[0]
        version = previous_count + 1

        # Mark all previous versions of this file as superseded
        if previous_count > 0:
            cursor.execute(
                "UPDATE documents SET status = 'superseded' WHERE filename = ?",
                (filename,)
            )

        # Insert new version as active
        cursor.execute("""
            INSERT INTO documents (
                filename, upload_date, pages, chunks, file_size_kb,
                version, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (
            filename,
            datetime.now().isoformat(),
            pages,
            chunks,
            file_size_kb,
            version
        ))

        conn.commit()
        conn.close()

        if version > 1:
            print(f"📄 {filename} — version {version} uploaded (previous marked superseded)")
        return version

    except Exception as e:
        print(f"❌ log_document failed: {e}")
        raise


def get_document_versions(filename):
    """Return full version history for a document."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT version, upload_date, pages, chunks, file_size_kb, status
            FROM documents
            WHERE filename = ?
            ORDER BY version DESC
        """, (filename,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "version":    r[0],
                "uploaded":   r[1],
                "pages":      r[2],
                "chunks":     r[3],
                "size_kb":    r[4],
                "status":     r[5]
            }
            for r in rows
        ]
    except Exception as e:
        print(f"❌ get_document_versions failed: {e}")
        return []


def get_all_active_documents():
    """Return only the latest active version of each document."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, upload_date, pages, chunks, file_size_kb, version
            FROM documents
            WHERE status = 'active'
            ORDER BY upload_date DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "filename":  r[0],
                "uploaded":  r[1],
                "pages":     r[2],
                "chunks":    r[3],
                "size_kb":   r[4],
                "version":   r[5]
            }
            for r in rows
        ]
    except Exception as e:
        print(f"❌ get_all_active_documents failed: {e}")
        return []


def get_analytics():
    """Get analytics data for admin dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH)

        import pandas as pd

        # Total queries
        total = pd.read_sql(
            "SELECT COUNT(*) as count FROM queries", conn
        ).iloc[0]["count"]

        # Decision breakdown
        decisions = pd.read_sql("""
            SELECT decision, COUNT(*) as count
            FROM queries
            GROUP BY decision
        """, conn)

        # Average latency
        avg_latency = pd.read_sql("""
            SELECT AVG(latency_seconds) as avg_latency
            FROM queries
            WHERE guardrail_triggered = 0
        """, conn).iloc[0]["avg_latency"]

        # Guardrail triggers
        guardrails = pd.read_sql("""
            SELECT COUNT(*) as count
            FROM queries
            WHERE guardrail_triggered = 1
        """, conn).iloc[0]["count"]

        # Recent queries
        recent = pd.read_sql("""
            SELECT timestamp, question, decision, citation, latency_seconds
            FROM queries
            ORDER BY timestamp DESC
            LIMIT 20
        """, conn)

        # Most common issue categories
        categories = pd.read_sql("""
            SELECT issue_category, COUNT(*) as count
            FROM queries
            WHERE issue_category IS NOT NULL
            GROUP BY issue_category
            ORDER BY count DESC
        """, conn)

        conn.close()

        return {
            "total_queries": int(total),
            "decisions": decisions,
            "avg_latency": round(float(avg_latency or 0), 1),
            "guardrail_triggers": int(guardrails),
            "recent_queries": recent,
            "categories": categories
        }

    except Exception as e:
        print(f"❌ get_analytics failed: {e}")
        raise
