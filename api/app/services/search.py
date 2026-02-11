"""
Azure AI Search client wrapper.

Implements hybrid search (keyword + vector) with security trimming
and optional semantic reranking.
"""

import logging
from dataclasses import dataclass

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryType,
    VectorizedQuery,
)

from app.core.config import Settings
from app.core.telemetry import get_tracer

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from the index."""

    chunk_id: str
    content: str
    title: str
    source_uri: str
    score: float


class PolicySearchService:
    """Wrapper around Azure AI Search for policy document retrieval."""

    def __init__(self, settings: Settings) -> None:
        credential = DefaultAzureCredential()
        self._client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=settings.azure_search_index_name,
            credential=credential,
        )
        self._tracer = get_tracer()

    def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float],
        user_groups: list[str],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """
        Execute a hybrid search with security trimming.

        Args:
            query_text: The user's natural language query.
            query_vector: The embedded query vector.
            user_groups: Entra ID group IDs for security filtering.
            top_k: Number of results to return.

        Returns:
            List of SearchResult ordered by relevance.
        """
        with self._tracer.start_as_current_span("search.hybrid") as span:
            # Build security filter
            security_filter = self._build_security_filter(user_groups)
            span.set_attribute("search.filter", security_filter)
            span.set_attribute("search.top_k", top_k)

            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=50,
                fields="content_vector",
            )

            results = self._client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=security_filter,
                select=["id", "content", "title", "source_uri"],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                top=top_k,
            )

            search_results = []
            for doc in results:
                search_results.append(
                    SearchResult(
                        chunk_id=doc["id"],
                        content=doc["content"],
                        title=doc.get("title", "Unknown"),
                        source_uri=doc.get("source_uri", ""),
                        score=doc.get("@search.score", 0.0),
                    )
                )

            span.set_attribute("search.results_count", len(search_results))
            logger.info(
                "Hybrid search returned %d results (filter: %s)",
                len(search_results),
                security_filter,
            )
            return search_results

    @staticmethod
    def _build_security_filter(user_groups: list[str]) -> str:
        """
        Build an OData security filter from Entra ID group claims.

        Returns documents that are either Public or match the user's groups.
        """
        if not user_groups:
            return "classification eq 'Public'"

        safe_groups = ",".join(f"'{g}'" for g in user_groups)
        return (
            f"classification eq 'Public' or "
            f"allowed_groups/any(g: search.in(g, '{safe_groups}'))"
        )
