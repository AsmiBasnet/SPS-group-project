# PolicyGuard

An HR policy chatbot built in five progressive AI engineering phases — from a basic RAG pipeline to a fully evaluated, production-grade system with agentic self-healing, hybrid search, long-term memory, knowledge graph retrieval, and automated evaluation.

All inference runs locally through [Ollama](https://ollama.com). No policy text, no questions, and no answers leave the machine.

---

## What it does

PolicyGuard answers employee questions about HR and compliance policies — FMLA leave, ADA accommodations, sick leave, harassment, absenteeism — and **refuses to guess** when the evidence is weak or when two policies contradict each other.

Instead of a single "here's your answer" response, the system returns one of three decisions:

- **`ANSWER`** — a grounded response with a citation to the specific policy section
- **`CLARIFY`** — a follow-up question when the employee type or situation is ambiguous
- **`FLAG_CONFLICT`** — quotes the two clauses that disagree so HR can resolve them

Every answer requires a citation. If the LLM produces a response without one, it gets rejected.

---

## Five-Phase Architecture

The project was built incrementally. Each phase added a new capability on top of the previous one — nothing was thrown away.

```
Phase 1  →  Agentic RAG with LangGraph (self-healing retrieval)
Phase 2  →  Hybrid Search (BM25 + vector + cross-encoder reranking)
Phase 3  →  Long-Term Memory (mem0 + Qdrant, persisted per user)
Phase 4  →  Knowledge Graph (GraphRAG, 1-hop entity expansion)
Phase 5  →  Evaluation Pipeline (RAGAS-equivalent metrics, local LLM judge)
```

### Phase 1 — Agentic RAG with LangGraph

**Problem with basic RAG:** A single retrieval attempt either finds good chunks or it doesn't. If the question is phrased in a way that doesn't match the policy text, there's no recovery mechanism — the pipeline just returns a weak answer.

**What we built:** A LangGraph `StateGraph` that turns retrieval into a loop. The agent retrieves chunks, grades them, rewrites the question if they're poor, retrieves again, generates an answer, grades the answer, and regenerates if needed. Maximum two retries at each stage.

```
retrieve → grade_chunks
                ├─ good  → generate → grade_answer
                │                          ├─ grounded     → END
                │                          └─ not_grounded → generate (retry)
                └─ poor  → rewrite_question → retrieve (retry)
```

The `grade_chunks` node uses a simple similarity threshold — no extra LLM call needed. The `grade_answer` node accepts `ANSWER`, `CLARIFY`, and `FLAG_CONFLICT` as valid final decisions, so the agent doesn't retry a correct clarification.

**Key files:** [`src/agentic_rag.py`](src/agentic_rag.py)

---

### Phase 2 — Hybrid Search with BM25 + Cross-Encoder Reranking

**Problem with vector-only search:** Semantic embeddings are great for conceptual similarity but can miss exact keyword matches. A question like "what does Section 2.0 say about eligibility" should find chunks that literally contain "Section 2.0", not just chunks about eligibility.

**What we built:** A hybrid retrieval function that runs vector search and BM25 keyword search in parallel, merges the results with RRF (Reciprocal Rank Fusion), then reranks the combined pool using a cross-encoder model. The cross-encoder reads the question and each candidate chunk together — not independently — which produces much more accurate relevance scores.

```
question
    ├── vector search (ChromaDB embeddings)     → top-K chunks
    └── BM25 keyword search (rank_bm25)         → top-K chunks
                    ↓
            RRF merge (deduplicate + fuse ranks)
                    ↓
        cross-encoder reranking (ms-marco-MiniLM)
                    ↓
            top-K final chunks → Phase 1 agent
```

**Key files:** [`src/hybrid_retriever.py`](src/hybrid_retriever.py)

---

### Phase 3 — Long-Term Memory with mem0

**Problem with session-only memory:** Every time a user starts a new chat, the pipeline loses everything it learned about them — their employee type, the policies they already asked about, their situation. Each conversation starts from zero.

**What we built:** A mem0 integration that saves every Q&A exchange to a local Qdrant vector store on disk. When a user asks a new question, the system retrieves the most relevant past memories and injects them into the LangGraph session context. The LLM extracts the important facts from each exchange (not just stores the raw text), so the memories stay compact and relevant.

```
ask() ──► get_memories(user_id, question)   # inject past context
       ──► agentic_ask(...)                 # run pipeline
       ──► save_memory(user_id, q, answer)  # persist this exchange
```

Memories survive server restarts because Qdrant stores them on disk at `logs/mem0_qdrant/`. The LLM used for extraction is the same local qwen2.5:7b model — no external API calls.

**Key files:** [`src/memory_manager.py`](src/memory_manager.py)

---

### Phase 4 — Knowledge Graph with GraphRAG

**Problem with flat retrieval:** Even the best vector search treats chunks as independent documents. It can find the chunk about "12-week FMLA entitlement" but won't automatically bring in the "eligibility criteria" chunk — even though they're deeply connected. You need to know both to answer most FMLA questions.

**What we built:** At document load time, we extract (subject, relation, object) triples from every chunk using the LLM — for example, `("contractor", "not eligible for", "FMLA")` — and build a NetworkX directed graph. Nodes are entities; edges are relationships.

At query time, after hybrid search returns its initial chunks, we:
1. Find which graph nodes are mentioned in those chunks (seed nodes)
2. Walk one hop — outgoing and incoming edges both
3. Collect the chunks associated with those neighbor nodes
4. Add them to the pool and rerank everything

The reranker ensures the LLM only sees the best chunks from the expanded pool — not all 30+ — so there's no token bloat.

```
hybrid search → initial chunks
                    ↓
            find seed nodes in graph
                    ↓
            1-hop traversal (neighbors + predecessors)
                    ↓
            collect neighbor chunks
                    ↓
            rerank(initial + expanded, top_k)
                    ↓
                final chunks → generate node
```

**Key files:** [`src/knowledge_graph.py`](src/knowledge_graph.py)

---

### Phase 5 — RAGAS Evaluation Pipeline

**Problem:** With four phases of improvements, we had no objective way to measure whether the system was actually getting better — or how good it was overall.

**What we built:** An evaluation pipeline that scores the pipeline on three RAGAS-equivalent metrics across a 5-question ground-truth test set:

| Metric | What it measures |
|---|---|
| **Faithfulness** | Are the answer's claims supported by the retrieved contexts? |
| **Context Precision** | Are the retrieved chunks actually relevant to the question? |
| **Context Recall** | Do the retrieved chunks cover what the reference answer says? |

**Why not the official RAGAS library?** We tried it. RAGAS 0.4.4 uses `instructor` to extract structured NLI claims via JSON schemas. With qwen2.5:7b, this raises `IncompleteOutputException` — the 7B model truncates before closing the JSON. The deeper issue is that qwen2.5:7b runs in thinking mode by default: all its output goes to the `thinking` field in Ollama's response, leaving `response` empty. The official library doesn't know about this.

The fix: bypass RAGAS entirely and call Ollama directly with `"think": False`. We prompt the model in plain English to return a single `{"score": 0.9}` JSON object for each metric — simpler schema, fully reliable output.

**Key files:** [`src/ragas_eval.py`](src/ragas_eval.py)

---

## Evaluation Results

Tested on 5 HR policy questions covering FMLA eligibility, contractor status, sick leave, advance notice, and leave duration.

| Q | Question | Faith | Prec | Recall | Decision |
|---|---|---|---|---|---|
| Q1 | How many weeks of FMLA leave? | 1.000 | 0.500 | 0.500 | ANSWER |
| Q2 | What are FMLA eligibility requirements? | 1.000 | 1.000 | 0.830 | ANSWER |
| Q3 | Can contractors take FMLA leave? | 0.000 | 0.000 | 0.000 | **CLARIFY** |
| Q4 | What happens to accrued sick leave? | 0.500 | 0.500 | 0.000 | ANSWER |
| Q5 | How much advance notice for FMLA? | 1.000 | 1.000 | 1.000 | ANSWER |

| Metric | Score |
|---|---|
| Faithfulness | 0.700 |
| Context Precision | 0.600 |
| Context Recall | 0.466 |
| **Overall** | **0.589 — FAIL** |

**Reading these results honestly:**

Q3 returns `CLARIFY` because the pipeline wasn't confident enough to answer — which is the correct behavior for an ambiguous question. But RAGAS penalizes `CLARIFY` decisions because the answer field is empty, dragging all three metrics to 0.0 for that row.

Excluding Q3, the system scores **~0.736 (MARGINAL)** — reasonable for a local 7B model running entirely on-device with no cloud APIs.

The low recall on Q4 is a real gap: the chunk covering concurrent sick leave exhaustion isn't being retrieved consistently, even after graph expansion.

**Production upgrade path:** Replace the direct Ollama scoring with RAGAS Collections API backed by `gpt-4o-mini` or `claude-haiku`. They handle the complex NLI schemas reliably and produce academically rigorous scores. One line change in `_score_one()`.

---

## Full Module Map

| File | Phase | Purpose |
|---|---|---|
| `src/pipeline.py` | All | Master orchestrator — wires all phases together |
| `src/ingestion.py` | Pre-1 | PDF reading (PyMuPDF) and chunk splitting |
| `src/retriever.py` | Pre-1 | Ollama embeddings → ChromaDB vector index |
| `src/reasoning.py` | Pre-1 | LLM prompting, JSON parsing, retry logic |
| `src/guardrails.py` | Pre-1 | Evidence strength, citation check, confidence |
| `src/agentic_rag.py` | 1 | LangGraph self-healing retrieval loop |
| `src/hybrid_retriever.py` | 2 | BM25 + vector fusion + cross-encoder rerank |
| `src/memory_manager.py` | 3 | mem0 long-term memory via local Qdrant |
| `src/knowledge_graph.py` | 4 | Triple extraction, NetworkX graph, 1-hop expand |
| `src/ragas_eval.py` | 5 | RAGAS-equivalent evaluation pipeline |
| `src/conflict_scanner.py` | Pre-1 | Cross-document contradiction detection |
| `src/gap_detector.py` | Pre-1 | Missing HR topic detection |
| `src/health_score.py` | Pre-1 | Policy Health Score (0-100) |
| `src/database.py` | Pre-1 | SQLite query/document logging and analytics |
| `src/config.py` | All | Settings from `.env` |

There are two frontends over the same `pipeline.py`:

- **Streamlit** (`app.py`) — the original single-file UI
- **React + FastAPI** (`frontend/` + `backend/`) — dark glassmorphism UI with JWT auth and role-based access

---

## Setup

### Prerequisites

- Python 3.12
- [Ollama](https://ollama.com) running locally with these models pulled:

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

- Node.js 18+ (React frontend only)

### Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (all values are optional — defaults shown):

```env
OLLAMA_URL=http://localhost:11434
MODEL_NAME=qwen2.5:7b
EMBED_MODEL=nomic-embed-text
DB_PATH=logs/policygard.db
POLICIES_FOLDER=policies

POLICY_ADMIN_USER=policy_admin
POLICY_ADMIN_PASS=admin123
HR_MANAGER_USER=hr_manager
HR_MANAGER_PASS=hr123
EMPLOYEE_USER=employee
EMPLOYEE_PASS=emp123
```

> The default passwords are for local demos only. Change them before sharing the app.

---

## Running

### Option A — Streamlit (quickest start)

```bash
streamlit run app.py
```

Open http://localhost:8501.

### Option B — React + FastAPI

Three terminals, in this order:

**Terminal 1 — Ollama** (skip if already running):
```bash
ollama serve
```

**Terminal 2 — Backend** (from project root, venv active):
```bash
uvicorn backend.main:app --reload --port 8000
```

Wait for `Uvicorn running on http://127.0.0.1:8000`, then:

**Terminal 3 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Option C — Docker (Streamlit)

```bash
docker compose up --build
```

The container reaches Ollama on the host at `host.docker.internal:11434`.

---

## Running the Evaluation

```bash
python -c "
from src.pipeline import PolicyGuardPipeline
from src.ragas_eval import run_evaluation
pipeline = PolicyGuardPipeline()
run_evaluation(pipeline)
"
```

This runs all 5 test questions through the full Phase 1–4 pipeline, scores them on the three RAGAS metrics, and prints the report. Takes about 8–10 minutes on a local machine — the pipeline runs the LLM once per question for retrieval + generation, then three more times per question for scoring.

---

## API Reference (FastAPI backend)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/login` | Returns a JWT and the user's role |
| POST | `/api/ask` | Ask a policy question |
| GET | `/api/documents` | List active documents |
| POST | `/api/documents/upload` | Upload and index a PDF |
| DELETE | `/api/documents/{filename}` | Remove a document |
| GET | `/api/dashboard` | Analytics and health score |
| GET | `/api/report` | Download the PDF audit report |
| GET | `/api/health` | Health check |

All endpoints except `/api/login` and `/api/health` require a Bearer token from the login response.

---

## Troubleshooting

**`incompatible architecture (have 'x86_64', need 'arm64')` on startup.**
The virtualenv was built on the wrong chip. Delete `venv/` and `frontend/node_modules/` and reinstall from scratch.

**Every question returns `CLARIFY` or `ERROR`.**
Check that Ollama is running (`curl http://localhost:11434`) and both models are pulled (`ollama list`).

**The first answer is very slow.**
Ollama is loading the model into RAM. Second and later answers are faster. On CPU-only machines, expect 30–60 seconds per answer.

**Frontend loads but login fails.**
The backend isn't on port 8000. Check `curl http://localhost:8000/api/health`.

**RAGAS evaluation returns all `nan` scores.**
The model is likely running in thinking mode. Make sure `"think": False` is set in the Ollama request options (it already is in the current code). If you switch models, check whether the new model has a thinking mode and add the flag if needed.

---

## Project Structure

```
app.py                  Streamlit app
backend/                FastAPI API (auth, routes, models)
frontend/               React + Vite app
src/                    Core RAG pipeline (all 5 phases)
data/                   Sample policy PDFs
eval/                   Benchmark questions and results
logs/                   SQLite DB, ChromaDB index, Qdrant memory store
policies/               PDF policies loaded at startup
```

---

## Authors

IT group project by **Utsav Khadka** and **Asmi Basnet**.

- **Utsav Khadka** — core RAG pipeline, all five AI engineering phases, guardrails, role-based access, conflict scanner, health score, versioning, Docker, React + FastAPI frontend
- **Asmi Basnet** — multi-turn conversational memory, database layer, reasoning updates
