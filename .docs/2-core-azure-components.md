# Core Azure Components for Security Policy Assistant

## Overview
This document outlines the essential Azure services and components required to build a secure, scalable, and production-ready Security Policy Assistant. Each component is selected to address enterprise requirements for identity, access, data security, observability, and GenAI capabilities.

## 1. Identity & Access
- **Microsoft Entra ID:**
  - User authentication via OIDC/OAuth
  - Group claims for RBAC and access control
- **Managed Identity:**
  - Secure workload identity for APIs and Azure Functions
  - Enables calling Azure services without managing secrets

## 2. App & API
- **Frontend:**
  - Azure Static Web Apps or Azure App Service for hosting the UI
- **Azure Functions (Python):**
  - Serverless backend for API logic
- **Azure API Management (APIM):**
  - API gateway for authentication, throttling, quotas, headers, routing, and versioning
  - Built-in rate-limit policies (returns 429 on exceed)

## 3. Knowledge & Data
- **Azure Storage (Blob / ADLS Gen2):**
  - Stores documents (policies, standards, runbooks)
- **Azure AI Search:**
  - Hybrid retrieval: keyword (BM25), vector, and merged rankings (RRF)
- **Semantic Ranker:**
  - Improves relevance by reranking search results

## 4. GenAI
- **Azure OpenAI (via Foundry):**
  - LLM for answer generation
  - Embeddings model for vector search
- **Azure AI Foundry (Prompt Flow + Evaluation):**
  - Orchestrates prompt flows and evaluation metrics

## 5. Secrets, Network, Observability
- **Azure Key Vault:**
  - Manages secrets, certificates, and key rotation
- **VNet + Private Endpoints + Private DNS:**
  - Ensures private traffic for OpenAI, Search, and Storage
- **Application Insights + Azure Monitor (+ Log Analytics):**
  - Provides tracing, metrics, audit logs, and dashboards

## 6. Delivery Platform (Production Readiness)
- **Azure Container Registry (ACR):**
  - Stores container images
- **GitHub Actions:**
  - CI/CD automation
- **IaC (Terraform):**
  - Enables repeatable, automated environment creation

## 7. Optional (Domain-Specific)
- **Azure AI Document Intelligence:**
  - Extracts structured data from complex PDF layouts (tables, headers)
  - Supports managed identity authentication

---
This document serves as a reference for the core Azure services required to implement the Security Policy Assistant, ensuring security, scalability, and compliance.