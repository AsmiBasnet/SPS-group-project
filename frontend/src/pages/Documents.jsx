import { useState, useEffect, useRef } from "react";
import Layout from "../components/Layout";
import api from "../api";

function FileIcon({ size = 40 }) {
  return (
    <div style={{
      width: size, height: size,
      background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
      border: "1px solid rgba(99,102,241,0.2)",
      borderRadius: 10,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: size * 0.5,
      flexShrink: 0,
    }}>📄</div>
  );
}

function ConflictPanel({ conflicts, onClose }) {
  return (
    <div className="scale-in" style={{
      position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 200,
      width: 420,
      background: "#0e1120",
      border: "1px solid var(--border-up)",
      borderRadius: 14,
      boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
      overflow: "hidden",
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0.85rem 1.1rem",
        borderBottom: "1px solid var(--border)",
        background: "rgba(245,158,11,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1rem" }}>⚠️</span>
          <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#f59e0b", letterSpacing: "0.04em" }}>
            {conflicts.length} POLICY CONFLICT{conflicts.length > 1 ? "S" : ""} DETECTED
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            width: 24, height: 24, padding: 0, fontSize: "1rem",
            background: "transparent", color: "var(--text-2)",
            border: "none", cursor: "pointer", lineHeight: 1,
          }}
        >×</button>
      </div>
      <div style={{ maxHeight: 340, overflowY: "auto", padding: "0.75rem" }}>
        {conflicts.map((c, i) => (
          <div key={i} style={{
            marginBottom: "0.75rem",
            padding: "0.85rem",
            background: "rgba(245,158,11,0.04)",
            border: "1px solid rgba(245,158,11,0.15)",
            borderRadius: 10,
          }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
              <div>
                <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#f59e0b", marginBottom: 4, letterSpacing: "0.05em" }}>
                  THIS DOCUMENT
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-2)", lineHeight: 1.5 }}>
                  "{c.new_text?.slice(0, 100)}…"
                </div>
              </div>
              <div>
                <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#94a3b8", marginBottom: 4, letterSpacing: "0.05em" }}>
                  CONFLICTS WITH
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-2)", lineHeight: 1.5 }}>
                  "{c.existing_text?.slice(0, 100)}…"
                </div>
                <div style={{ fontSize: "0.68rem", color: "var(--text-3)", marginTop: 3 }}>
                  {c.existing_src} · page {c.existing_page}
                </div>
              </div>
            </div>
            {c.reason && (
              <div style={{
                padding: "0.4rem 0.65rem",
                background: "rgba(245,158,11,0.08)",
                borderRadius: 7, fontSize: "0.75rem", color: "#fcd34d",
                display: "flex", gap: 6,
              }}>
                <span>⚡</span> {c.reason}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function DocumentRow({ doc, onDelete, deleting }) {
  const [showConflicts, setShowConflicts] = useState(false);
  const conflicts = doc.conflicts || [];

  return (
    <tr style={{ transition: "background 0.1s" }}>
      <td>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <FileIcon size={36} />
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{doc.filename}</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-3)", marginTop: 1 }}>
              PDF Document
            </div>
          </div>
        </div>
      </td>
      <td>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          padding: "0.3rem 0.7rem",
          background: "rgba(99,102,241,0.08)",
          border: "1px solid rgba(99,102,241,0.15)",
          borderRadius: 20,
          fontSize: "0.78rem", color: "#a5b4fc", fontWeight: 500,
        }}>
          {doc.chunks} chunks
        </div>
      </td>
      <td>
        <div style={{ position: "relative", display: "inline-block" }}>
          {conflicts.length > 0 ? (
            <button
              onClick={() => setShowConflicts(v => !v)}
              className="tag tag-amber"
              style={{ cursor: "pointer", border: "1px solid rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.1)" }}
            >
              ⚠️ {conflicts.length} conflict{conflicts.length > 1 ? "s" : ""}
            </button>
          ) : (
            <span className="tag tag-green">✅ Clean</span>
          )}
          {showConflicts && (
            <ConflictPanel conflicts={conflicts} onClose={() => setShowConflicts(false)} />
          )}
        </div>
      </td>
      <td>
        <span className="tag tag-green">
          <span className="dot-live" style={{ width: 6, height: 6 }} />
          Active
        </span>
      </td>
      <td>
        <button
          className="btn-danger"
          style={{ padding: "0.35rem 0.85rem", fontSize: "0.78rem" }}
          disabled={deleting}
          onClick={() => onDelete(doc.filename)}
        >
          {deleting ? <span className="spinner" /> : "Remove"}
        </button>
      </td>
    </tr>
  );
}

function UploadZone({ onUpload, uploading }) {
  const fileRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handle = (file) => {
    if (!file) return;
    if (!file.name.endsWith(".pdf")) { alert("Only PDF files are supported."); return; }
    onUpload(file);
  };

  return (
    <div
      onClick={() => !uploading && fileRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => {
        e.preventDefault(); setDragOver(false);
        handle(e.dataTransfer.files[0]);
      }}
      style={{
        border: `2px dashed ${dragOver ? "var(--indigo)" : "rgba(255,255,255,0.1)"}`,
        borderRadius: 16,
        padding: "2.5rem",
        textAlign: "center",
        cursor: uploading ? "wait" : "pointer",
        transition: "all 0.2s",
        background: dragOver
          ? "rgba(99,102,241,0.06)"
          : uploading ? "rgba(255,255,255,0.02)" : "transparent",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Grid overlay */}
      {dragOver && (
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "linear-gradient(rgba(99,102,241,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.05) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          pointerEvents: "none",
        }} />
      )}
      <input ref={fileRef} type="file" accept=".pdf" style={{ display: "none" }} onChange={e => handle(e.target.files[0])} />
      <div style={{
        width: 56, height: 56, margin: "0 auto 1rem",
        background: uploading ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.04)",
        border: `1px solid ${dragOver ? "rgba(99,102,241,0.4)" : "rgba(255,255,255,0.08)"}`,
        borderRadius: 14,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "1.5rem",
        transition: "all 0.2s",
        boxShadow: dragOver ? "0 0 24px rgba(99,102,241,0.2)" : "none",
      }}>
        {uploading ? <span className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} /> : "📤"}
      </div>
      <div style={{ fontWeight: 700, marginBottom: 5, fontSize: "0.95rem" }}>
        {uploading ? "Indexing document…" : dragOver ? "Drop to upload" : "Upload Policy PDF"}
      </div>
      <div style={{ fontSize: "0.78rem", color: "var(--text-3)", maxWidth: 300, margin: "0 auto" }}>
        {uploading
          ? "Chunking, embedding with nomic-embed-text, scanning for conflicts…"
          : "Drag & drop or click to browse · PDF files only · Processed 100% locally"
        }
      </div>
    </div>
  );
}

export default function Documents() {
  const [docs, setDocs]       = useState([]);
  const [isReady, setIsReady] = useState(false);
  const [chunks, setChunks]   = useState(0);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting]   = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const { data } = await api.get("/api/documents");
      setDocs(data.documents || []);
      setIsReady(data.is_ready);
      setChunks(data.total_chunks || 0);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const upload = async (file) => {
    setError(""); setUploadResult(null); setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await api.post("/api/documents/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult(data);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setUploading(false);
    }
  };

  const remove = async (filename) => {
    if (!window.confirm(`Remove "${filename}" from the policy index?`)) return;
    setDeleting(filename);
    try {
      await api.delete(`/api/documents/${encodeURIComponent(filename)}`);
      await load();
      setUploadResult(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <Layout>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "2rem" }}>
          <div>
            <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: 4 }}>
              Document Manager
            </h1>
            <p style={{ color: "var(--text-2)", fontSize: "0.82rem" }}>
              Upload PDF policy files · Indexed locally with vector embeddings
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {isReady
              ? <span className="tag tag-green">
                  <span className="dot-live" /> {docs.length} docs · {chunks} chunks
                </span>
              : <span className="tag tag-amber">⏳ No documents indexed</span>
            }
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="slide-up" style={{
            display: "flex", alignItems: "center", gap: 10,
            background: "rgba(239,68,68,0.07)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: 12, padding: "0.85rem 1.1rem",
            fontSize: "0.85rem", color: "#f87171", marginBottom: "1.25rem",
          }}>
            <span>⚠️</span> {error}
            <button onClick={() => setError("")} style={{ marginLeft: "auto", background: "transparent", color: "#f87171", border: "none", cursor: "pointer", fontSize: "1.1rem", padding: 0 }}>×</button>
          </div>
        )}

        {/* Upload result */}
        {uploadResult && (
          <div className="slide-up" style={{
            background: "rgba(16,185,129,0.06)",
            border: "1px solid rgba(16,185,129,0.2)",
            borderRadius: 14, padding: "1.1rem 1.4rem",
            marginBottom: "1.25rem",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div>
              <div style={{ fontWeight: 700, color: "#34d399", marginBottom: 3, display: "flex", alignItems: "center", gap: 8 }}>
                <span>✅</span> {uploadResult.filename} indexed successfully
              </div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-2)" }}>
                Version {uploadResult.version} · {uploadResult.chunks} chunks created and embedded
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {uploadResult.conflict_count > 0 ? (
                <span className="tag tag-amber">⚠️ {uploadResult.conflict_count} conflict{uploadResult.conflict_count > 1 ? "s" : ""}</span>
              ) : (
                <span className="tag tag-green">✅ No conflicts</span>
              )}
              <button onClick={() => setUploadResult(null)} style={{ background: "transparent", border: "none", color: "var(--text-3)", cursor: "pointer", fontSize: "1.1rem" }}>×</button>
            </div>
          </div>
        )}

        {/* Upload zone */}
        <div style={{ marginBottom: "1.5rem" }}>
          <UploadZone onUpload={upload} uploading={uploading} />
        </div>

        {/* Documents */}
        <div style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          overflow: "hidden",
        }}>
          {/* Table header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "1rem 1.5rem",
            borderBottom: "1px solid var(--border)",
            background: "var(--surface-up)",
          }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.08em" }}>
              INDEXED POLICY DOCUMENTS
            </span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-3)" }}>
              {docs.length} file{docs.length !== 1 ? "s" : ""}
            </span>
          </div>

          {loading ? (
            <div style={{ padding: "3rem", textAlign: "center" }}>
              <span className="spinner spinner-lg" />
            </div>
          ) : docs.length === 0 ? (
            <div style={{ padding: "4rem", textAlign: "center" }}>
              <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📭</div>
              <div style={{ fontWeight: 600, marginBottom: 6 }}>No documents uploaded yet</div>
              <div style={{ fontSize: "0.82rem", color: "var(--text-3)" }}>
                Upload PDF policy files above to start indexing
              </div>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="pg-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Index Size</th>
                    <th>Conflicts</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((doc) => (
                    <DocumentRow
                      key={doc.filename}
                      doc={doc}
                      onDelete={remove}
                      deleting={deleting === doc.filename}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Info footer */}
        <div style={{
          marginTop: "1rem",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          fontSize: "0.72rem", color: "var(--text-3)",
        }}>
          <span>🔒 Documents are processed and stored locally only</span>
          <span>{chunks} total vectors in ChromaDB store</span>
        </div>
      </div>
    </Layout>
  );
}
