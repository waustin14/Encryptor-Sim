"""RFC 7807 Problem Details error utilities.

Centralized error construction for consistent API error responses.
"""

from typing import Any


def create_rfc7807_error(
    status: int,
    title: str,
    detail: str,
    instance: str,
    error_type: str = "about:blank",
    **extra: Any,
) -> dict[str, Any]:
    """Create an RFC 7807 Problem Details error response.

    Args:
        status: HTTP status code.
        title: Short, human-readable summary of the problem type.
        detail: Human-readable explanation specific to this occurrence.
        instance: URI reference identifying the specific occurrence.
        error_type: URI reference identifying the problem type.
        **extra: Additional members to include in the error response.

    Returns:
        RFC 7807 compliant error dictionary.

    Example:
        >>> create_rfc7807_error(
        ...     status=404,
        ...     title="Not Found",
        ...     detail="Peer with ID 123 not found",
        ...     instance="/api/v1/peers/123"
        ... )
        {
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": "Peer with ID 123 not found",
            "instance": "/api/v1/peers/123"
        }
    """
    error = {
        "type": error_type,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
    }
    error.update(extra)
    return error
