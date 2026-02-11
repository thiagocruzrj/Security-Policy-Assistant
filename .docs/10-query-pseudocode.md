# Query Pipeline Logic (RAG Engine)

## Overview

This document serves as the implementation guide for the **Query Engine**. The goal is to take a raw user question and return a policy-grounded answer with strict citations. The pipeline emphasizes **security trimming**, **hybrid retrieval quality**, and **hallucination prevention**.

---

## 1. Core Logic Flow (`api/rag.py`)

```python
import openai
from azure.search.documents import SearchClient, VectorizedQuery
from azure.search.documents.models import QueryType, VectorFilterMode

def ask_policy_assistant(user_query: str, user_claims: dict):
    """
    Main RAG orchestrator.
    :param user_query: The raw string from the chat UI.
    :param user_claims: Decoded JWT token with 'groups' and 'oid'.
    """
    try:
        # 1. Expand Query (Synonyms / Intent)
        search_intent = generated_search_queries(user_query) or user_query
        
        # 2. Embed Query
        query_vector = embed_text(search_intent)
        
        # 3. Build Security Filter (CRITICAL)
        security_filter = build_security_filter(user_claims['groups'])
        
        # 4. Hybrid Retrieval + Semantic Rerank
        raw_results = search_client.search(
            search_text=search_intent,
            vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=50, fields="content_vector")],
            filter=security_filter,
            select=["id", "content", "title", "source_uri", "chunk_id"],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="default",
            top=5
        )
        
        # 5. Format Context
        context_str, sources = format_context(raw_results)
        
        # 6. Generate Answer (Streaming)
        answer_stream = call_llm(context_str, user_query)
        
        # 7. Post-Process (Citation Check)
        final_answer = validate_citations(answer_stream, sources)
        
        return final_answer
        
    except Exception as e:
        log_error(e)
        return "I encountered an error retrieving the policy. Please try again."
```

---

## 2. Detailed Steps

### 2.1 Security Trimming (`build_security_filter`)

**Goal:** Ensure the query *only* sees documents the user is allowed to access.
**Logic:** Use OData `search.in()` for performance with many groups.

```python
def build_security_filter(user_groups: list[str]) -> str:
    # 1. Always include 'Public' docs (no group requirement)
    # 2. OR match any of the user's groups in 'allowed_groups'
    
    # Escape group IDs just in case (though GUIDs are safe)
    safe_groups = ",".join([f"'{g}'" for g in user_groups])
    
    # OData Syntax:
    # classification eq 'Public' or allowed_groups/any(g: search.in(g, 'group1,group2'))
    return f"classification eq 'Public' or allowed_groups/any(g: search.in(g, '{safe_groups}'))"
```

### 2.2 Semantic Reranking Configuration

Passed to `search_client.search()`:
*   `query_type=QueryType.SEMANTIC`
*   `semantic_configuration_name="default"` (Matches index definition)
*   `query_caption="extractive"`: (Optional) Get highlighted snippets.
*   `query_answer="extractive"`: (Optional) Get a direct answer from the top doc.

### 2.3 Context Formatting (`format_context`)

**Goal:** Present chunks clearly to the LLM.
**Format:**
```text
[doc1]: (Source: Password_Policy.pdf) Content...
[doc2]: (Source: Remote_Work_Standard.pdf) Content...
```

```python
def format_context(results):
    context_parts = []
    sources = {}
    for i, doc in enumerate(results):
        doc_tag = f"[doc{i+1}]"
        content = doc['content'].replace("\n", " ") # Clean up newlines
        context_parts.append(f"{doc_tag} (Source: {doc['title']}): {content}")
        sources[doc_tag] = {"id": doc['id'], "uri": doc['source_uri']}
    
    return "\n\n".join(context_parts), sources
```

### 2.4 System Prompt (`call_llm`)

```python
SYSTEM_PROMPT = """
You are an expert Security Policy Assistant. 
Roles:
1. Answer the user question logic using ONLY the provided context.
2. If the answer is not in the context, state "I cannot find this information in the provided policies."
3. CITE your sources using the [docN] format logic at the end of each sentence.

Constraint:
- Do NOT use outside knowledge (e.g. from the internet).
- Do NOT generate markdown links, use the [docN] citation format.
"""

def call_llm(context, query):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]
    # Call OpenAI ChatCompletion (stream=True recommended for UX)
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.0 # Strict!
    )
```

---

## 3. Citation Verification (The Guardrail)

**Goal:** Prevent hallucinations where the model generates a plausible but fake citation.

```python
import re

def validate_citations(answer_text, valid_sources):
    # Regex to find [doc1], [doc2], etc.
    citations = re.findall(r"\[doc\d+\]", answer_text)
    
    valid_citations = []
    for cite in citations:
        if cite in valid_sources:
            valid_citations.append(valid_sources[cite])
            
    if not valid_citations and "I cannot find" not in answer_text:
        # Potential Hallucination - Log warning
        logging.warning("Answer generated without citations.")
        # Optional: Force a standard refusal or append a disclaimer
        return answer_text + "\n(Note: No specific policy text was cited.)"
        
    return answer_text
```

---

## Summary Checklist

- [ ] **Security Filter:** Applied *before* retrieval.
- [ ] **Hybrid Search:** Vector + Keyword + Semantic Rerank enabled.
- [ ] **Prompt:** System prompt enforces "No Outside Knowledge".
- [ ] **Citations:** Output format `[docN]` is strictly parsed and verified.