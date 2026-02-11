# RAG Quality Stages for Security Policy Assistant

## Overview
This document details the Retrieval-Augmented Generation (RAG) quality stages required to ensure the Security Policy Assistant delivers accurate, reliable, and policy-grounded answers. Each stage focuses on a critical aspect of data, retrieval, and evaluation quality.

## Stage 0 — Corpus Design
- Use only “approved” policy sources
- Maintain versioning: policy effective date, revision ID, owner

## Stage 1 — Chunking Strategy
- Chunk documents by section headings (e.g., Policy → Control → Exceptions)
- Keep chunk size consistent; add overlap for context
- Store metadata: policy name, section, last updated, classification

## Stage 2 — Retrieval Strategy
- Use hybrid retrieval (keyword + vector) with Azure AI Search (BM25 + HNSW/eKNN + RRF)
- Add semantic ranker to improve relevance
- Apply filters for security trimming (classification, allowed_groups)

## Stage 3 — Prompt Strategy
- Enforce strict system prompt: “Answer only from citations”
- Provide top-K chunks with citation IDs
- If low confidence or no sources: respond “Not found in policy set”

## Stage 4 — Evaluation
- Build a small test set (30–50 questions with expected citations)
- Use Foundry Prompt Flow evaluation to track metrics and regressions

## Stage 5 — Continuous Improvement
- Track “no answer” rate and “wrong citation” rate
- Update chunking, synonyms, metadata, and retrieval parameters based on evaluation results

---
Following these RAG quality stages ensures the Security Policy Assistant provides trustworthy, policy-grounded answers and supports ongoing quality improvement.