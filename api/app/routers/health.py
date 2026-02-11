"""
Health router — GET /health endpoint.

Used by Container Apps liveness/readiness probes and
load balancer health checks.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Return a simple health status for probes."""
    return {"status": "healthy", "service": "security-policy-assistant"}
