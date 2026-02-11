"""
Embedding module for batch vector generation.

Uses Azure OpenAI text-embedding-3-small model via DefaultAzureCredential.
"""

import logging
import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# Configuration from environment
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
EMBEDDING_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
)
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")


def get_openai_client() -> AzureOpenAI:
    """Create an Azure OpenAI client with Entra ID auth."""
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=API_VERSION,
    )


def generate_embeddings(
    texts: list[str],
    batch_size: int = 16,
) -> list[list[float]]:
    """
    Generate embedding vectors for a list of texts.

    Processes in batches to avoid API limits.

    Args:
        texts: List of text strings to embed.
        batch_size: Number of texts per API call.

    Returns:
        List of embedding vectors (same order as input).
    """
    client = get_openai_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.info("Embedding batch %d/%d (%d items)", i // batch_size + 1,
                     (len(texts) + batch_size - 1) // batch_size, len(batch))

        response = client.embeddings.create(
            input=batch,
            model=EMBEDDING_DEPLOYMENT,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    logger.info("Generated %d embeddings total.", len(all_embeddings))
    return all_embeddings
