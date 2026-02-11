# Production Readiness Stages for Security Policy Assistant

## Overview

This document defines the **Production Readiness (SRE) Stages** required to transition the Security Policy Assistant from a functional Proof-of-Concept (PoC) to a resilient, scalable, and observable enterprise service. It emphasizes **Infrastructure as Code (IaC)**, **CICD automation**, **reliability patterns**, and **comprehensive observability**.

---

## Stage 0: Environment Standards (IaC & Networking)

The foundation of production is reproducibility. Manual portal clicks are forbidden.

### 0.1 Infrastructure as Code
*   **Tooling:** Use **Terraform** (with Azure Verified Modules) or **Bicep**.
*   **State Management:** Remote state stored in a locked-down Azure Storage Account with `Prevent Delete` locks.
*   **Naming Convention:** Standardize: `e.g., rg-policybot-prod-weu`, `kv-policybot-prod-weu`.
*   **Drift Detection:** Scheduled pipelines (daily) to run `terraform plan` and alert on unauthorized changes.

### 0.2 Environment Parity
*   **Dev:** Cost-optimized. Single instance (no SLA). Ephemeral data. Feature branches deploy here.
*   **Staging:** Mirror of Prod (scaled down). Used for load testing, UAT, and security scanning.
*   **Prod:** High Availability (HA) configuration using Availability Zones (AZs) where supported.

---

## Stage 1: Build & Deploy Pipelines (CI/CD)

Automate the path to production with strict quality gates.

### 1.1 Continuous Integration (CI)
*   **Trigger:** On Pull Request (PR) to `main`.
*   **Steps:**
    1.  **Code Quality:** `ruff` or `flake8` linting.
    2.  **Secret Scan:** `trivy` or GitHub Advanced Security to detect hardcoded keys.
    3.  **Unit Tests:** `pytest` with >80% code coverage requirement.
    4.  **Security Static Analysis (SAST):** `bandit` for Python vulnerabilities.
    5.  **Build:** Create container image (`azure-policy-bot:sha-123`) and push to ACR.

### 1.2 Continuous Deployment (CD)
*   **Strategy:** Blue/Green or Rolling updates via Azure Container Apps revisions.
*   **Gated Releases:** Deployment to Prod requires approval from Release Manager + successful E2E test run in Staging.
*   **Smoke Tests:** Post-deployment script verifies `/health` endpoint and performs a synthetic "hello world" RAG query.
*   **Rollback:** Automated rollback to previous healthy revision if Smoke Test fails.

---

## Stage 2: Scalability & Performance Tuning

Configure the system to handle concurrent users without degradation.

### 2.1 Backend Scaling (Container Apps)
*   **Autoscaling Rules (KEDA):**
    *   `http-scaling`: Scale up when `concurrent requests > 10` per replica.
    *   `min-replicas`: 2 (for HA).
    *   `max-replicas`: 10 (cost guardrail).
*   **Resource Limits:** Define tight CPU/Memory requests to effectively bin-pack nodes.

### 2.2 Database & Search Scaling
*   **AI Search:**
    *   **Replicas:** Add replicas for read query throughput (QPS). Use at least 2 for SLA.
    *   **Partitions:** Only increase if index size > 25GB (unlikely for policy docs).
*   **Cosmos DB / Storage:** Use partitioning keys effectively if storing session history.

### 2.3 Caching Strategy
*   **APIM Cache:** Cache response for identical queries (hash of query text + user group claims) for 5 minutes.
*   **Embeddings Cache:** (In-Memory or Redis) Check if query embedding already exists before calling OpenAI `text-embedding-3-small`.

---

## Stage 3: Reliability & Resilience Patterns

The system must handle downstream failures gracefully.

### 3.1 Retry Logic
*   **Transient Fault Handling:** Use `tenacity` library in Python.
*   **Policy:** Exponential Backoff + Jitter.
    *   OpenAI: Retry on 429 (Too Many Requests) and 5xx. Max 3 retries.
    *   Search: Retry on 5xx. Max 2 retries.
*   **Dead Letter Queue (DLQ):** Failed ingestion messages go to Storage Queue for manual inspection.

### 3.2 Circuit Breakers
*   **Pattern:** If OpenAI fails 5 times in 10 seconds, open circuit for 60 seconds.
*   **Fallback:**
    *   **Primary:** "Service is degraded, trying cached answers..."
    *   **Secondary:** "Service unavailable, please check back later or consult the source PDF manually." (Link to Blob Storage if permitted).

### 3.3 Rate Limiting (Quotas)
*   **APIM Policy:**
    *   `ip-filter`: Allow only corporate VPN IPs.
    *   `quota-by-key`: Limit each user to 100 queries/day.
    *   `rate-limit`: 20 calls/minute per user to prevent flooding.

---

## Stage 4: Observability Strategy

"You build it, you run it." Teams need data to run it.

### 4.1 Distributed Tracing
*   **Standard:** OpenTelemetry (OTEL).
*   **Trace Context:** Propagate `Trace-ID` and `Span-ID` from Client -> APIM -> Backend -> Vector DB -> OpenAI.
*   **Visualization:** Application Insights Application Map.

### 4.2 Application Metrics
*   **Key Metrics (GOLD Signals):**
    *   **Latency:** P50, P95, P99 of the full RAG pipeline.
    *   **Traffic:** Request rate (RPS).
    *   **Errors:** 4xx vs 5xx breakdown.
    *   **Saturation:** Container CPU/RAM usage; OpenAI Token Quota usage (TPM).

### 4.3 Alerting Rules
*   **Critical (PagerDuty):**
    *   `Available Replicas < 1` (Service Down).
    *   `P95 Latency > 10s` for 5 minutes (Degradation).
    *   `5xx Rate > 5%`.
*   **Warning (Email/Slack):**
    *   `OpenAI 429 Rate > 1%` (Quota approaching limit).
    *   `Ingestion Queue > 100 items`.

---

## Stage 5: Operational Excellence

### 5.1 Runbooks
*   **SOP-001:** "How to Rotate Keys" (Though Managed Identity should minimize this).
*   **SOP-002:** "How to Restore Index" (Re-run ingestion from Blob).
*   **SOP-003:** "Handling 'Bad Answer' Escalations" (Triage process).

### 5.2 Routine Maintenance
*   **Index Optimization:** Scheduled re-indexing (monthly) to clean up fragmentation.
*   **Dependency Updates:** Automated dependabot/renovate PRs for Python packages.
*   **Cost Review:** Monthly review of Azure Cost Analysis (focus on Search & OpenAI hourly costs).

---

## Summary Checklist
- [ ] **IaC:** Terraform applies cleanly to a fresh subscription.
- [ ] **CI/CD:** Pushing to main auto-deploys to Staging.
- [ ] **Resilience:** Circuit breakers prevent cascading failures.
- [ ] **Monitoring:** Dashboard shows P95 latency and token usage.
- [ ] **Docs:** Runbooks exist for critical incidents.