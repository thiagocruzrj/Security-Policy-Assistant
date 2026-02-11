# Demo Next Steps: FastAPI + Container Apps Blueprint

## Overview
This document outlines the recommended stack and next steps for building a demo of the Security Policy Assistant using Python, FastAPI, and Azure-native services. The blueprint emphasizes a production-ready architecture with clear separation of concerns, security, and scalability.

## Recommended Stack
- **Python + FastAPI:**
  - Rapid API development with strong async support and OpenAPI integration
- **Azure Container Apps:**
  - Host the FastAPI backend for scalable, production-grade deployment
- **Azure API Management (APIM):**
  - Acts as the secure gateway in front of the API
- **Azure AI Search + Azure OpenAI:**
  - Hybrid retrieval and LLM-powered answer generation
- **Azure Blob Storage:**
  - Stores policy documents
- **Azure Functions:**
  - Handles event-driven ingestion and processing of new/updated policy documents

## Architecture Narrative
- **Separation of Ingestion and Query Path:**
  - Ingestion (document processing) is handled by Azure Functions
  - Query (user questions) is handled by FastAPI in Container Apps
- **Private Endpoints & Managed Identity:**
  - All services communicate over private endpoints
  - Managed identities are used for secure, secretless access
- **Observability:**
  - Application Insights and Azure Monitor for tracing, metrics, and logging
- **Gateway Controls:**
  - APIM enforces authentication, rate limiting, and request validation

## Next Steps
1. Scaffold FastAPI project structure
2. Set up Azure Container Apps environment
3. Configure APIM as the API gateway
4. Integrate Azure AI Search and Azure OpenAI
5. Set up Blob Storage for policy documents
6. Implement Azure Functions for ingestion pipeline
7. Enable observability and monitoring

---
This blueprint provides a clear, enterprise-ready path for demoing the Security Policy Assistant, demonstrating best practices in architecture, security, and scalability.