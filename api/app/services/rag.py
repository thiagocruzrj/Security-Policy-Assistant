"""
RAG Orchestrator — Core query pipeline.

Coordinates the full Retrieve → Rank → Generate flow:
1. Embed the user query.
2. Build security filter from user's Entra group claims.
3. Execute hybrid search (keyword + vector + semantic rerank).
4. Construct a grounded prompt with retrieved chunks.
5. Call the LLM for generation.
6. Verify citations in the output.
"""

import logging
import re

from app.core.security import UserClaims
from app.core.telemetry import get_tracer
from app.models.chat import ChatMessage, ChatResponse, Citation, Source
from app.services.openai_client import OpenAIService
from app.services.search import PolicySearchService, SearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the **Security Policy Assistant**, an AI that helps employees \
understand internal security policies.

## Rules
1. Answer ONLY using the provided policy excerpts below.
2. If the answer is NOT in the excerpts, respond exactly:
   "I cannot find this information in the available security policies."
3. ALWAYS cite your sources using the [docN] tags shown before each excerpt.
4. Do NOT use your internal knowledge or information from the internet.
5. Be concise, accurate, and professional.
"""

REFUSAL_MESSAGE = (
    "I cannot find this information in the available security policies. "
    "Please contact the Security team for further assistance."
)


class RAGOrchestrator:
    """Orchestrates the full RAG pipeline for policy question answering."""

    def __init__(
        self,
        search_service: PolicySearchService,
        openai_service: OpenAIService,
    ) -> None:
        self._search = search_service
        self._openai = openai_service
        self._tracer = get_tracer()

    async def answer(
        self,
        messages: list[ChatMessage],
        user: UserClaims,
    ) -> ChatResponse:
        """
        Process a user question through the full RAG pipeline.

        Args:
            messages: Conversation history with the latest user message last.
            user: Authenticated user claims with group memberships.

        Returns:
            ChatResponse with grounded answer and citations.
        """
        with self._tracer.start_as_current_span("rag.answer") as span:
            user_query = messages[-1].content
            span.set_attribute("rag.user_id", user.user_id)
            span.set_attribute("rag.query_length", len(user_query))

            # Step 1: Embed the query
            query_vector = self._openai.embed_text(user_query)

            # Step 2: Hybrid search with security trimming
            results = self._search.hybrid_search(
                query_text=user_query,
                query_vector=query_vector,
                user_groups=user.groups,
                top_k=5,
            )
            span.set_attribute("rag.retrieval_count", len(results))

            # Step 3: Handle empty retrieval
            if not results:
                logger.warning("No results retrieved for query from user %s", user.user_id)
                return ChatResponse(answer=REFUSAL_MESSAGE, retrieval_count=0)

            # Step 4: Build grounded prompt
            context_str, source_map = self._format_context(results)
            llm_messages = self._build_messages(context_str, messages)

            # Step 5: Generate answer
            answer_text, usage = self._openai.chat_completion(llm_messages)
            span.set_attribute("rag.tokens_total", usage.get("total_tokens", 0))

            # Step 6: Verify citations
            citations = self._extract_citations(answer_text, source_map)
            final_answer = self._validate_answer(answer_text, citations)

            return ChatResponse(
                answer=final_answer,
                citations=citations,
                retrieval_count=len(results),
                model=self._openai._settings.azure_openai_chat_deployment,
            )

    @staticmethod
    def _format_context(
        results: list[SearchResult],
    ) -> tuple[str, dict[str, Source]]:
        """Format retrieved chunks into a context block with doc tags."""
        parts = []
        source_map: dict[str, Source] = {}
        for i, doc in enumerate(results):
            tag = f"[doc{i + 1}]"
            content = doc.content.replace("\n", " ").strip()
            parts.append(f"{tag} (Source: {doc.title}): {content}")
            source_map[tag] = Source(
                chunk_id=doc.chunk_id,
                title=doc.title,
                source_uri=doc.source_uri,
            )
        return "\n\n".join(parts), source_map

    @staticmethod
    def _build_messages(
        context: str,
        conversation: list[ChatMessage],
    ) -> list[dict[str, str]]:
        """Assemble the LLM message array: system + context + history."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Include up to last 4 prior messages for conversational context
        history = conversation[:-1][-4:]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # User question with retrieved context
        user_query = conversation[-1].content
        messages.append(
            {
                "role": "user",
                "content": f"## Retrieved Policy Excerpts\n\n{context}\n\n## Question\n\n{user_query}",
            }
        )
        return messages

    @staticmethod
    def _extract_citations(
        answer: str,
        source_map: dict[str, Source],
    ) -> list[Citation]:
        """Parse [docN] tags from the answer and map to sources."""
        found_tags = set(re.findall(r"\[doc\d+\]", answer))
        citations = []
        for tag in sorted(found_tags):
            if tag in source_map:
                citations.append(Citation(tag=tag, source=source_map[tag]))
        return citations

    @staticmethod
    def _validate_answer(answer: str, citations: list[Citation]) -> str:
        """
        Validate that the answer contains citations.
        If no citations are found and it's not already a refusal, append a warning.
        """
        is_refusal = "cannot find" in answer.lower()
        if not citations and not is_refusal:
            logger.warning("Answer generated without any citations — potential hallucination.")
            return REFUSAL_MESSAGE
        return answer
