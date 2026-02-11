"""
Indexing module for Azure AI Search.

Handles idempotent upsert of document chunks with deterministic IDs.
"""

import base64
import hashlib
import logging
import os
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

logger = logging.getLogger(__name__)

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "security-policies-idx")


def get_search_client() -> SearchClient:
    """Create an Azure AI Search client with Entra ID auth."""
    return SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
        credential=DefaultAzureCredential(),
    )


def generate_chunk_id(source_uri: str, chunk_index: int) -> str:
    """
    Generate a deterministic, URL-safe ID for a chunk.

    Using SHA-256 hash of (source_uri + chunk_index) ensures:
    - Idempotent re-processing (same file → same IDs).
    - No collisions across different files.
    """
    raw = f"{source_uri}_chunk_{chunk_index}"
    hash_bytes = hashlib.sha256(raw.encode()).digest()
    return base64.urlsafe_b64encode(hash_bytes).decode().rstrip("=")


def upsert_chunks(
    chunks: list[dict],
    vectors: list[list[float]],
    source_uri: str,
    title: str,
    allowed_groups: list[str] | None = None,
    classification: str = "Internal",
) -> int:
    """
    Upsert chunks with their vectors into the search index.

    Uses mergeOrUpload action for idempotency — re-running the
    ingestion pipeline updates existing chunks instead of duplicating.

    Args:
        chunks: List of chunk dicts with 'text' and 'metadata' keys.
        vectors: Corresponding embedding vectors.
        source_uri: URI of the source document in Blob Storage.
        title: Document title (filename).
        allowed_groups: Entra ID group IDs that can access this document.
        classification: Data classification (Public, Internal, Confidential).

    Returns:
        Number of documents upserted.
    """
    client = get_search_client()
    if allowed_groups is None:
        allowed_groups = ["all-employees"]

    documents = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        chunk_id = generate_chunk_id(source_uri, i)
        doc = {
            "@search.action": "mergeOrUpload",
            "id": chunk_id,
            "content": chunk["text"],
            "content_vector": vector,
            "title": title,
            "source_uri": source_uri,
            "chunk_id": i,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "classification": classification,
            "allowed_groups": allowed_groups,
        }
        documents.append(doc)

    # Batch upload (SDK handles chunking into 1000-doc batches)
    result = client.upload_documents(documents=documents)
    succeeded = sum(1 for r in result if r.succeeded)

    logger.info(
        "Upserted %d/%d chunks for '%s'", succeeded, len(documents), title
    )
    return succeeded


def delete_document_chunks(source_uri: str) -> int:
    """
    Delete all chunks for a given source document.

    Used when a document is removed from Blob Storage.
    """
    client = get_search_client()

    # Find all chunks for this document
    results = client.search(
        search_text="*",
        filter=f"source_uri eq '{source_uri}'",
        select=["id"],
        top=1000,
    )

    doc_ids = [{"id": doc["id"]} for doc in results]
    if not doc_ids:
        logger.info("No chunks found for '%s'", source_uri)
        return 0

    result = client.delete_documents(documents=doc_ids)
    deleted = sum(1 for r in result if r.succeeded)
    logger.info("Deleted %d chunks for '%s'", deleted, source_uri)
    return deleted
