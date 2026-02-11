"""
FastAPI application entrypoint.

Registers routers, configures CORS, initializes telemetry,
and creates service instances on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.telemetry import setup_telemetry
from app.routers import chat, health
from app.services.openai_client import OpenAIService
from app.services.rag import RAGOrchestrator
from app.services.search import PolicySearchService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """
    Application lifespan handler.
    Initializes service clients on startup, cleans up on shutdown.
    """
    settings = get_settings()

    # Configure logging
    logging.basicConfig(level=settings.log_level)

    # Initialize telemetry
    setup_telemetry(settings.applicationinsights_connection_string)

    # Initialize service clients
    search_service = PolicySearchService(settings)
    openai_service = OpenAIService(settings)
    rag_orchestrator = RAGOrchestrator(search_service, openai_service)

    # Store in app state for dependency injection
    application.state.rag_orchestrator = rag_orchestrator

    logger.info("Security Policy Assistant API started.")
    yield
    logger.info("Security Policy Assistant API shutting down.")


app = FastAPI(
    title="Security Policy Assistant API",
    description="RAG-powered assistant for querying internal security policies.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(chat.router)
