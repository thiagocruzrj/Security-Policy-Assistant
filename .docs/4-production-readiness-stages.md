# Production Readiness Stages for Security Policy Assistant

## Overview
This document describes the stages and controls required to ensure the Security Policy Assistant is production-ready, reliable, and maintainable. Each stage demonstrates the ability to ship, operate, and secure the solution at scale.

## Stage 0 — Environments & IaC
- Separate resources for dev, stage, and prod environments
- All infrastructure provisioned via Terraform or Bicep
- Parameterized deployments per environment

## Stage 1 — CI/CD
- Build API container image, push to Azure Container Registry (ACR), deploy to Container Apps
- Run automated tests (unit + basic integration)
- Policy as code: linting for IaC, security checks

## Stage 2 — Gateway Controls
- Azure API Management (APIM) as the API gateway
  - OAuth validation
  - Request size limits
  - Rate limiting per subscription, key, or user (rate-limit/rate-limit-by-key policies)
  - Header normalization (e.g., correlation IDs)

## Stage 3 — Reliability Patterns
- Timeouts and retries (with jitter) for OpenAI and Search calls
- Circuit breaker/fallback: “retrieval-only answer” if LLM fails, or “cannot answer”
- Caching strategies:
  - Embeddings cache (query normalization)
  - Retrieval cache for repeated questions (with per-user filter awareness)

## Stage 4 — Observability
- Tracing for each request step: auth → retrieval → prompt-build → LLM → response
- Metrics: latency (p50/p95), retrieval hit rate, token usage, error rates
- Dashboards and alerts (e.g., 429 spikes, OpenAI throttling, Search latency)

## Stage 5 — Security Operations
- Secrets rotation using Azure Key Vault
- RBAC drift detection
- Automated dependency scanning

---
Following these production readiness stages ensures the Security Policy Assistant can be shipped, operated, and maintained securely and reliably in enterprise environments.