# RAG Quality Stages for Security Policy Assistant

## Overview

High-quality RAG (Retrieval-Augmented Generation) is not accidental—it is engineered. This document defines the **Quality Lifecycle** for the Security Policy Assistant, detailing the specific techniques required to ensure answers are eager, accurate, and strictly grounded in policy.

---

## Stage 1: Data Curation & Ingestion (Garbage In, Cleanup First)

Policy documents are often long, complex, and filled with legalese. We must preprocess them rigorously.

### 1.1 Text Extraction Strategy
*   **Source Formats:** PDF, DOCX.
*   **Tool:** **Azure AI Document Intelligence** (`prebuilt-layout` model).
*   **Why:** Standard Python libraries (`pypdf`, `unstructured`) often fail on multi-column layouts and tables common in security standards.
*   **Table Resolution:** Convert tables to Markdown or HTML representation to preserve row/column relationships within the text stream.

### 1.2 "Semantic" Chunking
*   **Strategy:** **Recursive Character Chunking** is insufficient. Use **MarkdownHeaderSplitter** (or similar) to respect document structure.
*   **Hierarchy:**
    1.  Split by `H1` (Policy Title).
    2.  Split by `H2` (Section, e.g., "Access Control").
    3.  Split by `H3` (Subsection, e.g., "Password Requirements").
*   **Size:** Target **512 tokens** with **15% (75 tokens) overlap**.
*   **Context Injection:** Prepend the *Parent Header Path* to every chunk.
    *   *Bad Chunk:* "Passwords must be 12 chars."
    *   *Good Chunk:* "Information Security Policy > Authentication Standard > Password Complexity: Passwords must be 12 chars."

### 1.3 Metadata Enrichment
*   Every chunk **MUST** carry these fields for filtering confidence:
    *   `policy_id` (e.g., "ISP-001")
    *   `effective_date` (ISO-8601)
    *   `audience` (e.g., "All Employees", "IT Admins")
    *   `classification` ("Public", "Internal")

---

## Stage 2: Retrieval Tuning (The "Search" in RAG)

We use **Hybrid Search + Semantic Reranking** (State-of-the-Art for Azure AI Search).

### 2.1 Hybrid Search Configuration
*   **Keyword (BM25):** Essential for exact matches of acronyms (e.g., "MFA", "GDPR", "SOC2") where vectors might be fuzzy.
*   **Vector (HNSW):** Captures conceptual queries (e.g., "How do I secure my laptop?" -> matches "Endpoint Protection Standard").
*   **Fusion:** **Reciprocal Rank Fusion (RRF)** combines the two scores.

### 2.2 Semantic Reranker (Critical)
*   **Action:** Take the Top-50 results from Hybrid Search and pass them to the **Semantic Reranker** deep learning model.
*   **Output:** Re-scores the list based on reading comprehension relevance.
*   **Selection:** Pick the **Top-5 to Top-10** reranked chunks for the context window.

### 2.3 Query Expansion (Optional / Stage 2+)
*   **Synonym Maps:** Map "2FA" <-> "MFA" <-> "Multi-Factor". defines explicitly in the Search Index.
*   **HyDE (Hypothetical Document Embeddings):** (Advanced) Generate a fake "perfect" answer using the LLM, embed that, and search against it to find improved vector alignment.

---

## Stage 3: Prompt Engineering (The "Generation" in RAG)

The prompt instructs the LLM on *how* to use the retrieved data.

### 3.1 System Prompt "Golden Rules"
1.  **Role:** "You are a strict compliance auditor."
2.  **Constraint:** "Answer ONLY using the excerpts provided below. Do not use outside knowledge."
3.  **Refusal:** "If the answer is not in the text, reply: 'I cannot find this in our policy documents.'"
4.  **Citation:** "Cite every statement using [doc_id]."

### 3.2 Context Formatting
Structure the injected context clearly to prevent "context bleeding":

```text
### Retrieved Context ###

[Chunk 1 (ISP-001, Access Control)]:
"...Users must lock screens after 5 mins..."

[Chunk 2 (ISP-002, Remote Work)]:
"...VPN is mandatory for public Wi-Fi..."

### End Context ###
```

### 3.3 Chain of Thought (CoT)
For complex queries (e.g., "Can I use a personal USB drive?"), instruct the model to:
> "First, identify the relevant policy clauses. Second, compare them to the user's scenario. Third, verify if an exception process exists. Finally, state the conclusion."

---

## Stage 4: Quantitative Evaluation (Eval Ops)

We move from "it feels right" to "it scores 92%". Use **Azure AI Foundry Prompt Flow**.

### 4.1 The "Golden Dataset"
Create a CSV with 50+ question-answer pairs:
*   **Columns:** `question`, `expected_answer`, `expected_citation_ids`.
*   **Standard:** Verified correct by a Security Policy Owner.

### 4.2 Metrics
*   **Groundedness (1-5):** Does the answer rely *only* on the context? (Automated via GPT-4 evaluator).
*   **Relevance (1-5):** Did retrieval find the right chunks? (Recall@K).
*   **Citation Accuracy:** (Binary) Did the answer cite the `expected_citation_ids`?
*   **Coherence:** Is the answer readable?

### 4.3 Regression Testing
*   **Trigger:** Any change to Chunk Size, Prompt, or Index config.
*   **Gate:** New Score must be >= Baseline Score.

---

## Stage 5: Continuous Improvement Loop

RAG is never "done".

### 5.1 User Feedback
*   UI must have **Thumbs Up / Thumbs Down**.
*   **Logic:**
    *   👍 -> Positive signal (save as potential Golden Dataset candidate).
    *   👎 -> Negative signal (Human Review required).
*   **"No Answer" Analysis:** Track queries that returned the "I cannot find..." refusal.
    *   *Cause A:* Missing policy? -> Create new doc.
    *   *Cause B:* Bad retrieval? -> Tune synonyms/search.

### 5.2 Content Freshness
*   **Automated Re-indexing:**
    *   Blob Trigger (Event Grid) updates the index immediately when a PDF is replaced.
    *   **Stale Data Removal:** Indexer must **soft-delete** or purge chunks from old document versions (ensure `delete` logic handles chunks, not just files).

---

## Summary Checklist

- [ ] **Ingestion:** Tables are parsed correctly (Layout model).
- [ ] **Chunking:** Section headers are preserved in context.
- [ ] **Retrieval:** Semantic Reranker is ENABLED.
- [ ] **Prompt:** System prompt enforces "No Outside Knowledge".
- [ ] **Eval:** A Golden Dataset of 50 questions exists.
- [ ] **Feedback:** "Thumbs Down" events notify the engineering team.