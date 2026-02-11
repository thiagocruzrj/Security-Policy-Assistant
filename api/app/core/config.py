"""
Configuration module using Pydantic Settings.

Loads all Azure service endpoints and deployment names from environment
variables. Supports .env files for local development.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_api_version: str = "2024-06-01"

    # Azure AI Search
    azure_search_endpoint: str
    azure_search_index_name: str = "security-policies-idx"

    # Application Insights
    applicationinsights_connection_string: str = ""

    # App
    log_level: str = "INFO"
    allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


def get_settings() -> Settings:
    """Factory for cached settings instance."""
    return Settings()
