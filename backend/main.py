# ================================================
# PolicyGuard — FastAPI Backend
# Wraps the existing AI pipeline — zero AI code changes
# ================================================
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List
import io

from backend.models import (
    LoginRequest, LoginResponse, AskRequest,
    AskResponse, DocumentInfo, HealthScoreResponse
)
from backend.auth import create_token, verify_token, authenticate
from src.pipeline import PolicyGuardPipeline
from src.database import (
    get_analytics, get_all_active_documents,
    get_document_versions
)
from src.health_score import compute_health_score
from src.report import generate_audit_report

# ── App setup ────────────────────────────────────
app = FastAPI(title="PolicyGuard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Single shared pipeline ────────────────────────
pipeline = PolicyGuardPipeline()


# ── Auth ──────────────────────────────────────────
@app.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest):
    role = authenticate(req.username, req.password)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(req.username, role)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=role,
        username=req.username
    )


# ── Chat ──────────────────────────────────────────
@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest, user=Depends(verify_token)):
    if not pipeline.is_ready:
        raise HTTPException(
            status_code=400,
            detail="No documents loaded. Upload policy PDFs first."
        )
    result = pipeline.ask(
        req.question,
        req.employee_type,
        req.issue_category,
        anonymous=req.anonymous
    )
    return AskResponse(**{
        k: result.get(k, "") for k in AskResponse.model_fields
    })


# ── Documents ─────────────────────────────────────
@app.get("/api/documents")
def get_documents(user=Depends(verify_token)):
    return {
        "documents": pipeline.loaded_documents,
        "total_chunks": pipeline.chunk_count,
        "is_ready": pipeline.is_ready
    }


@app.post("/api/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    user=Depends(verify_token)
):
    if user["role"] != "Policy Admin":
        raise HTTPException(status_code=403, detail="Policy Admin only")
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF files only")

    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", file.filename)

    with open(save_path, "wb") as f:
        f.write(file.file.read())

    try:
        size_kb = os.path.getsize(save_path) / 1024
        pipeline.load_document(save_path, size_kb)
        versions = get_document_versions(file.filename)
        v = versions[0]["version"] if versions else 1
        conflicts = pipeline.scan_results.get(file.filename, [])
        return {
            "filename": file.filename,
            "version": v,
            "chunks": len([c for c in pipeline.chunks
                           if c["source"] == file.filename]),
            "conflicts": conflicts,
            "conflict_count": len(conflicts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{filename}")
def delete_document(filename: str, user=Depends(verify_token)):
    if user["role"] != "Policy Admin":
        raise HTTPException(status_code=403, detail="Policy Admin only")
    # Remove from pipeline chunks
    pipeline.chunks = [
        c for c in pipeline.chunks if c["source"] != filename
    ]
    pipeline.loaded_documents = [
        d for d in pipeline.loaded_documents if d["filename"] != filename
    ]
    # Remove file from disk
    path = os.path.join("data", filename)
    if os.path.exists(path):
        os.remove(path)
    # Rebuild index if chunks remain
    if pipeline.chunks:
        from src.retriever import build_index, save_index
        pipeline.index, _ = build_index(pipeline.chunks)
        save_index(pipeline.index, pipeline.chunks)
    else:
        pipeline.index = None
    return {"message": f"{filename} deleted successfully"}


# ── Dashboard ─────────────────────────────────────
@app.get("/api/dashboard")
def dashboard(user=Depends(verify_token)):
    if user["role"] not in ("Policy Admin", "HR Manager"):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        analytics = get_analytics()
        active_docs = get_all_active_documents()
        hs = compute_health_score(pipeline.chunks, active_docs)
        return {
            "total_queries":     analytics["total_queries"],
            "avg_latency":       analytics["avg_latency"],
            "guardrail_triggers":analytics["guardrail_triggers"],
            "document_count":    pipeline.document_count,
            "health_score":      hs,
            "decisions": analytics["decisions"].to_dict("records"),
            "categories": analytics["categories"].to_dict("records"),
            "recent_queries": analytics["recent_queries"].to_dict("records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Audit Report ──────────────────────────────────
@app.get("/api/report")
def audit_report(user=Depends(verify_token)):
    if user["role"] not in ("Policy Admin", "HR Manager"):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        analytics    = get_analytics()
        active_docs  = get_all_active_documents()
        queries_list = analytics["recent_queries"].to_dict("records")
        pdf_bytes    = generate_audit_report(queries_list, active_docs)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                "attachment; filename=policyguard_audit.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health check ──────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": os.getenv("MODEL_NAME", "qwen3.5:4b"),
        "documents_loaded": pipeline.document_count,
        "chunks": pipeline.chunk_count
    }
