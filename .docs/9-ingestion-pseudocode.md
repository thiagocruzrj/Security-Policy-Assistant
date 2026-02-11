# Ingestion Pseudocode: Policy Docs to Searchable Chunks

This document provides pseudocode for the ingestion pipeline that processes policy documents into searchable, vectorized chunks for Azure AI Search.

## Pseudocode
```python
def ingest_document(blob_uri):
    text = extract_text(blob_uri)          # plain text or Document Intelligence
    chunks = chunk_by_headings(text, overlap=100)

    docs = []
    for i, chunk in enumerate(chunks):
        vec = embed(chunk.text)            # Azure OpenAI embeddings
        docs.append({
            "id": f"{blob_uri}#{i}",
            "policy_id": chunk.policy_id,
            "policy_name": chunk.policy_name,
            "section": chunk.section,
            "content": chunk.text,
            "contentVector": vec,
            "source_uri": blob_uri,
            "classification": chunk.classification,
            "allowed_groups": chunk.allowed_groups,
            "effective_date": chunk.effective_date,
            "version": chunk.version,
            "chunk_id": i,
            "content_hash": sha256(chunk.text),
            "last_indexed_at": now()
        })

    upload_to_ai_search(index="security-policies-idx", documents=docs)
```

## Steps Explained
1. **Extract text** from the policy document (plain text or via Document Intelligence for complex layouts)
2. **Chunk by headings** with overlap for context
3. **Embed each chunk** using Azure OpenAI embeddings
4. **Assemble document metadata** for each chunk
5. **Upload all chunks** to the `security-policies-idx` Azure AI Search index

---
This ingestion flow ensures policy documents are processed into secure, searchable, and semantically rich chunks for enterprise-grade retrieval.