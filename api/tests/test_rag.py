"""
Unit tests for the RAG orchestrator.

Tests the core pipeline logic with mocked Azure services.
"""

import pytest

from app.core.security import UserClaims
from app.models.chat import ChatMessage
from app.services.rag import RAGOrchestrator, REFUSAL_MESSAGE


class MockSearchResult:
    def __init__(self, chunk_id, content, title, source_uri, score):
        self.chunk_id = chunk_id
        self.content = content
        self.title = title
        self.source_uri = source_uri
        self.score = score


class MockSearchService:
    """Mock Azure AI Search service."""

    def __init__(self, results=None):
        self._results = results or []

    def hybrid_search(self, query_text, query_vector, user_groups, top_k=5):
        return self._results


class MockOpenAIService:
    """Mock Azure OpenAI service."""

    def __init__(self, answer="Test answer [doc1]", embedding=None):
        self._answer = answer
        self._embedding = embedding or [0.1] * 1536
        self._settings = type("S", (), {"azure_openai_chat_deployment": "gpt-4o"})()

    def embed_text(self, text):
        return self._embedding

    def chat_completion(self, messages, temperature=0.0):
        return self._answer, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}


@pytest.fixture
def user():
    return UserClaims(
        user_id="test-user",
        name="Test User",
        email="test@example.com",
        groups=["all-employees"],
    )


@pytest.fixture
def sample_results():
    return [
        MockSearchResult(
            chunk_id="chunk-1",
            content="All passwords must be at least 12 characters.",
            title="Password_Policy.pdf",
            source_uri="https://storage/policy-docs/Password_Policy.pdf",
            score=0.95,
        ),
        MockSearchResult(
            chunk_id="chunk-2",
            content="MFA is required for VPN access.",
            title="Access_Control_Policy.pdf",
            source_uri="https://storage/policy-docs/Access_Control_Policy.pdf",
            score=0.88,
        ),
    ]


@pytest.mark.asyncio
async def test_answer_with_citations(user, sample_results):
    """Test that a valid answer with citations is returned."""
    search = MockSearchService(results=sample_results)
    openai = MockOpenAIService(answer="Passwords must be 12 characters [doc1].")
    rag = RAGOrchestrator(search, openai)

    messages = [ChatMessage(role="user", content="What is the password policy?")]
    response = await rag.answer(messages, user)

    assert "12 characters" in response.answer
    assert len(response.citations) == 1
    assert response.citations[0].tag == "[doc1]"
    assert response.retrieval_count == 2


@pytest.mark.asyncio
async def test_no_results_returns_refusal(user):
    """Test that empty retrieval returns a refusal message."""
    search = MockSearchService(results=[])
    openai = MockOpenAIService()
    rag = RAGOrchestrator(search, openai)

    messages = [ChatMessage(role="user", content="How do I bake a cake?")]
    response = await rag.answer(messages, user)

    assert response.answer == REFUSAL_MESSAGE
    assert response.retrieval_count == 0


@pytest.mark.asyncio
async def test_no_citations_triggers_refusal(user, sample_results):
    """Test that answers without citations are replaced with refusal."""
    search = MockSearchService(results=sample_results)
    openai = MockOpenAIService(answer="Passwords should be strong.")  # No [docN]
    rag = RAGOrchestrator(search, openai)

    messages = [ChatMessage(role="user", content="Password policy?")]
    response = await rag.answer(messages, user)

    assert response.answer == REFUSAL_MESSAGE


@pytest.mark.asyncio
async def test_format_context():
    """Test context formatting produces correct doc tags."""
    results = [
        MockSearchResult("c1", "Content one", "Doc1.pdf", "uri1", 0.9),
        MockSearchResult("c2", "Content two", "Doc2.pdf", "uri2", 0.8),
    ]
    context, sources = RAGOrchestrator._format_context(results)

    assert "[doc1]" in context
    assert "[doc2]" in context
    assert "Doc1.pdf" in context
    assert "[doc1]" in sources
    assert sources["[doc1]"].chunk_id == "c1"
