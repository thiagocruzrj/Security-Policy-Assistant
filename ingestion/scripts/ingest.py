"""
Document ingestion CLI script.

Extracts text from a PDF, chunks it semantically, generates embeddings,
and upserts chunks to the Azure AI Search index.

Usage:
    python ingestion/scripts/ingest.py --file "./sample_policies/example.pdf"
    python ingestion/scripts/ingest.py --file "./docs/policy.pdf" --classification Confidential
"""

import argparse
import logging
import os
import sys

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pypdf import PdfReader

from shared.chunking import semantic_chunk
from shared.embedding import generate_embeddings
from shared.indexing import upsert_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF using pypdf."""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append(f"## Page {i + 1}\n\n{text}")
    return "\n\n".join(pages)


def ingest_document(
    file_path: str,
    classification: str = "Internal",
    allowed_groups: list[str] | None = None,
) -> None:
    """
    Full ingestion pipeline for a single document.

    Steps:
    1. Extract text from PDF.
    2. Chunk by headings with overlap.
    3. Generate embeddings in batches.
    4. Upsert to Azure AI Search index.
    """
    if not os.path.exists(file_path):
        logger.error("File not found: %s", file_path)
        return

    filename = os.path.basename(file_path)
    logger.info("Starting ingestion for '%s'", filename)

    # Step 1: Extract text
    logger.info("Extracting text...")
    text = extract_text_from_pdf(file_path)
    logger.info("Extracted %d characters from %s", len(text), filename)

    if not text.strip():
        logger.warning("No text extracted from '%s'. Skipping.", filename)
        return

    # Step 2: Chunk
    logger.info("Chunking text...")
    chunks = semantic_chunk(text, max_chunk_size=1000, overlap=100, source_file=filename)
    logger.info("Created %d chunks", len(chunks))

    # Step 3: Embed
    logger.info("Generating embeddings...")
    chunk_texts = [c.text for c in chunks]
    vectors = generate_embeddings(chunk_texts, batch_size=16)

    # Step 4: Upsert
    logger.info("Upserting to search index...")
    chunk_dicts = [{"text": c.text, "metadata": c.metadata} for c in chunks]

    # Construct source URI (would be blob URL in production)
    source_uri = f"https://storage.blob.core.windows.net/policy-docs/{filename}"

    succeeded = upsert_chunks(
        chunks=chunk_dicts,
        vectors=vectors,
        source_uri=source_uri,
        title=filename,
        allowed_groups=allowed_groups or ["all-employees"],
        classification=classification,
    )

    logger.info(
        "Ingestion complete: %d/%d chunks indexed for '%s'",
        succeeded, len(chunks), filename,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a policy document into Azure AI Search"
    )
    parser.add_argument(
        "--file", required=True, help="Path to the PDF file to ingest"
    )
    parser.add_argument(
        "--classification",
        default="Internal",
        choices=["Public", "Internal", "Confidential"],
        help="Data classification level (default: Internal)",
    )
    parser.add_argument(
        "--groups",
        nargs="*",
        default=["all-employees"],
        help="Entra ID group IDs that can access this document",
    )

    args = parser.parse_args()
    ingest_document(
        file_path=args.file,
        classification=args.classification,
        allowed_groups=args.groups,
    )


if __name__ == "__main__":
    main()
