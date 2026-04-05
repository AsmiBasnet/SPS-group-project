# ================================================
# Master Pipeline
# Connects all components together
# ================================================

import time
import uuid
from src.ingestion import read_pdf, read_multiple_pdfs
from src.retriever import build_index, search, save_index, load_index
from src.reasoning import retry_reason
from src.guardrails import (
    check_evidence_strength,
    check_citation_present,
    get_confidence_level,
    get_conflict_severity
)
from src.database import init_database, log_query, log_document
from src.conflict_scanner import scan_for_conflicts


class PolicyGuardPipeline:

    def __init__(self):
        # Initialize database
        init_database()

        # Conflict scan results: {filename: [conflict_dicts]}
        self.scan_results = {}

        # Session
        self.session_id = str(uuid.uuid4())[:8]
        self.session = {
            "employee_type": None,
            "issue_category": None,
            "clauses_cited": [],
            "clarifications_asked": [],
            "conflict_flagged": False,
            "query_count": 0
        }

        # Restore persisted ChromaDB index automatically
        # so users don't need to re-upload on every login
        self.index, self.chunks = load_index()

        # Rebuild loaded_documents metadata from DB records
        self.loaded_documents = self._restore_loaded_documents()

    def _restore_loaded_documents(self):
        """
        Rebuild the in-memory loaded_documents list from:
          1. ChromaDB chunks (source of truth for what's indexed)
          2. DB active documents (for metadata like chunk counts)
        Called once at startup — makes re-login transparent.
        """
        from src.database import get_all_active_documents
        if not self.chunks:
            return []

        # Unique filenames present in the restored chunks
        indexed_sources = list(dict.fromkeys(
            c["source"] for c in self.chunks
        ))

        # Enrich with DB metadata where available
        db_docs = {d["filename"]: d for d in get_all_active_documents()}

        loaded = []
        for src in indexed_sources:
            chunk_count = sum(1 for c in self.chunks if c["source"] == src)
            db = db_docs.get(src, {})
            loaded.append({
                "filename": src,
                "chunks":   chunk_count,
                "path":     db.get("source_path", "")
            })

        if loaded:
            print(f"✅ Restored {len(loaded)} document(s) from persisted index")
        return loaded

    def load_document(self, file_path, file_size_kb=0):
        """Load a single PDF document into the pipeline."""
        import os

        # read_pdf returns (chunks, total_pages) — no second fitz.open() needed
        chunks, pages = read_pdf(file_path)

        if not chunks:
            raise ValueError(f"No content extracted from {file_path}")

        # Add to existing chunks
        self.chunks.extend(chunks)

        # Rebuild FAISS index with all chunks
        self.index, _ = build_index(self.chunks)

        # Persist index to disk
        save_index(self.index, self.chunks)

        # Track loaded document
        filename = os.path.basename(file_path)
        self.loaded_documents.append({
            "filename": filename,
            "chunks": len(chunks),
            "path": file_path
        })

        # Log to database — wrapped in try/except so a DB failure
        # never prevents the document from being used in queries
        try:
            log_document(filename, pages, len(chunks), file_size_kb)
        except Exception as e:
            print(f"⚠️ Warning: could not log document to database: {e}")

        # Proactive conflict scan — only if other documents already exist
        prior_chunks = [c for c in self.chunks if c["source"] != filename]
        if prior_chunks:
            print(f"🔍 Running conflict scan for {filename}...")
            try:
                conflicts = scan_for_conflicts(chunks, filename, self.chunks)
                self.scan_results[filename] = conflicts
                if conflicts:
                    print(f"⚠️ {len(conflicts)} conflict(s) detected in {filename}")
                else:
                    print(f"✅ No conflicts detected in {filename}")
            except Exception as e:
                print(f"⚠️ Conflict scan failed: {e}")
                self.scan_results[filename] = []
        else:
            # First document — nothing to compare against
            self.scan_results[filename] = []

    def ask(self, question, employee_type=None, issue_category=None, anonymous=False):
        """
        Main entry point — process a policy question.
        Returns structured response with decision and metadata.
        """
        if not self.index:
            return {
                "decision": "ERROR",
                "answer": "No documents loaded. Please upload an HR policy PDF first.",
                "citation": "N/A",
                "reasoning": "No index",
                "confidence": "NONE",
                "top_score": 0,
                "latency": 0
            }

        # Update session context
        if employee_type and employee_type != "-- Select --":
            self.session["employee_type"] = employee_type
        if issue_category and issue_category != "-- Select --":
            self.session["issue_category"] = issue_category
        self.session["query_count"] += 1

        # Build session context string
        session_context = ""
        if self.session["employee_type"]:
            session_context += f"Employee type: {self.session['employee_type']}. "
        if self.session["clauses_cited"]:
            session_context += (
                f"Previously discussed: "
                f"{', '.join(self.session['clauses_cited'][-3:])}."
            )

        # Start timer
        start_time = time.time()

        # Step 1 — Retrieve relevant chunks
        retrieved = search(question, self.index, self.chunks)

        # Step 2 — Guardrail: check evidence strength
        evidence_ok, evidence_msg = check_evidence_strength(retrieved)

        if not evidence_ok:
            latency = time.time() - start_time
            result = {
                "decision": "REFUSED",
                "answer": (
                    "I cannot find sufficient policy evidence to answer this question. "
                    "This topic may not be covered in your uploaded documents. "
                    "Please consult your HR Director directly."
                ),
                "citation": "N/A",
                "reasoning": evidence_msg,
                "confidence": "NONE",
                "top_score": retrieved[0]["score"] if retrieved else 0,
                "latency": round(latency, 1),
                "retrieved_chunks": retrieved
            }

            try:
                log_query(
                    question, employee_type, issue_category,
                    result, latency, self.session_id,
                    guardrail_triggered=True,
                    retrieved_chunks=retrieved,
                    anonymous=anonymous
                )
            except Exception as e:
                print(f"⚠️ Warning: could not log query to database: {e}")

            return result

        # Step 3 — LLM Reasoning
        llm_result = retry_reason(question, retrieved, session_context)

        # Step 4 — Validate citation for ANSWER
        if llm_result["decision"] == "ANSWER":
            if not check_citation_present(llm_result):
                llm_result["answer"] += (
                    " (Note: Please verify citation in source document)"
                )

        # Step 5 — Get confidence and conflict severity
        top_score = retrieved[0]["score"]
        confidence = get_confidence_level(top_score)
        conflict_severity, severity_msg = get_conflict_severity(
            llm_result, retrieved
        )

        # Step 6 — Update session
        if llm_result.get("citation") and llm_result["citation"] != "N/A":
            self.session["clauses_cited"].append(llm_result["citation"])
        if llm_result["decision"] == "FLAG_CONFLICT":
            self.session["conflict_flagged"] = True
        if llm_result["decision"] == "CLARIFY":
            q = llm_result.get("clarification_question", "")
            if q:
                self.session["clarifications_asked"].append(q)

        # Calculate latency
        latency = time.time() - start_time

        # Build final result
        result = {
            **llm_result,
            "confidence": confidence,
            "top_score": round(top_score, 3),
            "latency": round(latency, 1),
            "conflict_severity": conflict_severity,
            "severity_msg": severity_msg,
            "retrieved_chunks": retrieved,
            "session_id": self.session_id
        }

        # Step 7 — Log to database
        try:
            log_query(
                question, employee_type, issue_category,
                result, latency, self.session_id,
                guardrail_triggered=False,
                conflict_severity=conflict_severity,
                retrieved_chunks=retrieved,
                anonymous=anonymous
            )
        except Exception as e:
            print(f"⚠️ Warning: could not log query to database: {e}")

        return result

    def reset_session(self):
        """Clear session and start fresh."""
        self.session_id = str(uuid.uuid4())[:8]
        self.session = {
            "employee_type": None,
            "issue_category": None,
            "clauses_cited": [],
            "clarifications_asked": [],
            "conflict_flagged": False,
            "query_count": 0
        }

    def clear_documents(self):
        """Remove all loaded documents and reset index."""
        self.index = None
        self.chunks = []
        self.loaded_documents = []
        self.scan_results = {}
        self.reset_session()

    @property
    def is_ready(self):
        """Check if pipeline has documents loaded."""
        return self.index is not None and len(self.chunks) > 0

    @property
    def document_count(self):
        """Number of loaded documents."""
        return len(self.loaded_documents)

    @property
    def chunk_count(self):
        """Total number of indexed chunks."""
        return len(self.chunks)
