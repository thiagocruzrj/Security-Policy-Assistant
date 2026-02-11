"""
Azure OpenAI client wrapper.

Handles embedding generation and chat completions with retry logic.
Uses DefaultAzureCredential (Managed Identity in production, az login locally).
"""

import logging

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from app.core.config import Settings
from app.core.telemetry import get_tracer

logger = logging.getLogger(__name__)


class OpenAIService:
    """Wrapper around Azure OpenAI for embeddings and chat completions."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._tracer = get_tracer()

        # Use Entra ID token-based auth (no API keys)
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )

    def embed_text(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to embed (query or chunk).

        Returns:
            A list of floats representing the embedding vector.
        """
        with self._tracer.start_as_current_span("openai.embed") as span:
            span.set_attribute("openai.model", self._settings.azure_openai_embedding_deployment)
            response = self._client.embeddings.create(
                input=[text],
                model=self._settings.azure_openai_embedding_deployment,
            )
            return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors (same order as input).
        """
        with self._tracer.start_as_current_span("openai.embed_batch") as span:
            span.set_attribute("openai.batch_size", len(texts))
            response = self._client.embeddings.create(
                input=texts,
                model=self._settings.azure_openai_embedding_deployment,
            )
            return [item.embedding for item in response.data]

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> tuple[str, dict]:
        """
        Generate a chat completion.

        Args:
            messages: The conversation messages (system + user + context).
            temperature: Sampling temperature (0.0 = deterministic).

        Returns:
            Tuple of (answer_text, usage_metadata).
        """
        with self._tracer.start_as_current_span("openai.chat") as span:
            span.set_attribute("openai.model", self._settings.azure_openai_chat_deployment)
            span.set_attribute("openai.temperature", temperature)

            response = self._client.chat.completions.create(
                model=self._settings.azure_openai_chat_deployment,
                messages=messages,
                temperature=temperature,
            )

            answer = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            span.set_attribute("openai.prompt_tokens", usage["prompt_tokens"])
            span.set_attribute("openai.completion_tokens", usage["completion_tokens"])
            logger.info("Chat completion: %d tokens used", usage["total_tokens"])

            return answer, usage
