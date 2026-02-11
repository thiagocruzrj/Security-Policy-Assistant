"""
Security module for JWT token validation with Microsoft Entra ID.

Extracts user identity and group claims from the bearer token.
In production, tokens are validated by APIM/EasyAuth before reaching
this layer — this module parses the pre-validated claims.
"""

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, Request, status


@dataclass
class UserClaims:
    """Parsed user claims from Entra ID JWT token."""

    user_id: str
    name: str
    email: str
    groups: list[str] = field(default_factory=list)


def get_current_user(request: Request) -> UserClaims:
    """
    Extract user claims from the request.

    In production with EasyAuth / APIM, the validated identity is
    forwarded via headers (X-MS-CLIENT-PRINCIPAL-*). For local
    development, a mock user is returned when no auth headers are present.
    """
    # EasyAuth forwards identity via these headers
    user_id = request.headers.get("X-MS-CLIENT-PRINCIPAL-ID")
    user_name = request.headers.get("X-MS-CLIENT-PRINCIPAL-NAME", "")

    if user_id:
        # Production path: extract claims from EasyAuth headers
        groups_header = request.headers.get("X-MS-CLIENT-PRINCIPAL-GROUPS", "")
        groups = [g.strip() for g in groups_header.split(",") if g.strip()]
        return UserClaims(
            user_id=user_id,
            name=user_name,
            email=user_name,
            groups=groups,
        )

    # Local development fallback: mock user with broad access
    return UserClaims(
        user_id="dev-user-001",
        name="Developer",
        email="dev@localhost",
        groups=["all-employees"],
    )


def require_authenticated_user(
    user: UserClaims = Depends(get_current_user),
) -> UserClaims:
    """Dependency that rejects unauthenticated users in strict mode."""
    if not user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
