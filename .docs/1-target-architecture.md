# Target Architecture for Security Policy Assistant

## Introduction & Objectives
The Security Policy Assistant aims to deliver a secure, enterprise-grade GenAI solution for managing and querying security policies. The primary objectives are:
- Ensure robust identity and access management using Microsoft Entra ID
- Protect sensitive data with strong boundaries and security filters
- Guarantee auditability and compliance through comprehensive logging
- Provide accurate, grounded answers strictly from policy documents
- Enable continuous improvement via feedback and evaluation loops

This document introduces the overall architecture and foundational principles that guide the design and implementation of the Security Policy Assistant.

## 1. End-to-End Flow
The Security Policy Assistant is designed to provide enterprise-grade GenAI capabilities for security policy management, ensuring identity, data boundaries, auditability, and strong guardrails. The architecture supports a secure, scalable, and auditable workflow for policy retrieval and question answering.

### High-Level Steps
1. **User Signs In (Entra ID):**
   - Users authenticate using Microsoft Entra ID (formerly Azure AD), ensuring secure, enterprise-grade identity management and RBAC.

2. **UI Calls API (Behind APIM):**
   - The frontend UI communicates with backend APIs, which are protected and managed by Azure API Management (APIM) for security, throttling, and monitoring.

3. **API Performs Retrieval from AI Search (Hybrid + Semantic Rerank):**
   - The API queries Azure AI Search using both keyword and semantic search, with hybrid retrieval and semantic reranking to ensure relevant, high-quality policy context is returned.

4. **API Builds a Grounded Prompt (Context + Citations):**
   - The API constructs a prompt for the LLM, grounding it with retrieved policy context and including citations for traceability and auditability.

5. **API Calls Azure OpenAI for Answer:**
   - The grounded prompt is sent to Azure OpenAI, which generates a response strictly based on the provided context ("answer only from policy").

6. **Logs/Metrics Go to App Insights / Monitor:**
   - All interactions, including user queries, API calls, and LLM responses, are logged to Azure Application Insights and Azure Monitor for observability, auditing, and compliance.

7. **Feedback Loop Improves Chunking, Index, Prompts, and Evaluation:**
   - User feedback and system metrics are used to iteratively improve document chunking, search index quality, prompt engineering, and evaluation metrics.

## 2. Security and Compliance Considerations
- **Identity & Access:** Entra RBAC, user authentication, and authorization.
- **Data Boundaries:** Use of VNets, private endpoints, and secure storage.
- **Document Security:** AI Search security filters restrict document access per user.
- **Auditability:** All actions are logged for compliance and traceability.
- **Guardrails:** LLM is instructed to answer only from retrieved policy context.

## 3. Reference
- [Azure OpenAI: Use Your Data Guidance](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/use-your-data?view=foundry-classic&utm_source=chatgpt.com&tabs=ai-search%2Ccopilot)

---
This document provides a high-level overview of the architecture and security principles for the Security Policy Assistant. Subsequent documentation will detail each component and process.