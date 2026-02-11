"""
Semantic chunking module for policy documents.

Splits extracted text by markdown headings to preserve section context.
Falls back to recursive character splitting for oversized sections.
"""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single text chunk with its metadata."""

    text: str
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0


def semantic_chunk(
    text: str,
    max_chunk_size: int = 1000,
    overlap: int = 100,
    source_file: str = "",
) -> list[Chunk]:
    """
    Split text into semantic chunks by headings.

    Strategy:
    1. Split by markdown headings (##, ###).
    2. If a section exceeds max_chunk_size characters, recursively split
       by paragraph boundaries with overlap.
    3. Each chunk inherits its heading path as metadata.

    Args:
        text: The full document text (markdown or plain text).
        max_chunk_size: Maximum characters per chunk.
        overlap: Character overlap between consecutive sub-chunks.
        source_file: Original file name for metadata.

    Returns:
        List of Chunk objects with text and metadata.
    """
    sections = _split_by_headings(text)
    chunks: list[Chunk] = []
    chunk_idx = 0

    for section in sections:
        heading = section["heading"]
        content = section["content"].strip()
        if not content:
            continue

        # Prepend heading as context for each chunk
        prefix = f"[{heading}] " if heading else ""

        if len(content) <= max_chunk_size:
            chunks.append(
                Chunk(
                    text=prefix + content,
                    metadata={
                        "heading": heading,
                        "source_file": source_file,
                    },
                    chunk_index=chunk_idx,
                )
            )
            chunk_idx += 1
        else:
            # Recursively split oversized sections
            sub_chunks = _recursive_split(content, max_chunk_size, overlap)
            for sub in sub_chunks:
                chunks.append(
                    Chunk(
                        text=prefix + sub,
                        metadata={
                            "heading": heading,
                            "source_file": source_file,
                        },
                        chunk_index=chunk_idx,
                    )
                )
                chunk_idx += 1

    return chunks


def _split_by_headings(text: str) -> list[dict]:
    """Split text into sections by markdown headings (## or ###)."""
    pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    sections: list[dict] = []
    last_end = 0
    current_heading = ""

    for match in pattern.finditer(text):
        # Capture content before this heading
        content = text[last_end : match.start()]
        if content.strip():
            sections.append({"heading": current_heading, "content": content})

        current_heading = match.group(2).strip()
        last_end = match.end()

    # Capture remaining content
    remaining = text[last_end:]
    if remaining.strip():
        sections.append({"heading": current_heading, "content": remaining})

    # If no headings found, return the entire text as one section
    if not sections:
        sections.append({"heading": "", "content": text})

    return sections


def _recursive_split(
    text: str, max_size: int, overlap: int
) -> list[str]:
    """Split text by paragraph boundaries with overlap."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 2 <= max_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # Start new chunk with overlap from previous
            if overlap > 0 and current:
                overlap_text = current[-overlap:]
                current = overlap_text + "\n\n" + para
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks
