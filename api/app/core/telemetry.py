"""
Telemetry module for OpenTelemetry + Application Insights.

Configures distributed tracing and custom metrics for the RAG pipeline.
"""

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanExporter

logger = logging.getLogger(__name__)

_tracer: trace.Tracer | None = None


def setup_telemetry(connection_string: str) -> None:
    """
    Initialize OpenTelemetry with Application Insights exporter.

    Args:
        connection_string: Application Insights connection string.
                          If empty, telemetry is disabled (local dev).
    """
    global _tracer

    resource = Resource.create({"service.name": "security-policy-assistant"})
    provider = TracerProvider(resource=resource)

    if connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import (
                AzureMonitorTraceExporter,
            )

            exporter = AzureMonitorTraceExporter(
                connection_string=connection_string
            )
            provider.add_span_processor(BatchSpanExporter(exporter))
            logger.info("Application Insights telemetry enabled.")
        except ImportError:
            logger.warning(
                "azure-monitor-opentelemetry-exporter not installed. "
                "Telemetry will not be exported."
            )
    else:
        logger.info("No connection string provided. Telemetry export disabled.")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("security-policy-assistant")


def get_tracer() -> trace.Tracer:
    """Return the application tracer, initializing a no-op if not set up."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("security-policy-assistant")
    return _tracer
