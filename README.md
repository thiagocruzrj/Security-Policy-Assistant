# Security Policy Assistant

An enterprise-grade **Retrieval-Augmented Generation (RAG)** solution that enables employees to query internal security policies using natural language. Built on Azure with a Zero-Trust architecture.

## Architecture

```
User → Static Web App → APIM → FastAPI (Container Apps) → Azure AI Search + Azure OpenAI
```

Key capabilities:
- **Hybrid retrieval** — BM25 keyword + HNSW vector + Semantic Reranking
- **Security trimming** — Document-level access control via Entra ID group claims
- **Grounded answers** — Strict citation enforcement; refuses to answer from outside knowledge
- **Full observability** — End-to-end distributed tracing via Application Insights

## Project Structure

```
api/            → FastAPI backend (query path)
ingestion/      → Document processing pipeline (chunking, embedding, indexing)
infra/          → Terraform modules for Azure resources
evaluation/     → RAG quality evaluation (golden dataset, Prompt Flow)
.docs/          → Architecture & design documentation
.github/        → CI/CD workflows
```

## Quick Start

```bash
# 1. Clone and set up environment
git clone <repo-url> && cd security-policy-assistant
cp .env.example .env              # Fill in your Azure resource values
python -m venv .venv && source .venv/bin/activate

# 2. Install API dependencies
pip install -r api/requirements.txt

# 3. Run the API locally
cd api && uvicorn app.main:app --reload

# 4. Ingest a document
pip install -r ingestion/requirements.txt
python ingestion/scripts/ingest.py --file "./sample_policies/example.pdf"
```

## Documentation

See [`.docs/`](.docs/) for the full architecture series:
1. [Target Architecture](.docs/1-target-architecture.md)
2. [Core Azure Components](.docs/2-core-azure-components.md)
3. [Security & Compliance Stages](.docs/3-security-compliance-stages.md)
4. [Production Readiness](.docs/4-production-readiness-stages.md)
5. [RAG Quality Stages](.docs/5-rag-quality-stages.md)
6. [Demo & Next Steps](.docs/6-demo-next-steps.md)

## License

MIT
