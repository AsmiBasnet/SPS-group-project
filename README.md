# PolicyGuard

A local, privacy-preserving RAG assistant that answers employee questions about HR and compliance policies (FMLA, ADA, sick leave, harassment, absenteeism) and **refuses to guess** when the evidence is weak or the policies contradict each other.

All inference runs on-device through [Ollama](https://ollama.com), so no policy text leaves the machine.

## Key features

- **Grounded answers with citations.** Every answer must cite a section or page from the retrieved policy text. Answers without a citation are rejected.
- **Three decisions, not one.** The model returns `ANSWER`, `CLARIFY` (asks a follow-up when the employee type or situation is ambiguous), or `FLAG_CONFLICT` (quotes the two clauses that disagree).
- **Two-stage guardrails.** Retrieval is refused if the best similarity score is below the threshold, and model output is validated for a citation before it is shown.
- **Multi-turn memory.** The session tracks employee type, issue category, cited clauses and chat history across turns.
- **Proactive conflict scanner.** Newly uploaded documents are scanned against the existing library for contradictions.
- **Policy Health Score (0-100).** Combines coverage (gap detection), freshness (documents older than a year are penalised) and consistency (conflict count).
- **Gap detection.** Flags standard HR topics missing from the policy library.
- **Versioning and audit reports.** Document versions are tracked, and a PDF audit report can be exported.
- **Role-based access.** Policy Admin (upload and full dashboard), HR Manager (chat and read-only dashboard), Employee (chat only), plus an anonymous employee mode.

## Architecture

```
PDF policies -> ingestion.py (PyMuPDF, chunking)
             -> retriever.py (Ollama embeddings -> ChromaDB, persistent)
question     -> pipeline.py -> retrieve top-k chunks
                            -> guardrails.py (evidence strength)
                            -> reasoning.py (Ollama LLM, JSON decision)
                            -> guardrails.py (citation check, confidence)
                            -> database.py (SQLite query/document log)
```

| Module | Purpose |
|---|---|
| `src/pipeline.py` | Orchestrates the whole flow and holds session state |
| `src/ingestion.py` | PDF reading and chunking |
| `src/retriever.py` | Embeddings and ChromaDB vector search |
| `src/reasoning.py` | Prompting, JSON parsing and retries |
| `src/guardrails.py` | Evidence, citation and confidence checks |
| `src/conflict_scanner.py` | Cross-document contradiction scan on upload |
| `src/gap_detector.py` | Missing-topic detection |
| `src/health_score.py` | Policy Health Score |
| `src/report.py` | PDF audit report |
| `src/database.py` | SQLite logging, analytics and document versions |
| `src/config.py` | Settings, loaded from `.env` |

There are two front ends over the same pipeline:

- **Streamlit app** (`app.py`), the original UI.
- **React + FastAPI app** (`frontend/` and `backend/`), with a dark glassmorphism UI.

## Prerequisites

- Python 3.12
- [Ollama](https://ollama.com) running locally, with the models pulled:
  ```bash
  ollama pull qwen3.5:4b
  ollama pull nomic-embed-text
  ```
- Node.js 18+ (React front end only)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root. Every value is optional and the defaults are shown:

```env
OLLAMA_URL=http://localhost:11434
MODEL_NAME=qwen3.5:4b
EMBED_MODEL=nomic-embed-text
DB_PATH=logs/policygard.db
POLICIES_FOLDER=policies

POLICY_ADMIN_USER=policy_admin
POLICY_ADMIN_PASS=admin123
HR_MANAGER_USER=hr_manager
HR_MANAGER_PASS=hr123
EMPLOYEE_USER=employee
EMPLOYEE_PASS=emp123

NGROK_AUTH_TOKEN=        # only needed for share.py
```

> The default passwords are for local demos only. Change them before exposing the app anywhere.

Put policy PDFs in the `policies/` folder to have them loaded automatically, or upload them as a Policy Admin. Sample PDFs are in `data/`.

## Running

### Option A: Streamlit app

```bash
streamlit run app.py
```

Open http://localhost:8501.

### Option B: React + FastAPI

Use three terminals, started in this order.

1. Ollama (skip if the Ollama app is already running):
   ```bash
   ollama serve
   ```

2. Backend, from the project root with the virtual environment active:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   Wait for `Uvicorn running on http://127.0.0.1:8000`. You can check it with `curl http://localhost:8000/api/health`.

3. Front end:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Open http://localhost:3000. The front end calls the API at `http://localhost:8000`, which must be running first.

### Docker (Streamlit app)

```bash
docker compose up --build
```

The container expects Ollama running on the host and reaches it at `host.docker.internal:11434`.

### Share a demo publicly

```bash
python share.py
```

Opens an ngrok tunnel to `localhost:8501`.

## API (FastAPI backend)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/login` | Returns a JWT and the user's role |
| POST | `/api/ask` | Ask a policy question |
| GET | `/api/documents` | List active documents |
| POST | `/api/documents/upload` | Upload and index a PDF |
| DELETE | `/api/documents/{filename}` | Remove a document |
| GET | `/api/dashboard` | Analytics and health score |
| GET | `/api/report` | Download the PDF audit report |
| GET | `/api/health` | Service health check |

All endpoints except login and health require a bearer token.

## Evaluation

`eval/benchmark.csv` holds benchmark questions with the expected decision and whether a conflict is expected. Run:

```bash
pip install scikit-learn
python evaluate.py
```

Results are written to `eval/results.md`. Early development notes and latency measurements are in `logs/experiment_results.md`.

## Troubleshooting

- **`incompatible architecture (have 'x86_64', need 'arm64')` on startup.** The virtual environment (or `frontend/node_modules`) was created on a Mac with a different chip. Don't copy these folders between Intel and Apple-silicon Macs. Delete `venv/` and `frontend/node_modules/` and reinstall (`python3 -m venv venv && pip install -r requirements.txt`, then `npm install` in `frontend/`).
- **Wrong packages are loaded even with the venv active.** Run `which uvicorn`. It should point inside this project's `venv/`. If not, start the server with `python -m uvicorn backend.main:app --port 8000` from the activated venv.
- **Every question fails or the app can't answer.** Check that Ollama is running (`curl http://localhost:11434`) and that both models are pulled (`ollama list` should show `qwen3.5:4b` and `nomic-embed-text`).
- **The first answer is very slow.** Ollama is loading the model into memory. Later answers are faster. On CPU-only machines expect tens of seconds per answer.
- **The front end loads but login fails.** The backend isn't running on port 8000. Check `curl http://localhost:8000/api/health`.

## Project structure

```
app.py              Streamlit app
backend/            FastAPI API (auth, models, routes)
frontend/           React (Vite) app
src/                Core RAG pipeline
data/               Sample policy PDFs
eval/               Benchmark questions
logs/               SQLite DB, vector index, experiment log
```

## Authors

IT group project by **Utsav Khadka** and **Asmi Basnet**.

- Utsav Khadka: core RAG pipeline, guardrails, role-based access, conflict scanner, health score, versioning, Docker and sharing setup, and the React + FastAPI front end.
- Asmi Basnet: multi-turn conversational memory and the database and reasoning updates.
