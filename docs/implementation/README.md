# Implementation Reference: Security Policy Assistant

This folder documents the implementation details of the Security Policy Assistant, built from the architecture defined in [`1-target-architecture.md`](../.docs/1-target-architecture.md).

## Project Structure

```
security-policy-assistant/
├── api/                        ← FastAPI backend (Query Path)
│   ├── app/
│   │   ├── core/               ← Config, Security, Telemetry
│   │   ├── models/             ← Pydantic request/response models
│   │   ├── services/           ← Search, OpenAI, RAG orchestrator
│   │   └── routers/            ← HTTP endpoints (/chat, /health)
│   ├── tests/                  ← Unit tests (pytest)
│   └── Dockerfile              ← Multi-stage production image
│
├── ingestion/                  ← Document Processing (Ingestion Path)
│   ├── shared/                 ← Chunking, Embedding, Indexing modules
│   ├── scripts/                ← CLI tools (create_index, ingest)
│   └── tests/                  ← Unit tests
│
├── infra/                      ← Terraform IaC
│   └── terraform/
│       ├── variables.tf
│       └── environments/dev/   ← Dev environment config
│
└── .github/workflows/          ← CI/CD pipelines
```

---

## Architecture → Code Mapping

This table maps each section of `1-target-architecture.md` to the implementing code:

| Architecture Section | Code Location | Description |
|---|---|---|
| §2.1 Ingestion Flow | `ingestion/shared/chunking.py` | Semantic chunking by headings |
| §2.1 Ingestion Flow | `ingestion/shared/embedding.py` | Batch embedding via Azure OpenAI |
| §2.1 Ingestion Flow | `ingestion/shared/indexing.py` | Idempotent upsert with deterministic IDs |
| §2.1 Ingestion Flow | `ingestion/scripts/ingest.py` | CLI entrypoint for document ingestion |
| §2.2 Query Flow | `api/app/services/rag.py` | Full RAG orchestrator (embed → search → prompt → generate → verify) |
| §2.2 Query Flow | `api/app/services/search.py` | Hybrid search with security trimming |
| §2.2 Query Flow | `api/app/services/openai_client.py` | Azure OpenAI wrapper (Entra ID auth) |
| §3.1 Identity Layer | `api/app/core/security.py` | EasyAuth claim extraction, user groups |
| §3.2 Application Layer | `api/app/main.py` | FastAPI app with CORS, lifespan, routers |
| §3.2 Application Layer | `api/app/routers/chat.py` | POST /chat endpoint |
| §3.4 Security Layer | `api/app/services/search.py` | OData security filter (`_build_security_filter`) |
| §5 Security Layers | `api/app/services/rag.py` | System prompt guardrails, citation verification |
| §3.5 Observability | `api/app/core/telemetry.py` | OpenTelemetry + Application Insights |
| §3.6 DevOps Layer | `api/Dockerfile` | Multi-stage Docker build |
| §3.6 DevOps Layer | `.github/workflows/ci-backend.yml` | CI pipeline (lint + test + Docker build) |
| §4 Network Topology | `infra/terraform/environments/dev/main.tf` | Terraform: Storage, Search, Key Vault, App Insights |

---

## Key Design Decisions

### 1. No API Keys — Entra ID Everywhere
All service-to-service calls use `DefaultAzureCredential`. In production, this resolves to Managed Identity. Locally, it uses `az login`. See `api/app/services/openai_client.py`.

### 2. Citation Verification as a Guardrail
The RAG orchestrator (`rag.py`) enforces that every answer must contain at least one valid `[docN]` citation. If the LLM generates an answer without citations, it's replaced with a refusal message. This prevents hallucinated answers from reaching users.

### 3. Deterministic Chunk IDs
Chunk IDs are SHA-256 hashes of `source_uri + chunk_index` (see `ingestion/shared/indexing.py`). This ensures:
- Re-running ingestion updates existing chunks instead of duplicating them.
- Deleting a source document can reliably remove all its chunks.

### 4. Security Trimming at Query Time
Security is enforced via OData filters on `allowed_groups` and `classification` fields in Azure AI Search (see `search.py::_build_security_filter`). Users can only retrieve chunks their Entra ID groups grant access to.

---

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env  # Fill in Azure resource values
python -m venv .venv && .venv\Scripts\activate  # Windows

# 2. Run the API
pip install -r api/requirements.txt
cd api && uvicorn app.main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs (Swagger UI)

# 3. Create the search index
pip install -r ingestion/requirements.txt
python ingestion/scripts/create_index.py

# 4. Ingest a document
python ingestion/scripts/ingest.py --file "./sample_policies/example.pdf"

# 5. Run tests
pip install pytest pytest-asyncio
pytest api/tests/ -v
```
