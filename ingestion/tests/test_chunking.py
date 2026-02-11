"""
Unit tests for the semantic chunking module.
"""

import pytest

from shared.chunking import Chunk, semantic_chunk, _split_by_headings, _recursive_split


class TestSemanticChunk:
    def test_single_section_no_headings(self):
        """Text without headings should produce a single chunk."""
        text = "This is a simple paragraph about password policy."
        chunks = semantic_chunk(text, max_chunk_size=1000)
        assert len(chunks) == 1
        assert "password policy" in chunks[0].text

    def test_split_by_headings(self):
        """Text with headings should split into multiple chunks."""
        text = "## Section 1\n\nContent one.\n\n## Section 2\n\nContent two."
        chunks = semantic_chunk(text, max_chunk_size=1000)
        assert len(chunks) == 2
        assert "Section 1" in chunks[0].metadata.get("heading", "")
        assert "Section 2" in chunks[1].metadata.get("heading", "")

    def test_large_section_splits_recursively(self):
        """A section exceeding max_chunk_size should be split further."""
        long_content = "Word " * 500  # ~2500 chars
        text = f"## Large Section\n\n{long_content}"
        chunks = semantic_chunk(text, max_chunk_size=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.metadata["heading"] == "Large Section"

    def test_chunk_index_increments(self):
        """Each chunk should have a unique, incrementing index."""
        text = "## A\n\nContent A.\n\n## B\n\nContent B.\n\n## C\n\nContent C."
        chunks = semantic_chunk(text, max_chunk_size=1000)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_source_file_metadata(self):
        """Source file name should be in chunk metadata."""
        text = "Some policy text."
        chunks = semantic_chunk(text, source_file="test.pdf")
        assert chunks[0].metadata["source_file"] == "test.pdf"


class TestSplitByHeadings:
    def test_multiple_heading_levels(self):
        text = "# H1\n\nContent 1\n\n## H2\n\nContent 2\n\n### H3\n\nContent 3"
        sections = _split_by_headings(text)
        assert len(sections) == 3

    def test_no_headings(self):
        text = "Just plain text without any headings."
        sections = _split_by_headings(text)
        assert len(sections) == 1


class TestRecursiveSplit:
    def test_splits_by_paragraphs(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = _recursive_split(text, max_size=30, overlap=0)
        assert len(chunks) >= 2

    def test_single_paragraph_fits(self):
        text = "Short text."
        chunks = _recursive_split(text, max_size=1000, overlap=0)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."
