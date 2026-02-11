# Security & Compliance Stages for Security Policy Assistant

## Overview
This document outlines the critical security and compliance stages required to make the Security Policy Assistant enterprise-grade. Each stage addresses specific controls and best practices that security specialists will evaluate during design, implementation, and review.

## Stage 0 — Scope & Data Classification
- Define allowed data: strictly “security policies only” (exclude secrets, credentials, incident data unless explicitly approved)
- Classify documents: Public / Internal / Confidential
- Decide retention: logs, chat transcripts, evaluation datasets

## Stage 1 — Identity-First Access
- Entra ID authentication for all users
- Group-based authorization (e.g., Security team, Engineering, All Employees)
- Service-to-service authentication: Managed Identity + RBAC (no static keys)

## Stage 2 — Network Isolation
- Private endpoints for Storage, AI Search, and Azure OpenAI
- VNet integration for APIs (Container Apps)
- Restrict public ingress; use APIM as the only entry point
- Aligns with “On Your Data” patterns: RBAC, VNets, private endpoints

## Stage 3 — Data Leakage Prevention
- Security trimming in retrieval:
  - Store allowed_groups/classification metadata per chunk
  - AI Search filters based on user groups to prevent unauthorized access
- Never inject raw documents outside the “retrieved context”
- Avoid logging raw prompt/context by default (log hashes + metadata instead)

## Stage 4 — Prompt Injection & Jailbreak Defense
- System prompt: “Only answer from provided policy excerpts. If not found, say you don’t know.”
- Strip/ignore instructions embedded in documents
- Output constraints: require citations, enforce refusal policy for disallowed requests

## Stage 5 — Auditing & Responsible AI
- Audit events: who queried what, retrieval IDs, answer citations, latency/cost
- Content safety: block instructions like “how to bypass MFA” or “how to exfiltrate data”
- Human escalation: enable ticket creation for Security team

## Stage 6 — Compliance Posture
- Data residency: select regions aligned to Swiss/EU or other regulatory requirements
- Retention policies for logs and documents
- Access reviews: enforce least privilege and periodic RBAC reviews

---
This staged approach ensures the Security Policy Assistant meets enterprise security, compliance, and responsible AI standards. Each stage should be validated and documented during implementation and review.