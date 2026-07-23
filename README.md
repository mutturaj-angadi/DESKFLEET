# DeskFleet

**AI Multi-Agent Customer Support System** — a LangGraph crew (Classifier → Researcher →
Responder → Reviewer) that resolves support tickets end-to-end against an order/product API,
with every decision, tool call, and per-node latency traceable in LangSmith. Deployed behind
FastAPI, with a Streamlit operator dashboard, Prometheus/Grafana observability, and a
GitHub Actions CI/CD pipeline to Cloud Run.

Built as the C·04 capstone project (Multi-Agent Systems track, IITR-SE-2509 Cohort C).

---

## Architecture

```
POST /resolve
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ input_guardrail  — regex injection scan + PII redaction          │
│   │                                                               │
│   ├─ injection detected → decision = REFUSE → END                │
│   │                                                               │
│   ▼                                                               │
│ classifier   — LLM call, structured output → category            │
│   ▼                                                               │
│ researcher   — tool-calling agent, allowlisted tools only         │
│   ▼                                                               │
│ responder    — drafts a reply grounded only in gathered facts     │
│   ▼                                                               │
│ reviewer     — approve / retry / escalate                         │
│   │     ▲                                                         │
│   │     └── retry (iterations < MAX)  ──────────► responder       │
│   │                                                               │
│   ├─ approve            → decision = RESOLVED                     │
│   └─ escalate / max-iterations hit → decision = ESCALATE          │
│   ▼                                                               │
│ output_guardrail — PII redaction on the outbound reply            │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
persist to SQLite + Prometheus metrics + LangSmith trace URL
```

**Design decisions worth knowing:**

- **The tool registry *is* the allowlist.** `app/tools/registry.py` holds the only mapping
  from tool name → callable. Anything the model asks for outside that dict is rejected and
  logged as `status: "blocked"` — it never executes.
- **The max-iteration guard lives in code, not in a prompt.** `reviewer_node` forces
  `ESCALATE` once `iterations >= MAX_REVIEWER_ITERATIONS`, regardless of what the LLM says.
  This is what makes the loop provably bounded.
- **Guardrails are graph nodes, not side functions**, so injection scoring and PII redaction
  show up as their own steps in the LangSmith trace.
- **The mock API is deliberately not the public FakeStoreAPI** — it's a small FastAPI service
  with fixed fixtures, so agent behavior is reproducible in dev, tests, and CI.

## Project structure

```
deskfleet/
├── app/
│   ├── graph/
│   │   ├── state.py       # TicketState TypedDict
│   │   ├── nodes.py        # classifier, researcher, responder, reviewer
│   │   ├── edges.py        # conditional routing functions
│   │   ├── workflow.py     # StateGraph assembly + guardrail nodes
│   │   └── llm.py          # OpenAI client wrapper (the test-mocking seam)
│   ├── tools/
│   │   ├── order.py, product.py, search.py
│   │   └── registry.py     # the tool allowlist
│   ├── guardrails/
│   │   ├── injection.py    # regex prompt-injection scoring
│   │   └── pii.py          # regex PII redaction
│   ├── database/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── db.py           # session + persistence helpers
│   ├── routers/
│   │   ├── tickets.py      # /resolve /ticket /tickets /feedback /trace
│   │   └── schemas.py
│   ├── metrics/
│   │   ├── prometheus.py
│   │   └── cost.py         # tiktoken-based cost estimation
│   ├── config.py
│   └── main.py              # FastAPI app, /health, /metrics
├── mock_api/main.py          # fixture-backed order/product API
├── frontend/
│   ├── streamlit_app.py       # AI Operations Console (dashboard/resolve/history/analytics/settings)
│   └── components/            # header, sidebar, metrics, pipeline, result_card, history,
│                               # analytics, loading, styles — presentation wiring only,
│                               # resolve_ticket()/fetch_tickets() API contract untouched
├── tests/                    # 40 tests: agents, tools, guardrails, api, database, integration
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── grafana/provisioning/
├── .github/workflows/ci.yml
└── requirements.txt
```

## Installation & local setup

Requires Python 3.12+.

```bash
git clone <your-repo-url> deskfleet
cd deskfleet
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in LLM_API_KEY (your Gemini key) at minimum
```

Run the three services in separate terminals:

```bash
# 1. Mock order/product API
uvicorn mock_api.main:app --port 9000 --reload

# 2. FastAPI backend
uvicorn app.main:app --port 8000 --reload

# 3. Streamlit dashboard
streamlit run frontend/streamlit_app.py
```

Visit `http://localhost:8501` for the dashboard, or hit the API directly:

```bash
curl -X POST http://localhost:8000/resolve \
  -H "Content-Type: application/json" \
  -d '{"ticket": "Where is my order ORD-5001? It has not arrived.", "order_id": "ORD-5001"}'
```

## Environment variables

See `.env.example` for the full list. The only one you must set is `LLM_API_KEY`.
DeskFleet talks to the LLM through the OpenAI SDK pointed at an OpenAI-compatible
endpoint — it defaults to **Gemini's** OpenAI-compatible endpoint
(`LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`,
`OPENAI_MODEL=gemini-2.0-flash`). To use real OpenAI instead, set `LLM_PROVIDER=openai`,
clear `LLM_BASE_URL`, and set `LLM_API_KEY` to an OpenAI key.
`LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` enable LangSmith tracing (recommended —
this is the graph's "glass box" story).

## Running tests

```bash
pytest tests/ -v
```

40 tests across agent logic, tool allowlist enforcement, guardrails, the FastAPI layer,
SQLite persistence, and a full end-to-end graph run (mocked LLM + mocked tools).

## Docker

```bash
cd deployment
export LLM_API_KEY=your-gemini-api-key
docker compose up --build
```

This brings up: mock API (`:9000`), FastAPI backend (`:8000`), Streamlit (`:8501`),
Prometheus (`:9090`), and Grafana (`:3000`, anonymous admin access, dashboard
auto-provisioned as "DeskFleet Overview").

## Cloud Run deployment

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build & push
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/deskfleet/deskfleet:latest \
  -f deployment/Dockerfile .

# Deploy
gcloud run deploy deskfleet-api \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/deskfleet/deskfleet:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars LLM_API_KEY=your-gemini-api-key,LANGCHAIN_API_KEY=your-langsmith-key,LANGCHAIN_TRACING_V2=true,MOCK_API_BASE_URL=https://your-mock-api-url
```

Note: Cloud Run's local filesystem is ephemeral — `DATABASE_PATH` data is wiped on
container restart/scale-out. For a persistent deployment, point `DATABASE_PATH` at a
Cloud SQL-backed connection or mount a GCS-backed volume.

## GitHub Actions CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. `black --check` + `isort --check-only`
2. `pytest tests/ -v`
3. On `main` only: Docker build → push to Artifact Registry → `gcloud run deploy`

Required repo secrets: `GCP_SA_KEY`, `GCP_PROJECT_ID`, `LLM_API_KEY`, `LANGCHAIN_API_KEY`, `MOCK_API_BASE_URL`.

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/resolve` | Run the full agent graph on a ticket |
| GET | `/health` | Liveness check |
| GET | `/metrics` | Prometheus scrape endpoint |
| GET | `/ticket/{id}` | Fetch a stored ticket record |
| GET | `/tickets` | List recent tickets |
| POST | `/feedback` | Submit human feedback on a resolved/escalated ticket |
| GET | `/trace/{id}` | LangSmith trace URL for a ticket |

## Screenshots

*(placeholder — add screenshots of the Streamlit dashboard, a LangSmith trace view, and the
Grafana dashboard here before submitting)*

## Known limitations

- The injection/PII guardrails are regex-based — a determined adversary using enough
  paraphrasing could evade the injection detector, and rare PII formats (non-US phone
  numbers, non-SSN government IDs) aren't covered.
- SQLite is fine for a single-instance deployment; it is not safe for multi-replica Cloud
  Run without moving to a networked database.
- Cost/token metrics (`app/metrics/cost.py`) are an *estimate* based on prompt text length,
  not the model's actual reported `usage` — swap in `completion.usage` for exact accounting.

## Future improvements

- Stream the agent loop to the frontend via Server-Sent Events instead of a single blocking
  `/resolve` call.
- Add a semantic (embedding-based) guardrail alongside the regex injection detector.
- Express the same graph as a CrewAI role/task crew as a documented architecture comparison.
- Multi-replica deployment with a networked database (Cloud SQL / Postgres) instead of SQLite.
