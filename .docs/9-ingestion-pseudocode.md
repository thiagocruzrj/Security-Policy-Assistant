# Ingestion Pipeline Logic (Production Grade)

## Overview

This document details the **Python logic** required to reliably process policy documents into the Azure AI Search index. It moves beyond simple "read-and-embed" to handle **layout analysis**, **smart chunking**, **idempotency**, and **resilience**.

---

## 1. Core Logic Flow

```python
import logging
import hashlib
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.search.documents import SearchClient
from azure.storage.blob import BlobClient
from openai import AzureOpenAI

# Configuration
CHUNK_SIZE = 512  # Tokens
CHUNK_OVERLAP = 50 # Tokens
EMBEDDING_MODEL = "text-embedding-3-small"

def process_document(blob_url: str):
    """
    Main entry point triggered by Blob Storage Event.
    """
    try:
        # 1. Acquire Lease (Prevent double processing)
        lease = acquire_blob_lease(blob_url)
        
        # 2. Extract Content (High Fidelity)
        doc_content = extract_with_layout(blob_url)
        
        # 3. Create Semantic Chunks
        chunks = semantic_chunking(doc_content)
        
        # 4. Generate Embeddings (Batch)
        vectors = generate_embeddings([c['text'] for c in chunks])
        
        # 5. Index Upsert (Idempotent)
        upsert_to_search(chunks, vectors, blob_url)
        
        # 6. Release Lease & Tag Blob as 'Indexed'
        tag_blob(blob_url, status="indexed")
        
    except Exception as e:
        logging.error(f"Failed to process {blob_url}: {str(e)}")
        # Move to Dead Letter Queue or Tag as 'Failed'
        tag_blob(blob_url, status="failed", error=str(e))
    finally:
        lease.release()

```

---

## 2. Detailed Extract & Chunk Strategies

### 2.1 extraction: `extract_with_layout`

Using **Azure Document Intelligence**:
```python
def extract_with_layout(blob_url):
    poller = doc_intel_client.begin_analyze_document_from_url(
        "prebuilt-layout", blob_url
    )
    result = poller.result()
    
    markdown_output = ""
    for page in result.pages:
        # Tables are critical in policy docs
        for table in page.tables:
             markdown_output += table_to_markdown(table)
        
        # Merge lines into coherent paragraphs
        for line in page.lines:
             markdown_output += line.content + "\n"
             
    return markdown_output
```

### 2.2 chunking: `semantic_chunking`

Using `langchain.text_splitter.MarkdownHeaderSplitter`: or equivalent custom logic.
```python
def semantic_chunking(markdown_text):
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    splitter = MarkdownHeaderSplitter(headers_to_split_on=headers_to_split_on)
    splits = splitter.split_text(markdown_text)
    
    final_chunks = []
    for split in splits:
        # Further split if content > 512 tokens using RecursiveCharacterTextSplitter
        # This handles massive sections under a single header
        sub_chunks = recursive_splitter.split_text(split.page_content)
        for sub in sub_chunks:
            final_chunks.append({
                "text": sub,
                "metadata": split.metadata # Inherits Header Path
            })
    return final_chunks
```

---

## 3. Embedding & Indexing

### 3.1 Batch Embedding
Calls to OpenAI should be batched (e.g., 16 chunks at a time) to optimize latency/throughput.

```python
def generate_embeddings(text_list):
    response = openai_client.embeddings.create(
        input=text_list,
        model=EMBEDDING_MODEL
    )
    return [data.embedding for data in response.data]
```

### 3.2 Idempotent Upsert
We generate a deterministic ID so re-running the pipeline updates existing chunks instead of creating duplicates.

```python
def upsert_to_search(chunks, vectors, source_url):
    actions = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        # Deterministic ID: Hash(File URL + Chunk Index)
        # Using URL-safe Base64
        chunk_id = base64.urlsafe_b64encode(
            hashlib.sha256(f"{source_url}_{i}".encode()).digest()
        ).decode()
        
        doc = {
            "@search.action": "mergeOrUpload", # Update if exists
            "id": chunk_id,
            "content": chunk['text'],
            "content_vector": vector,
            "source_uri": source_url,
            "title": extract_filename(source_url),
            "allowed_groups": ["group-guid-123"], # Extracted from blob metadata or default
            "classification": "Internal",
            "last_updated": datetime.utcnow().isoformat()
        }
        actions.append(doc)
        
    search_client.upload_documents(documents=actions)
```

---

## 4. Operational Considerations

### 4.1 "Sync" Deletes
If a file `policy-v1.pdf` is deleted from Blob Storage, we must delete its chunks from the Search Index.
*   **Trigger:** Blob Delete Event.
*   **Logic:**
    1.  Query Search Index: `$filter=source_uri eq '.../policy-v1.pdf'`.
    2.  Collect all returned `id`s.
    3.  Call `search_client.delete_documents(keys=[...])`.

### 4.2 Large File Handling
*   **Problem:** Azure Functions have a 5-10 min timeout (Consumption).
*   **Solution:** For large PDFs (>50 pages), the "Extract" function should push pages to a Queue. A separate "Process Page" function picks them up in parallel. (Fan-out/Fan-in pattern).

---

## Summary Checklist

- [ ] **Document Intelligence:** Used for layout/table extraction.
- [ ] **Chunking:** Semantic (Header-aware) + fallback to recursion.
- [ ] **Embedding:** Batched calls.
- [ ] **Search:** Deterministic IDs for idempotency (`mergeOrUpload`).
- [ ] **Cleanup:** Active deletion logic for removed files.