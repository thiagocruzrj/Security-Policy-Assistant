# Repository Structure: Professional & Modular

## Overview

This structure is designed for **Scalability**, **Testability**, and **Team Collaboration**. It enforces a clean separation of concerns:
*   **API:** The FastAPI backend (Query Logic).
*   **Ingestion:** The Azure Functions or scripts (Data Pipeline).
*   **Infrastructure:** Terraform/Bicep (IaC).
*   **Tests:** Pytest (Unit/Integration).
*   **Evaluation:** Prompt Flow (RAG Quality).

---

## Root Structure

```text
security-policy-assistant/
│
├── .github/                    # GitHub Action Workflows
│   ├── workflows/
│   │   ├── ci-backend.yml      # Build/Test API
│   │   ├── ci-ingest.yml       # Build/Test Ingestion
│   │   ├── cd-prod.yml         # Deploy to Azure (gate: main)
│   │   └── pr-checks.yml       # Linting & Security Scans
│
├── .vscode/                    # Editor config (extensions, launch.json)
│   ├── launch.json             # Debug configurations for FastAPI/Functions
│   └── settings.json           # Python formatting (Black/Ruff)
│
├── api/                        # The Chat Backend (Container App)
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings (ENV vars)
│   │   │   ├── security.py     # AuthX (JWT Validation)
│   │   │   └── telemetry.py    # OpenTelemetry/App Insights
│   │   ├── models/
│   │   │   ├── chat.py         # Request/Response Pydantic Models
│   │   │   └── citation.py     # Citation Data Structure
│   │   ├── services/
│   │   │   ├── search.py       # Azure AI Search Client Wrapper
│   │   │   ├── openai.py       # OpenAI Client (Chat/Embed)
│   │   │   └── rag.py          # The Core Logic (Retrieve -> Rank -> Generate)
│   │   ├── main.py             # FastAPI App Entrypoint
│   │   └── routers/            # API Route Definitions
│   ├── tests/                  # Backend Tests (pytest)
│   ├── Dockerfile              # Production Image
│   └── requirements.txt        # Backend Dependencies
│
├── ingestion/                  # The Data Pipeline (Azure Functions)
│   ├── functions/
│   │   ├── blob_trigger/       # Trigger on new PDF upload
│   │   │   ├── __init__.py     # Function Entry Point
│   │   │   └── function.json   # Bindings Configuration
│   │   ├── shared/             # Shared logic
│   │   │   ├── chunking.py     # MarkdownHeaderSplitter Implementation
│   │   │   ├── embedding.py    # OpenAI Embedding Logic
│   │   │   └── indexing.py     # Search Index Upsert Logic
│   ├── local.settings.json     # Local Dev Config (GitIgnored!)
│   └── requirements.txt        # Ingestion Dependencies
│
├── infra/                      # Infrastructure as Code
│   ├── terraform/              # Azure Resources
│   │   ├── modules/            # Reusable Modules (KeyVault, Search, storage)
│   │   ├── environments/       # Per-Env Configuration
│   │   │   ├── dev/
│   │   │   │   ├── main.tf
│   │   │   │   └── terraform.tfvars
│   │   │   └── prod/
│   │   └── variables.tf
│   └── scripts/                # Setup/Teardown Shell Scripts
│
├── evaluation/                 # RAG Quality Assurance
│   ├── golden_dataset.csv      # The Ground Truth (Q/A pairs)
│   ├── promptflow/             # Azure AI Foundry Prompt Flow
│   │   ├── flow.dag.yaml       # The Eval Logic
│   │   ├── promot.jinja2       # The System Prompt Template
│   │   └── evaluate.py         # Local runner script
│
├── docs/                       # Project Documentation
│   ├── 1-target-architecture.md
│   ├── 2-core-azure-components.md
│   ├── ... (This Documentation Series)
│   └── ADR/                    # Architecture Decision Records
│
├── .gitignore                  # Standard Python/Terraform ignores
├── .pre-commit-config.yaml     # Git Hooks (Linting/Secrets)
├── LICENSE
└── README.md                   # Project Entry Point
```

---

## Component Details

### `api/` (FastAPI)
*   **Separation:** Core logic (`services/rag.py`) is decoupled from the framework (`routers/`). This allows unit testing the RAG logic without spinning up a web server.
*   **Config:** Uses `pydantic-settings` to load environment variables safely. **No hardcoding.**
*   **Docker:** Multi-stage build to keep the final image slim (distroless/python).

### `ingestion/` (Azure Functions)
*   **Trigger:** Primarily uses `BlobTrigger`.
*   **Idempotency:** The pipeline handles re-processing specific files without duplicating chunks (using `id` hashing or explicit `delete` before `upsert`).
*   **Shared Code:** Common utilities (`chunking.py`) can potentially be moved to a shared local package if `api` and `ingestion` need identical logic, but keeping them separate usually simplifies deployment.

### `infra/` (Terraform)
*   **Modules:** Build modules for `storage_account`, `key_vault`, `ai_search`, `openai`.
*   **State:** Use an Azure Storage Account container for remote state file (`terraform.tfstate`).
*   **Environments:** Strict separation of `.tfvars` ensures `dev` and `prod` never mix.

### `evaluation/` (Prompt Flow)
*   **Golden Dataset:** The most valuable asset. A CSV of 50-100 questions with "perfect" anwers and required citation IDs.
*   **Flow:** An automated flow that:
    1.  Takes a question.
    2.  Runs the RAG logic (mocked or live).
    3.  Scores the answer using an LLM-as-a-Judge (GPT-4).

---

## Best Practices Enforced
1.  **Repo Root is Clean:** Only config files (`.gitignore`, `README`, `.env.example`) live here.
2.  **No Monolith:** Backend and Ingestion are distinct deployable units.
3.  **Config Management:** All secrets are injected via Env Vars/Key Vault references, never committed.
4.  **Docs-as-Code:** Architecture changes are PRs to the `docs/` folder.