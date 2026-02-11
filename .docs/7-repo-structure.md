# Repository Structure: Minimal but Professional

This document describes the recommended folder and file structure for the Security Policy Assistant repository. The structure is designed for clarity, modularity, and professional DevOps practices, supporting both development and production workflows.

## security-policy-assistant/
```
infra/
  terraform/            # or bicep/
    modules/
    envs/dev
    envs/stage
    envs/prod
api/
  app/
    main.py             # FastAPI entry
    auth.py             # Entra validation helpers
    rag.py              # retrieval + prompt build
    clients/
      search.py
      openai.py
  tests/
ingestion/
  function/             # Azure Functions (optional)
  chunking.py
  indexer.py
promptflow/
  flows/
  eval/
docs/
  ARCHITECTURE.md
  THREAT_MODEL.md
```

## Structure Overview
- **infra/**: Infrastructure as code (Terraform or Bicep), with modules and environment-specific configs
- **api/**: FastAPI application, authentication helpers, RAG logic, and API clients
- **ingestion/**: Azure Functions and scripts for document chunking and indexing
- **promptflow/**: Prompt orchestration flows and evaluation assets
- **docs/**: Architecture and threat model documentation

---
This structure supports scalable development, clear separation of concerns, and professional delivery for the Security Policy Assistant.