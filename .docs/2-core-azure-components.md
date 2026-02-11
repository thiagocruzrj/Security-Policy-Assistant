# Core Azure Components for Security Policy Assistant

## Overview

This document details the specific Azure services chosen for the **Security Policy Assistant**, including recommended SKUs, configuration requirements, and the architectural rationale for each decision. The selection prioritizes **security** (Zero Trust), **scalability**, and **enterprise compliance**.

---

## 1. Identity & Access Management (IAM)

### **Microsoft Entra ID (formerly Azure AD)**
*   **Role:** The single source of truth for identity. Handles authentication (AuthN) and provides group claims for authorization (AuthZ).
*   **Configuration:**
    *   **App Registration:** Create one for the Frontend (SPA) and one for the Backend (API).
    *   **ID Tokens:** specific to the application; should include `groups` claim for RBAC.
    *   **Conditional Access Policies:** Enforce MFA and device compliance before specialized access is granted.
*   **Rationale:** Eliminates the need for custom user management. "Bring your own identity" is standard for enterprise apps.

### **Managed Identity**
*   **Role:** Eliminates static credentials (API keys, connection strings) from code and config.
*   **Type:** **User-Assigned Managed Identity** is recommended for better lifecycle management (one identity can be shared across the Container App and Function App if they share the same permissions scope, though strictly least-privilege suggests separate identities).
*   **Assignments:**
    *   `Cognitive Services OpenAI User` (on Azure OpenAI)
    *   `Search Index Data Reader` / `Search Index Data Contributor` (on AI Search)
    *   `Storage Blob Data Reader` (on Storage Account)
    *   `Key Vault Secrets User` (on Key Vault)

---

## 2. Compute & API Hosting

### **Azure Container Apps (ACA)**
*   **Role:** Hosts the FastAPI backend query service.
*   **Recommended SKU:** **Consumption Plan** (serverless) or **Dedicated Plan** (if VNet injection requires it, though Consumption + VNet is now supported).
*   **Key Settings:**
    *   **Ingress:** Internal-only (traffic only allowed from APIM via VNet/Private Link).
    *   **Scaling:** KEDA-based autoscaling (http-scaling rule) to handle concurrent requests (0 to N replicas).
    *   **Dapr:** Optional, but useful for sidecar patterns if more complex state management is needed later.
*   **Rationale:** Abstracts Kubernetes complexity while providing full container orchestration, VNet integration, and scale-to-zero capabilities.

### **Azure Functions**
*   **Role:** Handles the asynchronous ingestion pipeline (Blob Trigger -> Text Extraction -> Embedding -> Indexing).
*   **Runtime:** Python (isolation recommended: use the V2 programming model).
*   **Hosting Plan:** **Premium Plan (EP1)** is recommended over Consumption for:
    *   **VNet Integration:** Required to reach private endpoints of AI Search and OpenAI.
    *   **No Cold Start:** Critical if ingestion happens frequently or sporadically but needs instant processing.
    *   **Longer Execution Limits:** Ingestion of large PDFs may exceed standard consumption timeouts.

### **Azure API Management (APIM)**
*   **Role:** The secure Gateway for all external traffic.
*   **Recommended SKU:** **Standard v2** (supports VNet integration) or **Premium** (if high availability/multi-region is needed). *Basic/Standard v1 do not support VNet injection typically required for this architecture.*
*   **Key Policies:**
    *   `validate-jwt`: Verifies the Entra ID token before passing to backend.
    *   `rate-limit-by-key`: Throttles requests based on user ID or subscription key.
    *   `set-header`: Strips sensitive backend headers; adds correlation IDs.
*   **Rationale:** Decouples the frontend from backend services, providing a unified enforcement point for security and governance.

---

## 3. Knowledge & Data

### **Azure AI Search**
*   **Role:** Vector database and retrieval engine.
*   **Recommended SKU:** **Basic** (minimum for Semantic Ranker) or **Standard (S1)** (for larger indexes/higher partition count). *Free tier does not support Semantic Ranker or VNet Private Endpoints.*
*   **Configuration:**
    *   **Semantic Ranker:** Enabled (critical for RAG quality).
    *   **Vector Search:** HNSW algorithm configuration.
    *   **Network:** Public network access **Disabled**. Private Endpoint required.
*   **Rationale:** Native specialized vector database that combines keyword (BM25) + vector search (RRF) for superior retrieval quality compared to pure vector DBs.

### **Azure Blob Storage (Data Lake Gen2)**
*   **Role:** Stores the "Gold Source" policy documents (PDF, DOCX) and ingestion state.
*   **Configuration:**
    *   **Hierarchical Namespace:** Enabled (ADLS Gen2) for efficient directory operations.
    *   **Access Tier:** Hot (for active policies).
    *   **Network:** Public access **Disabled**. Private Endpoint required.
    *   **Versioning:** Enabled to track policy revisions.

### **Azure OpenAI**
*   **Role:** Provides the LLM (GPT-4) and Embedding models.
*   **Models:**
    *   **Chat:** `gpt-4o` or `gpt-4-turbo` (Model version 1106 or newer for JSON mode/better instruction following).
    *   **Embeddings:** `text-embedding-3-small` (or `ada-002` if migrating legacy).
*   **Deployment:** Standard (provisioned throughput units - PTU - only if extremely high volume, otherwise Standard Tier pay-as-you-go).
*   **Network:** Private Endpoint required.

---

## 4. Networking & Security

### **Virtual Network (VNet)**
*   **Role:** The secure isolation boundary.
*   **Subnets:**
    *   `snet-apim`: For API Management (requires dedicated NSG rules).
    *   `snet-apps`: For Container Apps and Functions (delegated).
    *   `snet-pe`: For Private Endpoints (Storage, OpenAI, Search, Key Vault).

### **Private Endpoints**
*   **Role:** Provides a private IP address from the VNet to PaaS services.
*   **DNS:** Requires **Private DNS Zones** linked to the VNet to resolve hostnames (e.g., `privatelink.openai.azure.com`) to internal IPs.

### **Azure Key Vault**
*   **Role:** Stores the few inevitable secrets (e.g., if a 3rd party API key is needed) and encryption keys.
*   **Access Policy:** RBAC-based (recommended over legacy Access Policies).
*   **Rationale:** distinct separation of configuration (App Configuration—optional) and secrets (Key Vault).

---

## 5. Observability

### **Application Insights**
*   **Role:** Application Performance Monitoring (APM).
*   **Instrumentation:**
    *   **Distributed Tracing:** Implemented via OpenTelemetry SDKs in Python.
    *   **Custom Dimensions:** Log `chunk_id`, `token_usage`, `retrieval_score` (without logging PII/raw text).

### **Azure Monitor & Log Analytics**
*   **Role:** Centralized log aggregation and alerting.
*   **Workbooks:** Create a "RAG Quality" workbook to visualize "No Answer" rates and user feedback scores.

---

## 6. DevOps & Infrastructure

### **Azure Container Registry (ACR)**
*   **Role:** Stores Docker images for the FastAPI backend.
*   **SKU:** **Standard** (allows private link usage) or **Premium**. Basic is often sufficient for non-VNet scenarios, but for full closure, Standard is preferred.

### **Infrastructure as Code (IaC)**
*   **Tooling:** **Terraform** (providers: `azurerm`, `azapi`) or **Azure Bicep**.
*   **State Management:** Remote state stored in a separate, locked-down Storage Account.

---

## Summary of SKUs for Cost Estimation

| Service | SKU / Tier | Justification |
| :--- | :--- | :--- |
| **Azure OpenAI** | Standard (Pay-as-you-go) | Flexible for varying token usage. |
| **Azure AI Search** | **Basic** | Supports Semantic Ranker and Private Endpoints (Cost effective entry point). |
| **APIM** | **Standard v2** | Required for VNet Integration (Compute Isolation). |
| **App Service/ACA** | **Consumption** | Scale based on demand. |
| **Azure Functions** | **Premium (EP1)** | Required for VNet Integration. |
| **Storage** | **Standard (LRS)** | Low cost, high durability. |