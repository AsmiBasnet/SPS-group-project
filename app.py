# ================================================
# PolicyGuard — Main Streamlit Application
# Phase A: Three roles, staging area, batch index,
#           auto-load from /policies folder
# ================================================

import streamlit as st
import os
import time
from datetime import datetime

from src.pipeline import PolicyGuardPipeline
from src.database import (
    get_analytics, get_all_active_documents,
    get_document_versions
)
from src.report import generate_audit_report
from src.gap_detector import detect_gaps
from src.health_score import compute_health_score
from src.config import (
    EMPLOYEE_TYPES, ISSUE_CATEGORIES,
    USERS, POLICIES_FOLDER
)

# ── Page Configuration ───────────────────────────
st.set_page_config(
    page_title="PolicyGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Role helpers ─────────────────────────────────
ROLE_ICONS = {
    "Policy Admin": "🔐",
    "HR Manager":   "👔",
    "Employee":     "👤"
}

def can_upload(role):
    return role == "Policy Admin"

def can_view_dashboard(role):
    return role in ("Policy Admin", "HR Manager")

# ── Login Gate ───────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None

if not st.session_state.logged_in:
    # ── Hero ────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding: 32px 0 16px 0;">
            <div style="font-size:56px;">🛡️</div>
            <h1 style="font-size:2.8rem; font-weight:900; margin:8px 0 4px 0;">
                PolicyGuard
            </h1>
            <p style="font-size:1.1rem; color:#666; margin:0;">
                HR Compliance Intelligence — 100% Local &amp; Private
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── Login form (centred column) ──────────────
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. employee")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Sign In →", use_container_width=True, type="primary"
            )

        if submitted:
            user = USERS.get(username)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Invalid username or password.")

    st.divider()

    # ── Demo account cards ───────────────────────
    st.markdown(
        "<p style='text-align:center; color:#888; font-size:13px;'>"
        "Demo accounts</p>",
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns(3)
    card_style = (
        "background:#f8f9fa; border:1px solid #e0e0e0; border-radius:12px; "
        "padding:16px 20px; text-align:center;"
    )
    with col1:
        st.markdown(
            f'<div style="{card_style}">'
            '<div style="font-size:28px;">🔐</div>'
            '<b>Policy Admin</b><br>'
            '<code>policy_admin / admin123</code><br>'
            '<small style="color:#888;">Upload · Dashboard · Chat</small>'
            "</div>",
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div style="{card_style}">'
            '<div style="font-size:28px;">👔</div>'
            '<b>HR Manager</b><br>'
            '<code>hr_manager / hr123</code><br>'
            '<small style="color:#888;">Dashboard · Chat</small>'
            "</div>",
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f'<div style="{card_style}">'
            '<div style="font-size:28px;">👤</div>'
            '<b>Employee</b><br>'
            '<code>employee / emp123</code><br>'
            '<small style="color:#888;">Chat · Anonymous Mode</small>'
            "</div>",
            unsafe_allow_html=True
        )
    st.stop()

# ── Initialize Pipeline ──────────────────────────
if "pipeline" not in st.session_state:
    st.session_state.pipeline = PolicyGuardPipeline()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "staged_files" not in st.session_state:
    st.session_state.staged_files = {}    # filename → {bytes, size_kb}
if "auto_loaded" not in st.session_state:
    st.session_state.auto_loaded = False
if "anonymous_mode" not in st.session_state:
    st.session_state.anonymous_mode = False
if "last_scan_report" not in st.session_state:
    st.session_state.last_scan_report = {}   # filename → [conflict dicts]

# ── A3: Auto-load from /policies folder ──────────
# Runs once per session at startup
if not st.session_state.auto_loaded:
    st.session_state.auto_loaded = True
    if os.path.isdir(POLICIES_FOLDER):
        pdfs = [
            f for f in os.listdir(POLICIES_FOLDER)
            if f.lower().endswith(".pdf")
        ]
        already = {
            d["filename"]
            for d in st.session_state.pipeline.loaded_documents
        }
        to_load = [p for p in pdfs if p not in already]
        if to_load:
            for pdf in to_load:
                path = os.path.join(POLICIES_FOLDER, pdf)
                try:
                    size_kb = os.path.getsize(path) / 1024
                    st.session_state.pipeline.load_document(path, size_kb)
                except Exception as e:
                    print(f"⚠️ Auto-load failed for {pdf}: {e}")

# ── Determine page ───────────────────────────────
role = st.session_state.role

if can_upload(role):
    nav_options = ["💬 Policy Chat", "📋 Document Manager", "📊 Dashboard"]
elif can_view_dashboard(role):
    nav_options = ["💬 Policy Chat", "📊 Dashboard"]
else:
    nav_options = ["💬 Policy Chat"]

# ── Sidebar ──────────────────────────────────────
with st.sidebar:
    st.title("🛡️ PolicyGuard")
    st.caption("HR Compliance Intelligence Agent")
    st.divider()

    # Role badge + sign out
    icon = ROLE_ICONS.get(role, "👤")
    st.caption(f"{icon} Signed in as **{role}**")
    if st.button("Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()

    # Navigation
    page = st.radio(
        "Navigation", nav_options, label_visibility="collapsed"
    )

    st.divider()

    # Anonymous mode toggle (Policy Chat only — not relevant on Dashboard)
    if page == "💬 Policy Chat":
        anon_on = st.toggle(
            "🕵️ Anonymous Mode",
            value=st.session_state.anonymous_mode,
            help=(
                "Your session ID will NOT be stored with your query. "
                "Responses are still logged for aggregate analytics "
                "but cannot be traced back to you."
            )
        )
        if anon_on != st.session_state.anonymous_mode:
            st.session_state.anonymous_mode = anon_on
            st.rerun()
        if st.session_state.anonymous_mode:
            st.caption("🔒 Identity hidden — queries logged anonymously.")

        st.divider()

    # Knowledge base status
    st.subheader("📁 Knowledge Base")
    if st.session_state.pipeline.loaded_documents:
        st.caption(
            f"📄 {st.session_state.pipeline.document_count} doc(s) · "
            f"{st.session_state.pipeline.chunk_count} sections indexed"
        )
        for doc in st.session_state.pipeline.loaded_documents:
            st.caption(f"  • {doc['filename']}")
    else:
        st.caption("No documents loaded yet.")

    if not can_upload(role):
        st.caption("📌 Contact Policy Admin to upload documents.")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.pipeline.reset_session()
            st.session_state.chat_history = []
            st.rerun()
    with col2:
        if st.button("🗑️ Clear Docs", use_container_width=True):
            st.session_state.pipeline.clear_documents()
            st.session_state.chat_history = []
            st.session_state.staged_files = {}
            st.rerun()

# ════════════════════════════════════════════════
# PAGE: Policy Chat
# ════════════════════════════════════════════════
if page == "💬 Policy Chat":

    st.title("💬 Policy Chat")

    if not st.session_state.pipeline.is_ready:
        # Empty state
        if can_upload(role):
            st.info("👆 Go to **Document Manager** to upload HR policy PDFs first.")
        else:
            st.info("⏳ No policy documents are loaded yet. Contact your Policy Admin.")

        st.subheader("Example Questions You Can Ask:")
        for ex in [
            "Am I eligible for FMLA leave?",
            "What is the process for reporting harassment?",
            "How many vacation days do I get per year?",
            "Can I request a flexible work arrangement?",
            "What accommodations are available under ADA?"
        ]:
            st.caption(f"• {ex}")
        st.stop()

    # Question form
    with st.form("question_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            employee_type = st.selectbox("Employee Type", EMPLOYEE_TYPES)
        with col2:
            issue_category = st.selectbox("Issue Category", ISSUE_CATEGORIES)

        question = st.text_area(
            "Your Question",
            placeholder="Ask about any HR policy in your uploaded documents...",
            height=80
        )
        submitted = st.form_submit_button(
            "🔍 Get Policy Guidance",
            type="primary",
            use_container_width=True
        )

    if submitted and question.strip():
        with st.spinner("Searching policy documents..."):
            result = st.session_state.pipeline.ask(
                question, employee_type, issue_category,
                anonymous=st.session_state.anonymous_mode
            )
        st.session_state.chat_history.append({
            "question":       question,
            "employee_type":  employee_type,
            "issue_category": issue_category,
            "result":         result,
            "anonymous":      st.session_state.anonymous_mode
        })

    # Chat history
    for item in reversed(st.session_state.chat_history):
        result   = item["result"]
        decision = result["decision"]
        is_anon  = item.get("anonymous", False)

        # ── Question bubble ──────────────────────
        anon_badge = (
            '<span style="background:#1a1a2e;color:#a0c4ff;border:1px solid #3a6fa0;'
            'border-radius:20px;padding:1px 10px;font-size:11px;font-weight:600;'
            'margin-left:8px;">🕵️ anonymous</span>'
            if is_anon else ""
        )
        st.markdown(
            f'<div style="background:#f0f4ff;border-left:4px solid #4a6cf7;'
            f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
            f'<b>You</b>{anon_badge}<br>{item["question"]}</div>',
            unsafe_allow_html=True
        )

        # ── Response card ────────────────────────
        if decision == "ANSWER":
            confidence = result.get("confidence", "MEDIUM")
            conf_color = {"HIGH": "#2d6a4f", "MEDIUM": "#e76f51", "LOW": "#c9184a"}.get(
                confidence, "#555"
            )
            conf_icon  = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(confidence, "🟡")
            st.markdown(
                f'<div style="background:#f0fff4;border:1px solid #b7e4c7;'
                f'border-radius:12px;padding:16px 20px;margin-bottom:4px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'margin-bottom:8px;">'
                f'<span style="font-weight:700;color:#1b4332;">✅ Policy Answer</span>'
                f'<span style="background:{conf_color};color:#fff;border-radius:20px;'
                f'padding:2px 10px;font-size:12px;">{conf_icon} {confidence} confidence</span>'
                f'</div>'
                f'<p style="margin:0 0 10px 0;">{result["answer"]}</p>'
                f'<div style="font-size:12px;color:#555;border-top:1px solid #b7e4c7;'
                f'padding-top:8px;">'
                f'📄 <b>Citation:</b> {result["citation"]} &nbsp;|&nbsp; '
                f'🔍 <b>Score:</b> {result.get("top_score",0):.3f} &nbsp;|&nbsp; '
                f'⏱️ <b>Time:</b> {result.get("latency",0):.1f}s'
                f'</div></div>',
                unsafe_allow_html=True
            )
            st.caption("⚠️ Policy guidance only — not legal advice. Verify before acting.")
            with st.expander("🔍 View Logic Trace"):
                st.json({
                    "decision":         result["decision"],
                    "confidence":       result["confidence"],
                    "similarity_score": result.get("top_score"),
                    "reasoning":        result.get("reasoning"),
                    "citation":         result.get("citation"),
                    "session_id":       result.get("session_id"),
                    "latency_seconds":  result.get("latency"),
                    "chunks_searched":  len(result.get("retrieved_chunks", []))
                })

        elif decision == "CLARIFY":
            st.markdown(
                '<div style="background:#e8f4fd;border:1px solid #90caf9;'
                'border-radius:12px;padding:16px 20px;margin-bottom:4px;">'
                '<span style="font-weight:700;color:#0d47a1;">🔵 More info needed</span><br>'
                f'{result.get("clarification_question","Please provide more context.")}'
                '</div>',
                unsafe_allow_html=True
            )

        elif decision == "FLAG_CONFLICT":
            severity   = result.get("conflict_severity", "RED")
            sev_colors = {"RED": ("#fff5f5","#ffb3b3","#c9184a"),
                          "YELLOW": ("#fffbea","#ffe082","#f57f17"),
                          "GREEN":  ("#f0fff4","#b7e4c7","#2d6a4f")}
            bg, border, txt = sev_colors.get(severity, sev_colors["RED"])
            sev_icon = {"RED":"🔴","YELLOW":"🟡","GREEN":"🟢"}.get(severity,"🔴")
            st.markdown(
                f'<div style="background:{bg};border:1px solid {border};'
                f'border-radius:12px;padding:16px 20px;margin-bottom:4px;">'
                f'<span style="font-weight:700;color:{txt};">'
                f'{sev_icon} Policy Conflict Detected — Severity: {severity}</span><br>'
                f'{result["answer"]}'
                f'</div>',
                unsafe_allow_html=True
            )
            if result.get("conflict_clause_a"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Clause A:**")
                    st.write(result["conflict_clause_a"])
                with c2:
                    st.markdown("**Clause B:**")
                    st.write(result["conflict_clause_b"])
            st.error("⚠️ Do not act — escalate to HR Director immediately.")

        elif decision == "REFUSED":
            st.markdown(
                '<div style="background:#fff8e1;border:1px solid #ffe082;'
                'border-radius:12px;padding:16px 20px;margin-bottom:4px;">'
                '<span style="font-weight:700;color:#e65100;">🛑 Insufficient Evidence</span><br>'
                f'{result["answer"]}<br>'
                f'<small style="color:#888;">Evidence score: {result.get("top_score",0):.3f} '
                f'(minimum required: 0.65)</small>'
                '</div>',
                unsafe_allow_html=True
            )

        st.divider()

# ════════════════════════════════════════════════
# PAGE: Document Manager (Policy Admin only)
# ════════════════════════════════════════════════
elif page == "📋 Document Manager":

    st.title("📋 Document Manager")
    st.caption(
        "Stage your policy documents, review them, then index all at once. "
        "Only approved PDFs should be uploaded here."
    )

    st.divider()

    # ── Step 1: Stage files ──────────────────────
    st.subheader("Step 1 — Select Policy Documents")
    st.caption(
        "Select one or more PDFs. Nothing is processed yet — "
        "you review first."
    )

    new_uploads = st.file_uploader(
        "Select HR Policy PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Hold Cmd/Ctrl to select multiple files"
    )

    # Add newly selected files to staging area
    if new_uploads:
        for f in new_uploads:
            if f.name not in st.session_state.staged_files:
                st.session_state.staged_files[f.name] = {
                    "bytes":   f.getbuffer(),
                    "size_kb": round(len(f.getbuffer()) / 1024, 1)
                }

    # ── Step 2: Review staged files ─────────────
    st.divider()
    st.subheader("Step 2 — Review Staged Documents")

    if not st.session_state.staged_files:
        st.info("No files staged yet. Select PDFs above.")
    else:
        st.caption(
            f"{len(st.session_state.staged_files)} file(s) ready to index. "
            "Remove any you don't want before confirming."
        )

        to_remove = []
        for fname, meta in st.session_state.staged_files.items():
            already = any(
                d["filename"] == fname
                for d in st.session_state.pipeline.loaded_documents
            )
            col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
            with col1:
                st.write(f"📄 **{fname}**")
            with col2:
                st.caption(f"{meta['size_kb']} KB")
            with col3:
                st.caption("✅ Already indexed" if already else "🆕 New")
            with col4:
                if st.button("✕", key=f"remove_{fname}"):
                    to_remove.append(fname)

        for fname in to_remove:
            del st.session_state.staged_files[fname]
            st.rerun()

    # ── Step 3: Confirm and batch index ─────────
    st.divider()
    st.subheader("Step 3 — Confirm & Index All")

    new_files = {
        fname: meta
        for fname, meta in st.session_state.staged_files.items()
        if not any(
            d["filename"] == fname
            for d in st.session_state.pipeline.loaded_documents
        )
    }

    if not new_files:
        st.info("No new files to index.")
    else:
        st.caption(
            f"**{len(new_files)} new document(s)** will be saved, embedded, "
            f"and indexed in one batch."
        )

        if st.button(
            f"✅ Index {len(new_files)} Document(s)",
            type="primary",
            use_container_width=True
        ):
            os.makedirs("data", exist_ok=True)
            results_log = []

            progress = st.progress(0, text="Starting...")
            total    = len(new_files)

            for i, (fname, meta) in enumerate(new_files.items()):

                # Step indicator
                progress.progress(
                    i / total,
                    text=f"[{i+1}/{total}] Saving {fname}..."
                )

                # Save to disk
                save_path = os.path.join("data", fname)
                with open(save_path, "wb") as f:
                    f.write(meta["bytes"])

                progress.progress(
                    (i + 0.4) / total,
                    text=f"[{i+1}/{total}] Embedding {fname}..."
                )

                # Index
                try:
                    st.session_state.pipeline.load_document(
                        save_path, meta["size_kb"]
                    )
                    versions = get_document_versions(fname)
                    v = versions[0]["version"] if versions else 1
                    # Capture conflict scan results produced during load
                    scan = st.session_state.pipeline.scan_results.get(fname, [])
                    st.session_state.last_scan_report[fname] = scan
                    results_log.append(
                        {"file": fname, "status": "✅", "version": f"v{v}",
                         "conflicts": scan}
                    )
                except Exception as e:
                    results_log.append(
                        {"file": fname, "status": "❌", "version": str(e),
                         "conflicts": []}
                    )

                progress.progress(
                    (i + 1) / total,
                    text=f"[{i+1}/{total}] Done — {fname}"
                )

            progress.progress(1.0, text="✅ All documents indexed!")

            # Clear staging area
            st.session_state.staged_files = {}

            # Summary
            st.success(
                f"✅ Indexed {len(results_log)} document(s) — "
                f"{st.session_state.pipeline.chunk_count} total sections in knowledge base."
            )
            for r in results_log:
                conflict_count = len(r.get("conflicts", []))
                conflict_badge = (
                    f"  ⚠️ {conflict_count} conflict(s) found"
                    if conflict_count else "  ✅ No conflicts"
                ) if r["status"] == "✅" else ""
                st.caption(f"{r['status']} {r['file']} — {r['version']}{conflict_badge}")

            # ── Conflict Scan Report ─────────────────
            total_conflicts = sum(
                len(r.get("conflicts", [])) for r in results_log
            )
            if total_conflicts > 0:
                st.divider()
                st.error(
                    f"🔴 **Proactive Conflict Scan** — "
                    f"{total_conflicts} potential conflict(s) detected across uploaded documents. "
                    f"Review before using these policies."
                )
                for r in results_log:
                    for c in r.get("conflicts", []):
                        with st.expander(
                            f"⚠️ Conflict: **{c['new_source']}** vs **{c['existing_src']}** "
                            f"(similarity {c['similarity']:.0%})"
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(
                                    f"**📄 {c['new_source']}** — Page {c['new_page']}"
                                )
                                st.info(c["new_text"][:300])
                            with col2:
                                st.markdown(
                                    f"**📄 {c['existing_src']}** — Page {c['existing_page']}"
                                )
                                st.warning(c["existing_text"][:300])
                            st.caption(f"🤖 LLM assessment: {c['reason']}")
                            st.error(
                                "⚠️ Do not use conflicting policies until an HR Director resolves this."
                            )
            elif any(r["status"] == "✅" for r in results_log):
                # Only show "clean" message if at least 2 docs were ever loaded
                # (first upload has nothing to compare against)
                prior = len(st.session_state.pipeline.loaded_documents)
                if prior > 1:
                    st.success("✅ Conflict scan complete — no contradictions detected.")

    # ── Currently loaded documents ───────────────
    st.divider()
    st.subheader("Currently Indexed Documents")

    if st.session_state.pipeline.loaded_documents:
        for doc in st.session_state.pipeline.loaded_documents:
            versions = get_document_versions(doc["filename"])
            v = versions[0]["version"] if versions else 1
            col1, col2, col3 = st.columns([4, 2, 2])
            with col1:
                st.write(f"📄 {doc['filename']}")
            with col2:
                st.caption(f"v{v} · {doc['chunks']} sections")
            with col3:
                if versions:
                    st.caption(
                        f"Uploaded: {versions[0]['uploaded'][:10]}"
                    )
    else:
        st.caption("No documents indexed yet.")

# ════════════════════════════════════════════════
# PAGE: Dashboard (Policy Admin + HR Manager)
# ════════════════════════════════════════════════
elif page == "📊 Dashboard":

    st.title("📊 Admin Dashboard")

    try:
        analytics = get_analytics()
    except Exception as e:
        st.error(f"No data yet — start asking questions first. ({e})")
        st.stop()

    # ── Policy Health Score ──────────────────────
    active_docs = get_all_active_documents()
    hs = compute_health_score(
        st.session_state.pipeline.chunks,
        active_docs
    )

    score_color = {
        "green":  "#2d6a4f",
        "orange": "#e76f51",
        "red":    "#c9184a"
    }.get(hs["color"], "#333333")

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 28px 32px;
            margin-bottom: 24px;
        ">
            <div style="display:flex; align-items:center; gap:32px; flex-wrap:wrap;">
                <div style="text-align:center; min-width:110px;">
                    <div style="
                        font-size: 64px;
                        font-weight: 900;
                        color: {score_color};
                        line-height: 1;
                    ">{hs['score']}</div>
                    <div style="
                        font-size: 22px;
                        font-weight: 700;
                        color: {score_color};
                    ">/ 100  Grade {hs['grade']}</div>
                    <div style="
                        font-size: 12px;
                        color: #aaaaaa;
                        margin-top: 4px;
                    ">Policy Health Score</div>
                </div>
                <div style="flex:1; min-width:220px;">
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:#cccccc; font-size:13px;">📋 Coverage</span>
                            <span style="color:#ffffff; font-weight:700;">{hs['coverage_score']} / 40</span>
                        </div>
                        <div style="background:#2a2a4a; border-radius:6px; height:8px; margin-top:4px;">
                            <div style="background:{score_color}; width:{int(hs['coverage_score']/40*100)}%; height:8px; border-radius:6px;"></div>
                        </div>
                    </div>
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:#cccccc; font-size:13px;">🕐 Freshness</span>
                            <span style="color:#ffffff; font-weight:700;">{hs['freshness_score']} / 30</span>
                        </div>
                        <div style="background:#2a2a4a; border-radius:6px; height:8px; margin-top:4px;">
                            <div style="background:{score_color}; width:{int(hs['freshness_score']/30*100)}%; height:8px; border-radius:6px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:#cccccc; font-size:13px;">⚖️ Consistency</span>
                            <span style="color:#ffffff; font-weight:700;">{hs['consistency_score']} / 30</span>
                        </div>
                        <div style="background:#2a2a4a; border-radius:6px; height:8px; margin-top:4px;">
                            <div style="background:{score_color}; width:{int(hs['consistency_score']/30*100)}%; height:8px; border-radius:6px;"></div>
                        </div>
                    </div>
                </div>
                <div style="flex:1; min-width:200px;">
                    {''.join([f'<div style="color:#cccccc; font-size:12px; margin-bottom:6px;">{i}</div>' for i in hs['insights']])}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Queries",       analytics["total_queries"])
    col2.metric("Avg Response Time",   f"{analytics['avg_latency']}s")
    col3.metric("Guardrails Triggered",analytics["guardrail_triggers"])
    col4.metric("Documents Loaded",    st.session_state.pipeline.document_count)

    st.divider()

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Decision Breakdown")
        if not analytics["decisions"].empty:
            st.bar_chart(analytics["decisions"].set_index("decision"))
    with col2:
        st.subheader("Top Issue Categories")
        if not analytics["categories"].empty:
            st.bar_chart(analytics["categories"].set_index("issue_category"))

    st.divider()

    # Recent queries
    st.subheader("Recent Queries")
    if not analytics["recent_queries"].empty:
        st.dataframe(analytics["recent_queries"], use_container_width=True)
    else:
        st.caption("No queries yet.")

    st.divider()

    # Policy gap detail (expanded from health score)
    st.subheader("🔍 Policy Gap Detail")
    if hs["gaps"]:
        st.error(f"**{len(hs['gaps'])} missing topic(s):**")
        for g in hs["gaps"]:
            st.markdown(f"- ❌ {g}")
    elif st.session_state.pipeline.chunks:
        st.success("✅ All standard HR topics are covered.")
    else:
        st.info("Upload documents to run gap detection.")

    if hs["covered"]:
        with st.expander("✅ View covered topics"):
            for c in hs["covered"]:
                st.markdown(f"- ✅ {c}")

    st.divider()

    # PDF export
    st.subheader("📄 Export Audit Report")
    st.caption("Download a PDF of the full query history and document log.")

    if st.button("⬇️ Generate PDF Report", type="primary"):
        try:
            active_docs  = get_all_active_documents()
            queries_list = (
                analytics["recent_queries"].to_dict("records")
                if not analytics["recent_queries"].empty else []
            )
            pdf_bytes = generate_audit_report(queries_list, active_docs)
            st.download_button(
                label="📥 Download Report PDF",
                data=pdf_bytes,
                file_name=(
                    f"policyguard_audit_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Could not generate report: {e}")
