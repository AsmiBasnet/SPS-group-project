# ================================================
# PolicyGuard — Main Streamlit Application
# ================================================

import streamlit as st
import time
import os
from src.pipeline import PolicyGuardPipeline
from src.database import get_analytics
from src.config import EMPLOYEE_TYPES, ISSUE_CATEGORIES

# ── Page Configuration ──────────────────────────
st.set_page_config(
    page_title="PolicyGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Initialize Pipeline ─────────────────────────
if "pipeline" not in st.session_state:
    st.session_state.pipeline = PolicyGuardPipeline()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "page" not in st.session_state:
    st.session_state.page = "Chat"

# ── Sidebar Navigation ───────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=60)
    st.title("PolicyGuard")
    st.caption("HR Compliance Intelligence Agent")
    st.divider()
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["💬 Policy Chat", "📊 Admin Dashboard"],
        label_visibility="collapsed"
    )
    st.session_state.page = page
    
    st.divider()
    
    # Document Upload
    st.subheader("📁 Knowledge Base")
    
    uploaded_files = st.file_uploader(
        "Upload HR Policy PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more HR policy documents"
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check if already loaded
            already_loaded = any(
                d["filename"] == uploaded_file.name
                for d in st.session_state.pipeline.loaded_documents
            )
            
            if not already_loaded:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    # Save to data folder
                    save_path = f"data/{uploaded_file.name}"
                    os.makedirs("data", exist_ok=True)
                    
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Load into pipeline
                    file_size = len(uploaded_file.getbuffer()) / 1024
                    chunk_count = st.session_state.pipeline.load_document(
                        save_path, file_size
                    )
                    
                st.success(f"✅ {uploaded_file.name}")
    
    # Show loaded documents
    if st.session_state.pipeline.loaded_documents:
        st.caption(
            f"📄 {st.session_state.pipeline.document_count} document(s) loaded"
            f" · {st.session_state.pipeline.chunk_count} sections indexed"
        )
        
        for doc in st.session_state.pipeline.loaded_documents:
            st.caption(f"  • {doc['filename']}")
    
    st.divider()
    
    # Session Controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Session"):
            st.session_state.pipeline.reset_session()
            st.session_state.chat_history = []
            st.rerun()
    with col2:
        if st.button("🗑️ Clear Docs"):
            st.session_state.pipeline.clear_documents()
            st.session_state.chat_history = []
            st.rerun()

# ── POLICY CHAT PAGE ─────────────────────────────
if st.session_state.page == "💬 Policy Chat":
    
    st.title("💬 Policy Chat")
    
    if not st.session_state.pipeline.is_ready:
        st.info(
            "👆 Upload your HR policy PDF documents "
            "in the sidebar to get started."
        )
        
        # Show example questions
        st.subheader("Example Questions You Can Ask:")
        examples = [
            "Am I eligible for FMLA leave?",
            "What is the process for reporting harassment?",
            "How many vacation days do I get per year?",
            "Can I request a flexible work arrangement?",
            "What accommodations are available under ADA?"
        ]
        for ex in examples:
            st.caption(f"• {ex}")
        st.stop()
    
    # Question Form
    with st.form("question_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            employee_type = st.selectbox(
                "Employee Type",
                EMPLOYEE_TYPES
            )
        
        with col2:
            issue_category = st.selectbox(
                "Issue Category",
                ISSUE_CATEGORIES
            )
        
        question = st.text_area(
            "Your Question",
            placeholder=(
                "Ask about any HR policy covered "
                "in your uploaded documents..."
            ),
            height=80
        )
        
        submitted = st.form_submit_button(
            "🔍 Get Policy Guidance",
            type="primary",
            use_container_width=True
        )
    
    # Process Question
    if submitted and question.strip():
        
        with st.spinner("Searching policy documents..."):
            result = st.session_state.pipeline.ask(
                question,
                employee_type,
                issue_category
            )
        
        # Add to history
        st.session_state.chat_history.append({
            "question": question,
            "employee_type": employee_type,
            "issue_category": issue_category,
            "result": result
        })
    
    # Display Chat History
    if st.session_state.chat_history:
        
        for item in reversed(st.session_state.chat_history):
            result = item["result"]
            decision = result["decision"]
            
            # Question bubble
            st.markdown(f"**You:** {item['question']}")
            
            # Response card
            if decision == "ANSWER":
                confidence = result.get("confidence", "MEDIUM")
                colors = {
                    "HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"
                }
                icon = colors.get(confidence, "🟡")
                
                st.success(
                    f"✅ **Answer** — Evidence Strength: "
                    f"{icon} {confidence}"
                )
                st.write(result["answer"])
                st.info(
                    f"📄 **Citation:** {result['citation']}  \n"
                    f"🔍 **Score:** {result.get('top_score', 0):.3f}  \n"
                    f"⏱️ **Time:** {result.get('latency', 0):.1f}s"
                )
                
                # Audit Trail
                with st.expander("🔍 View Logic Trace"):
                    st.json({
                        "decision": result["decision"],
                        "confidence": result["confidence"],
                        "similarity_score": result.get("top_score"),
                        "reasoning": result.get("reasoning"),
                        "citation": result.get("citation"),
                        "session_id": result.get("session_id"),
                        "latency_seconds": result.get("latency"),
                        "chunks_searched": len(
                            result.get("retrieved_chunks", [])
                        )
                    })
                
                st.warning(
                    "⚠️ Policy guidance only — "
                    "not legal advice. Verify before acting."
                )
            
            elif decision == "CLARIFY":
                st.info("🔵 **Clarification Needed**")
                st.write(
                    result.get(
                        "clarification_question",
                        "Please provide more context."
                    )
                )
            
            elif decision == "FLAG_CONFLICT":
                severity = result.get("conflict_severity", "RED")
                severity_icons = {
                    "RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"
                }
                icon = severity_icons.get(severity, "🔴")
                
                st.error(
                    f"{icon} **Policy Conflict Detected** "
                    f"— Severity: {severity}"
                )
                st.write(result["answer"])
                
                if result.get("conflict_clause_a"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Clause A:**")
                        st.write(result["conflict_clause_a"])
                    with col2:
                        st.markdown("**Clause B:**")
                        st.write(result["conflict_clause_b"])
                
                st.error(
                    "⚠️ Do not act on this query — "
                    "escalate to HR Director immediately."
                )
                
                with st.expander("🔍 View Logic Trace"):
                    st.json({
                        "decision": result["decision"],
                        "conflict_severity": result.get("conflict_severity"),
                        "reasoning": result.get("reasoning"),
                        "citation": result.get("citation"),
                        "latency_seconds": result.get("latency")
                    })
            
            elif decision == "REFUSED":
                st.warning("🛑 **Cannot Answer**")
                st.write(result["answer"])
                st.caption(
                    f"Evidence score: "
                    f"{result.get('top_score', 0):.3f} "
                    f"(minimum required: 0.65)"
                )
            
            st.divider()

# ── ADMIN DASHBOARD PAGE ─────────────────────────
elif st.session_state.page == "📊 Admin Dashboard":
    
    st.title("📊 Admin Dashboard")
    
    # Password protection
    admin_pass = st.text_input(
        "Admin Password",
        type="password",
        placeholder="Enter admin password"
    )
    
    if admin_pass != "admin123":
        st.warning("Enter admin password to view dashboard")
        st.stop()
    
    # Get analytics
    try:
        analytics = get_analytics()
    except Exception as e:
        st.error(f"No data yet — start asking questions first. ({e})")
        st.stop()
    
    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Queries",
            analytics["total_queries"]
        )
    with col2:
        st.metric(
            "Avg Response Time",
            f"{analytics['avg_latency']}s"
        )
    with col3:
        st.metric(
            "Guardrails Triggered",
            analytics["guardrail_triggers"]
        )
    with col4:
        documents = st.session_state.pipeline.document_count
        st.metric("Documents Loaded", documents)
    
    st.divider()
    
    # Decision Breakdown Chart
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Decision Breakdown")
        if not analytics["decisions"].empty:
            st.bar_chart(
                analytics["decisions"].set_index("decision")
            )
    
    with col2:
        st.subheader("Top Issue Categories")
        if not analytics["categories"].empty:
            st.bar_chart(
                analytics["categories"].set_index("issue_category")
            )
    
    st.divider()
    
    # Recent Queries Table
    st.subheader("Recent Queries")
    if not analytics["recent_queries"].empty:
        st.dataframe(
            analytics["recent_queries"],
            use_container_width=True
        )
    else:
        st.caption("No queries yet")