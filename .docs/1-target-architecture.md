# Target Architecture for Security Policy Assistant

## Introduction & Objectives

The **Security Policy Assistant** is an enterprise-grade Retrieval-Augmented Generation (RAG) solution that enables employees to query internal security policies using natural language. It retrieves relevant policy excerpts from a curated corpus, grounds its answers exclusively in those excerpts, and returns cited, auditable responses.

### Primary Objectives

| # | Objective | How the Architecture Addresses It |
|---|-----------|-----------------------------------|
| 1 | **Identity-first access** | Microsoft Entra ID (OIDC/OAuth 2.0) for user authentication; group-based RBAC for authorization; Managed Identity for service-to-service calls—no static keys. |
| 2 | **Data boundary enforcement** | VNet integration, Private Endpoints, and Private DNS zones ensure all traffic between services stays on the Microsoft backbone. Azure AI Search security filters enforce document-level access control per user group. |
| 3 | **Auditability & compliance** | Every request step (auth → retrieval → prompt build → LLM generation → response) is traced via Application Insights. Audit metadata (who queried what, retrieval IDs, citations, latency, token usage) is logged—raw prompt/context content is hashed by default to prevent data leakage in logs. |
| 4 | **Grounded, policy-only answers** | The LLM system prompt enforces strict "answer only from retrieved policy excerpts" behavior. A post-generation citation check refuses to return answers if no citations can be verified. |
| 5 | **Continuous improvement** | Evaluation datasets, Foundry Prompt Flow metrics, and user feedback loops drive iterative improvements to chunking, retrieval parameters, and prompt engineering. |

---

## 1. Architectural Principles

The design follows five guiding principles that inform every component decision:

1. **Zero-Trust Networking** — Every service endpoint is private. The only public ingress point is Azure API Management (APIM). All inter-service communication traverses VNet-injected paths with Private Endpoints.

2. **Least-Privilege Access** — RBAC roles are scoped to the minimum required. Managed Identity replaces API keys wherever possible. Periodic access reviews ensure privilege does not drift.

3. **Defense in Depth** — Security is applied at every layer: network (VNet + NSG), transport (TLS 1.2+), identity (Entra ID + Managed Identity), application (APIM policies, input validation), data (AI Search security filters), and AI (system prompt guardrails, citation verification, content safety).

4. **Separation of Ingestion and Query Paths** — Document ingestion (chunking, embedding, indexing) runs independently of the query path (retrieval, prompt build, LLM generation). This decoupling allows each pipeline to scale, fail, and evolve independently.

5. **Observability by Default** — Every component emits structured traces, metrics, and logs. Correlation IDs propagate end-to-end, enabling full request tracing from the UI click to the LLM token output.

---

## 2. End-to-End Flow

The architecture encompasses two distinct data flows—**ingestion** and **query**—that share the same Azure AI Search index but operate independently.

### 2.1 Ingestion Flow (Document → Searchable Chunks)

```
┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐    ┌────────────────┐
│ Azure Blob   │───▶│ Azure Functions   │───▶│ Azure OpenAI     │───▶│ Azure AI Search│
│ Storage      │    │ (Chunking +       │    │ (Embeddings      │    │ (Index:        │
│ (Policy PDFs,│    │  Metadata Extract) │    │  Model)          │    │  security-     │
│  DOCX, MD)   │    │                   │    │                  │    │  policies-idx) │
└──────────────┘    └───────────────────┘    └──────────────────┘    └────────────────┘
```

**Detailed Steps:**

1. **Document Upload** — Policy documents (PDF, DOCX, MD, TXT, HTML, PPTX) are uploaded to Azure Blob Storage (ADLS Gen2). Each document is tagged with metadata: `policy_id`, `classification` (Internal / Confidential), `allowed_groups` (Entra group IDs), `effective_date`, and `version`.

2. **Event-Driven Trigger** — A Blob Storage event triggers an Azure Function. This decouples ingestion from the query path and allows event-driven, near-real-time processing.

3. **Text Extraction** — The Azure Function extracts text from the document. For simple formats (TXT, MD), direct parsing is used. For complex layouts with tables, headers, and multi-column PDFs, **Azure AI Document Intelligence** provides structured extraction.

4. **Chunking** — The extracted text is split into chunks by section headings (e.g., Policy → Control → Exception). Each chunk maintains:
   - **Consistent size** — Target chunk size of 512–1,024 tokens (tunable based on evaluation; see [Azure best practices on chunk sizing](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data#chunk-size-preview)).
   - **Overlap** — ~100 tokens of overlap to preserve cross-boundary context.
   - **Rich metadata** — `policy_name`, `section`, `classification`, `allowed_groups`, `effective_date`, `version`, `content_hash` (SHA-256 for deduplication).

5. **Embedding** — Each chunk is embedded using the Azure OpenAI embeddings model (e.g., `text-embedding-ada-002` or `text-embedding-3-small`), producing a dense vector for semantic search.

6. **Indexing** — Chunks with their metadata and vectors are uploaded to the `security-policies-idx` Azure AI Search index. The index schema supports hybrid retrieval, security trimming, and semantic reranking (see `8-ai-search-index-schema.md` for the full schema).

### 2.2 Query Flow (User Question → Grounded Answer)

```
┌──────┐   ┌──────┐   ┌──────────────┐   ┌───────────┐   ┌──────────────┐   ┌──────────────┐
│ User │──▶│ UI   │──▶│ APIM         │──▶│ FastAPI   │──▶│ Azure AI     │──▶│ Azure OpenAI │
│      │   │(SWA) │   │(Gateway)     │   │(Container │   │ Search       │   │ (LLM)        │
│      │   │      │   │              │   │ Apps)     │   │ (Hybrid +    │   │              │
│      │◀──│      │◀──│              │◀──│           │◀──│  Semantic)   │   │              │
└──────┘   └──────┘   └──────────────┘   └───────────┘   └──────────────┘   └──────────────┘
                                                │                                    │
                                                ▼                                    ▼
                                         ┌──────────────┐                    ┌──────────────┐
                                         │ App Insights │                    │ App Insights │
                                         │ + Monitor    │                    │ + Monitor    │
                                         └──────────────┘                    └──────────────┘
```

**Detailed Steps:**

1. **User Authentication (Entra ID)** — The user signs in via Microsoft Entra ID using OIDC/OAuth 2.0. The identity token includes group claims used for both authorization and document-level access control. The token is validated at the APIM layer before any backend processing.

2. **UI → APIM (Gateway)** — The frontend (Azure Static Web Apps or App Service) sends the user's question to the API through APIM. APIM performs:
   - **OAuth token validation** — Rejects unauthenticated and unauthorized requests.
   - **Rate limiting** — Enforces per-user and per-subscription rate limits (`rate-limit` / `rate-limit-by-key` policies); returns HTTP 429 when exceeded.
   - **Request validation** — Enforces maximum request body size, header normalization, and correlation ID injection.
   - **Quota management** — Prevents excessive consumption of LLM tokens.

3. **Security Filter Construction** — The FastAPI backend extracts the user's Entra group memberships from the validated token and constructs an Azure AI Search OData filter expression. This filter ensures the user can only retrieve chunks whose `allowed_groups` field matches their group membership and whose `classification` level is permitted.

4. **Hybrid Retrieval (Azure AI Search)** — The API executes a hybrid search query combining:
   - **Keyword search (BM25)** — Traditional full-text search for exact term matching.
   - **Vector search (HNSW/eKNN)** — Semantic similarity search using the embedded query vector.
   - **Reciprocal Rank Fusion (RRF)** — Merges keyword and vector result rankings into a single list for better relevance.
   - **Semantic Reranker** — An optional but recommended reranking pass that uses a transformer model to further improve result relevance (requires Basic SKU or higher for AI Search).
   - **Security trimming** — The OData filter on `allowed_groups` and `classification` is applied at query time, ensuring unauthorized documents are never returned.

5. **Grounded Prompt Construction** — The top-K retrieved chunks (default: 5; tunable) are assembled into a structured prompt:
   - **System message** — Instructs the LLM: *"You are the Security Policy Assistant. Answer ONLY using the provided policy excerpts. If the answer isn't in the excerpts, say you don't know. Always include citations like [chunk-id]."*
   - **Context block** — Each chunk is prefixed with its chunk ID for citation traceability: `[chunk-id] <chunk content>`.
   - **User question** — Appended after the context.
   - **Important:** Raw documents are never injected outside the "retrieved context" boundary. The system prompt reinforces that the LLM must not use its parametric knowledge.

6. **LLM Generation (Azure OpenAI)** — The grounded prompt is sent to the Azure OpenAI chat completion endpoint (e.g., GPT-4o, GPT-4.1). The response is expected to contain inline citations referencing the chunk IDs.

7. **Post-Generation Citation Verification** — Before returning the response to the user, the API checks that the LLM output contains at least one valid citation. If no citations are found, the response is replaced with: *"I can't answer from policy sources. Please ask Security for clarification."* This prevents hallucinated or un-grounded answers from reaching the user.

8. **Response Delivery** — The verified, cited answer is returned through APIM to the UI, along with metadata (retrieval latency, token usage, source document references).

9. **Logging & Observability** — Every step emits telemetry to Application Insights:
   - **Correlation ID** propagated across all services.
   - **Audit events:** user identity, query text hash, retrieval document IDs, citation IDs, latency per step, token counts, and cost estimates.
   - **Sensitive data protection:** Raw prompt/context is hashed; only metadata and hashes are logged by default.

---

## 3. Component Architecture

### 3.1 Identity & Access Layer

| Component | Role | Details |
|-----------|------|---------|
| **Microsoft Entra ID** | User authentication | OIDC/OAuth 2.0; group claims for RBAC and security trimming |
| **Managed Identity** | Service-to-service auth | System-assigned or user-assigned MSI for FastAPI → AI Search, FastAPI → Azure OpenAI, Azure Functions → Blob Storage, etc. Eliminates all static API keys. |
| **RBAC Roles** | Authorization | Scoped per service: `Cognitive Services OpenAI User` for OpenAI, `Search Index Data Reader` for AI Search, `Storage Blob Data Reader` for Blob Storage |

### 3.2 Application Layer

| Component | Role | Details |
|-----------|------|---------|
| **Azure Static Web Apps** | Frontend hosting | Serves the chat UI; authenticates users via Entra ID; communicates with backend through APIM |
| **Azure API Management (APIM)** | API gateway | Centralized security enforcement: OAuth validation, rate limiting, request size limits, header normalization, API versioning, and developer portal |
| **Azure Container Apps** | Backend hosting | Hosts the FastAPI application; supports auto-scaling, VNet injection, and Managed Identity; separates compute from infrastructure concerns |
| **Azure Functions (Python)** | Ingestion processing | Event-driven document processing: triggered by Blob Storage events; handles text extraction, chunking, embedding, and indexing |

### 3.3 Data & Knowledge Layer

| Component | Role | Details |
|-----------|------|---------|
| **Azure Blob Storage (ADLS Gen2)** | Document store | Stores policy documents with metadata tags; Private Endpoint access only; versioning enabled |
| **Azure AI Search** | Retrieval engine | Hybrid search index (`security-policies-idx`) with keyword (BM25), vector (HNSW), and semantic reranking; security filters for document-level access control; Basic SKU or higher for semantic ranker |
| **Azure OpenAI — Embeddings** | Vector generation | Embeds document chunks and user queries for semantic similarity search |
| **Azure OpenAI — Chat Completion** | Answer generation | GPT-4o / GPT-4.1 for generating grounded, cited answers from policy context |

### 3.4 Security & Networking Layer

| Component | Role | Details |
|-----------|------|---------|
| **Azure Virtual Network (VNet)** | Network isolation | All backend services (Container Apps, Functions, AI Search, OpenAI, Storage) are VNet-integrated or accessed via Private Endpoints |
| **Private Endpoints + Private DNS** | Private connectivity | Ensures traffic to Storage, AI Search, Azure OpenAI, and Key Vault never traverses the public internet |
| **Network Security Groups (NSG)** | Traffic rules | Fine-grained inbound/outbound rules per subnet |
| **Azure Key Vault** | Secrets management | Stores certificates, encryption keys, and any secrets not replaceable by Managed Identity; automated key rotation |

### 3.5 Observability Layer

| Component | Role | Details |
|-----------|------|---------|
| **Application Insights** | Distributed tracing & APM | End-to-end request tracing with correlation IDs; custom events for retrieval quality, citation accuracy, and token usage |
| **Azure Monitor** | Metrics & alerts | Platform-level metrics (CPU, memory, HTTP errors); custom alerts for 429 spikes, OpenAI throttling, high latency (p95), and error rate thresholds |
| **Log Analytics Workspace** | Log aggregation | Centralized log store for KQL queries, compliance reporting, and security event investigation |
| **Azure Monitor Workbooks** | Dashboards | Visual dashboards for operational health, cost tracking, and RAG quality metrics |

### 3.6 DevOps & Delivery Layer

| Component | Role | Details |
|-----------|------|---------|
| **GitHub Actions** | CI/CD | Automated pipelines: build container images, run tests (unit + integration), lint IaC, deploy to dev → stage → prod |
| **Azure Container Registry (ACR)** | Image registry | Stores versioned container images for the FastAPI backend; scanned for vulnerabilities |
| **Terraform (or Bicep)** | Infrastructure as Code | Repeatable, parameterized environment creation with modules and per-environment configs (`dev`, `stage`, `prod`) |

---

## 4. Network Topology

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                         Azure VNet                              │
                    │                                                                 │
Internet ──▶ APIM ─┤─▶ ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐  │
  (TLS)      (Public│   │ Container Apps  │──▶│ AI Search    │   │ Azure OpenAI   │  │
              EP)   │   │ (FastAPI)       │   │ (Private EP) │   │ (Private EP)   │  │
                    │   │ (VNet Injected) │──▶│              │   │                │  │
                    │   └─────────────────┘   └──────────────┘   └────────────────┘  │
                    │          │                                                      │
                    │          ▼                                                      │
                    │   ┌─────────────────┐   ┌──────────────┐   ┌────────────────┐  │
                    │   │ Azure Functions │──▶│ Blob Storage │   │ Key Vault      │  │
                    │   │ (VNet Injected) │   │ (Private EP) │   │ (Private EP)   │  │
                    │   └─────────────────┘   └──────────────┘   └────────────────┘  │
                    │                                                                 │
                    │   ┌──────────────────────────────────────────┐                  │
                    │   │ Private DNS Zones                        │                  │
                    │   │ - privatelink.search.windows.net         │                  │
                    │   │ - privatelink.openai.azure.com           │                  │
                    │   │ - privatelink.blob.core.windows.net      │                  │
                    │   │ - privatelink.vaultcore.azure.net        │                  │
                    │   └──────────────────────────────────────────┘                  │
                    └─────────────────────────────────────────────────────────────────┘
```

**Key networking decisions:**
- **APIM is the only public ingress point.** All other services have public network access disabled.
- **Private Endpoints** for AI Search, Azure OpenAI, Blob Storage, and Key Vault ensure data never leaves the Azure backbone.
- **Private DNS Zones** resolve private endpoint FQDNs to internal IPs within the VNet.
- **Container Apps and Functions** are VNet-injected, enabling them to reach Private Endpoints without public routing.

---

## 5. Security Layers (Defense in Depth)

Security is applied at every layer of the stack:

### Layer 1 — Network
- VNet isolation with NSGs
- Private Endpoints for all data-plane services
- Public network access disabled on Storage, AI Search, OpenAI, Key Vault
- APIM as sole public entry point with WAF-like policies

### Layer 2 — Identity
- Entra ID authentication (OIDC/OAuth 2.0) for all users
- Group-based RBAC for authorization (e.g., Security Team, Engineering, All Employees)
- Managed Identity for all service-to-service communication
- No static API keys or connection strings in code or configuration

### Layer 3 — Application
- APIM policies: OAuth validation, rate limiting, request size limits, header normalization
- Input sanitization and validation in FastAPI
- Correlation ID injection for end-to-end tracing

### Layer 4 — Data
- **Document-level access control**: Azure AI Search security filters restrict which chunks are returned based on the user's Entra group memberships (`allowed_groups` field) and document `classification` level
- Data classification enforcement: documents tagged as Internal/Confidential are only accessible to authorized groups
- Content hashing in logs (no raw policy content in telemetry)

### Layer 5 — AI Guardrails
- **System prompt enforcement**: *"Answer ONLY from provided policy excerpts. If not found, say you don't know."*
- **Prompt injection defense**: Instructions embedded in documents are stripped/ignored
- **Citation requirement**: Every claim must reference a chunk ID; un-cited responses are rejected
- **Content safety**: Queries for harmful content (e.g., "how to bypass MFA", "how to exfiltrate data") are blocked
- **Refusal policy**: Disallowed or out-of-scope requests receive a standard refusal response
- **Human escalation**: Users can create a ticket for the Security team when the assistant cannot answer

---

## 6. RAG Pipeline Details

### 6.1 Retrieval Strategy

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Search type** | Hybrid (keyword + vector) | Combines BM25 full-text and HNSW vector similarity |
| **Ranking fusion** | Reciprocal Rank Fusion (RRF) | Merges keyword and vector rankings |
| **Semantic reranker** | Enabled | Transformer-based reranking for improved relevance; requires Basic SKU+ |
| **Top-K documents** | 5 (tunable) | Balances context richness vs. token cost |
| **Security filter** | OData on `allowed_groups`, `classification` | Enforced at query time for document-level access control |
| **Strictness** | Medium (tunable) | Controls how aggressively irrelevant chunks are filtered |

### 6.2 Prompt Engineering Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ SYSTEM MESSAGE                                                  │
│ "You are the Security Policy Assistant.                         │
│  Answer ONLY using the provided policy excerpts.                │
│  If the answer isn't in the excerpts, say you don't know.       │
│  Always include citations like [chunk-id].                      │
│  Do not use your internal knowledge."                           │
├─────────────────────────────────────────────────────────────────┤
│ CONTEXT (Retrieved Chunks)                                      │
│ [policy-abc#3] "All employees must use MFA for VPN access..."   │
│ [policy-def#7] "Password rotation is required every 90 days..." │
│ [policy-abc#5] "Exceptions require CISO approval..."            │
├─────────────────────────────────────────────────────────────────┤
│ USER QUESTION                                                   │
│ "What is the password rotation policy?"                         │
└─────────────────────────────────────────────────────────────────┘
```

**Key prompt design decisions:**
- The system message is crafted to **reaffirm critical behavior** (answer only from sources, cite everything) as recommended by Azure's best practices.
- Retrieved chunks are clearly delimited with their IDs for unambiguous citation.
- The user question is placed last to take advantage of the LLM's recency bias.
- If the retrieved context is insufficient, the model is instructed to respond: *"Not found in the approved security policy set."*

### 6.3 Token Usage Considerations

Based on [Azure's token estimation guidance](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data#token-usage-estimation-for-azure-openai-on-your-data), two LLM calls contribute to total token usage:

1. **Intent processing call** — Reformulates the user query into search intents (includes: instructions + user question + conversation history).
2. **Generation call** — Produces the final answer (includes: instructions + system message + retrieved chunks + user question + conversation history).

**Cost optimization strategies:**
- Cache embeddings for frequently asked queries (with per-user filter awareness).
- Tune `top_k` and `strictness` parameters to minimize unnecessary token consumption.
- Monitor token usage per request via Application Insights custom metrics.

---

## 7. Observability & Auditing Strategy

### 7.1 Tracing

Every request is traced end-to-end through these stages:

```
Auth Validation → Security Filter Build → Query Embedding → Hybrid Retrieval
    → Semantic Rerank → Prompt Construction → LLM Generation → Citation Check → Response
```

Each stage emits a span with:
- **Duration** (ms)
- **Status** (success / failure / degraded)
- **Stage-specific metadata** (e.g., number of chunks retrieved, token count, model version)

### 7.2 Metrics & Alerts

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Request latency (p50) | < 2s | — |
| Request latency (p95) | < 5s | > 8s |
| Retrieval hit rate | > 90% | < 70% |
| Citation accuracy | > 95% | < 85% |
| "No answer" rate | < 10% | > 20% |
| Error rate (5xx) | < 1% | > 5% |
| Token usage per request | Monitor | Spike > 2x baseline |
| APIM 429 responses | Minimal | Spike > 50/min |

### 7.3 Audit Log Schema

Each query produces an audit record with:

| Field | Description |
|-------|-------------|
| `correlation_id` | Unique request identifier propagated across all services |
| `user_id` | Entra ID user identifier |
| `user_groups` | Group memberships used for security trimming |
| `query_hash` | SHA-256 hash of the user's question (not the raw text) |
| `retrieval_ids` | List of chunk IDs returned by AI Search |
| `cited_ids` | List of chunk IDs cited in the LLM response |
| `latency_ms` | Total request duration |
| `latency_breakdown` | Per-stage latency (auth, retrieval, generation, etc.) |
| `token_usage` | Input/output token counts for the LLM call |
| `model_version` | Azure OpenAI model deployment name and version |
| `timestamp` | UTC timestamp of the request |

---

## 8. Reliability & Resilience Patterns

| Pattern | Implementation | Fallback |
|---------|---------------|----------|
| **Timeouts** | Configurable per downstream call (AI Search: 5s, OpenAI: 30s) | Return error with retry guidance |
| **Retries with jitter** | Exponential backoff + random jitter for transient failures (429, 503) | Max 3 retries before circuit opens |
| **Circuit breaker** | Opens after N consecutive failures to a downstream service | Returns "retrieval-only answer" if LLM fails, or "system temporarily unavailable" |
| **Graceful degradation** | If semantic reranker is unavailable, fall back to hybrid-only results | Slightly reduced relevance, but service remains available |
| **Caching** | Embeddings cache for normalized queries; retrieval cache (per-user filter-aware) for repeated questions | Cache miss falls through to live query |

---

## 9. Evaluation & Continuous Improvement

### 9.1 Evaluation Framework

- **Golden test set**: 30–50 curated questions with expected answers and citation references
- **Automated evaluation**: Run via Azure AI Foundry Prompt Flow to track:
  - **Groundedness** — Is the answer fully supported by the retrieved context?
  - **Relevance** — Are the retrieved chunks relevant to the question?
  - **Citation accuracy** — Do citations point to the correct source chunks?
  - **Faithfulness** — Does the answer avoid hallucination?
- **Regression tracking**: Every change to chunking, retrieval parameters, or prompts triggers a re-evaluation run

### 9.2 Feedback Loop

```
User Feedback ──▶ Track "no answer" rate, "wrong citation" rate, thumbs up/down
       │
       ▼
Improvement Actions:
  ├─▶ Adjust chunk size and overlap
  ├─▶ Tune retrieval parameters (top_k, strictness)
  ├─▶ Update synonyms and metadata in the search index
  ├─▶ Refine system prompt instructions
  └─▶ Expand evaluation dataset with new edge cases
```

---

## 10. Data Classification & Governance

| Classification | Description | Access Control |
|---------------|-------------|----------------|
| **Public** | Policies available to all employees | No group restriction on `allowed_groups` |
| **Internal** | Policies limited to specific departments | `allowed_groups` contains relevant Entra group IDs |
| **Confidential** | Highly sensitive policies (e.g., incident response, executive security) | `allowed_groups` restricted to Security team; additional approval workflows |

**Governance rules:**
- Only approved policy sources are ingested (corpus curation)
- Documents carry `effective_date` and `version` for temporal accuracy
- Retired/superseded policies are de-indexed or marked with an expiration filter
- Data residency: Azure region selection aligns with Swiss/EU or other regulatory requirements
- Retention policies govern how long logs, chat transcripts, and evaluation datasets are stored

---

## 11. Migration Note — Azure OpenAI On Your Data

> **Important:** Azure OpenAI "On Your Data" is deprecated and approaching retirement. Microsoft recommends migrating to **Foundry Agent Service** with **Foundry IQ** for grounded answer generation.

This architecture follows the **custom RAG pattern** rather than relying on the "On Your Data" managed feature. Key differences:

| Aspect | On Your Data (Deprecated) | Custom RAG (This Architecture) |
|--------|--------------------------|-------------------------------|
| **Retrieval control** | Managed by Azure | Full control via FastAPI + AI Search SDK |
| **Security trimming** | Built-in filter support | Custom OData filters with Entra group claims |
| **Prompt engineering** | Limited system message customization | Full control over system prompt, context assembly, and post-processing |
| **Evaluation** | Limited | Full Prompt Flow evaluation pipeline |
| **Future-proofing** | Deprecated | Aligned with Foundry Agent Service / Foundry IQ migration path |

By implementing a custom RAG pipeline, this architecture avoids dependency on a deprecated feature while maintaining full control over security, retrieval quality, and prompt engineering.

---

## 12. References

- [Azure OpenAI: Use Your Data Concepts](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data)
- [Azure OpenAI On Your Data — Network & Access Configuration](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/on-your-data-configuration)
- [Azure AI Search — Security Trimming with Entra ID](https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search-with-aad)
- [Azure AI Search — Hybrid Search](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)
- [Azure AI Search — Semantic Ranking](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview)
- [Foundry Agent Service (Recommended Migration)](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)
- [Foundry IQ — Knowledge Base](https://learn.microsoft.com/en-us/azure/ai-services/agents/concepts/what-is-foundry-iq)

---

*This document serves as the comprehensive architectural reference for the Security Policy Assistant. It should be read in conjunction with the companion documents in this series (see `2-core-azure-components.md` through `11-checklists.md`) for component-level details, security stages, production readiness, and implementation pseudocode.*