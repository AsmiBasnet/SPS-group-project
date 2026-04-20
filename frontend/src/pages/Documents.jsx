import { useState, useEffect, useRef } from "react";
import Layout from "../components/Layout";
import api from "../api";

function ConflictBadge({ conflicts }) {
  const [open, setOpen] = useState(false);
  if (!conflicts || conflicts.length === 0) return (
    <span className="tag tag-green">✅ No Conflicts</span>
  );
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button
        className="tag tag-amber"
        style={{ cursor: "pointer", border: "none", background: "rgba(245,158,11,0.15)" }}
        onClick={() => setOpen(v => !v)}
      >
        ⚠️ {conflicts.length} Conflict{conflicts.length > 1 ? "s" : ""}
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, zIndex: 100,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: 10, padding: "1rem", minWidth: 360, maxWidth: 480,
          boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          marginTop: 6,
        }}>
          <div style={{ fontSize: "0.78rem", fontWeight: 700, marginBottom: "0.5rem", color: "var(--amber)" }}>
            Detected Conflicts
          </div>
          {conflicts.map((c, i) => (
            <div key={i} style={{
              marginBottom: "0.75rem", paddingBottom: "0.75rem",
              borderBottom: i < conflicts.length - 1 ? "1px solid var(--border)" : "none",
              fontSize: "0.78rem",
            }}>
              <div style={{ color: "var(--text-muted)", marginBottom: 3 }}>
                <strong style={{ color: "var(--text)" }}>This doc:</strong> {c.new_text?.slice(0, 120)}…
              </div>
              <div style={{ color: "var(--text-muted)" }}>
                <strong style={{ color: "var(--text)" }}>Conflicts with</strong> {c.existing_src} p{c.existing_page}:{" "}
                {c.existing_text?.slice(0, 120)}…
              </div>
              {c.reason && (
                <div style={{ marginTop: 4, padding: "0.3rem 0.5rem", background: "rgba(245,158,11,0.08)", borderRadius: 5, color: "var(--amber)" }}>
                  {c.reason}
                </div>
              )}
            </div>
          ))}
          <button className="btn-ghost" style={{ fontSize: "0.75rem", marginTop: 4 }} onClick={() => setOpen(false)}>
            Close
          </button>
        </div>
      )}
    </div>
  );
}

export default function Documents() {
  const [docs, setDocs]           = useState([]);
  const [isReady, setIsReady]     = useState(false);
  const [chunks, setChunks]       = useState(0);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting]   = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(true);
  const fileRef = useRef(null);

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

  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setError("");
    setUploadResult(null);
    setUploading(true);
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
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const remove = async (filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    setDeleting(filename);
    try {
      await api.delete(`/api/documents/${encodeURIComponent(filename)}`);
      setDocs(prev => prev.filter(d => d.filename !== filename));
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <Layout>
      <div style={{ maxWidth: 900, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Document Manager</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 2 }}>
              Upload and manage policy PDF files
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <span className={`tag ${isReady ? "tag-green" : "tag-amber"}`}>
              {isReady ? `✅ ${chunks} chunks indexed` : "⏳ No documents loaded"}
            </span>
            <button
              className="btn-primary"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              {uploading
                ? <><span className="spinner" style={{ marginRight: 8 }} /> Indexing…</>
                : "⬆ Upload PDF"
              }
            </button>
            <input
              ref={fileRef} type="file" accept=".pdf"
              style={{ display: "none" }} onChange={upload}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 10, padding: "0.75rem 1rem", fontSize: "0.85rem",
            color: "var(--red)", marginBottom: "1rem",
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* Upload result */}
        {uploadResult && (
          <div className="fade-in card" style={{
            background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.25)",
            marginBottom: "1.25rem",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--green)" }}>
                  ✅ {uploadResult.filename} indexed successfully
                </div>
                <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                  Version {uploadResult.version} · {uploadResult.chunks} chunks created
                </div>
              </div>
              <ConflictBadge conflicts={uploadResult.conflicts} />
            </div>
          </div>
        )}

        {/* Upload area (drop zone look) */}
        <div
          className="card"
          style={{
            border: "2px dashed var(--border)", background: "transparent",
            textAlign: "center", padding: "2rem", marginBottom: "1.5rem",
            cursor: "pointer", transition: "border-color 0.2s",
          }}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f) { const dt = new DataTransfer(); dt.items.add(f); fileRef.current.files = dt.files; upload({ target: { files: [f] } }); }
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📤</div>
          <div style={{ fontSize: "0.9rem", fontWeight: 600 }}>
            {uploading ? "Indexing document…" : "Click or drag & drop PDF"}
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 4 }}>
            PDF files only · Documents are processed locally with nomic-embed-text
          </div>
        </div>

        {/* Documents table */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
            <span className="spinner" />
          </div>
        ) : docs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
            <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📭</div>
            <div>No policy documents uploaded yet.</div>
            <div style={{ fontSize: "0.8rem", marginTop: 4 }}>Upload a PDF to get started.</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface2)" }}>
                  {["File", "Chunks", "Status", "Actions"].map(h => (
                    <th key={h} style={{
                      textAlign: "left", padding: "0.75rem 1rem",
                      fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {docs.map((doc, i) => (
                  <tr key={doc.filename} style={{
                    borderBottom: i < docs.length - 1 ? "1px solid var(--border)" : "none",
                    transition: "background 0.1s",
                  }}>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: "1.2rem" }}>📄</span>
                        <div>
                          <div style={{ fontWeight: 600 }}>{doc.filename}</div>
                          {doc.path && (
                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                              {doc.path}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: "0.85rem 1rem", color: "var(--text-muted)" }}>
                      {doc.chunks}
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <span className="tag tag-green">Active</span>
                    </td>
                    <td style={{ padding: "0.85rem 1rem" }}>
                      <button
                        className="btn-danger"
                        style={{ padding: "0.35rem 0.75rem", fontSize: "0.78rem" }}
                        disabled={deleting === doc.filename}
                        onClick={() => remove(doc.filename)}
                      >
                        {deleting === doc.filename ? <span className="spinner" /> : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: "1rem", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "right" }}>
          {docs.length} document{docs.length !== 1 ? "s" : ""} · {chunks} total chunks in vector store
        </div>
      </div>
    </Layout>
  );
}
