"""Runtime service accessors for shared services across API modules.

This module provides convenient access to services managed by the StateManager.
All services are initialized and managed by the StateManager during application startup.
"""

from typing import Any

from ..core.state import get_state_manager

# Mapping of service names to StateManager properties
_SERVICE_MAPPING = {
    "sse_manager": "sse_manager",
    "match_logger": "match_logger",
    "session_manager": "session_manager",
    "admin_service": "admin_service",
    "db_service": "db_service",
}


def __getattr__(name: str) -> Any:
    """Lazy service accessor using module-level __getattr__.

    This provides backward compatibility with the previous singleton approach
    while using the centralized StateManager.

    Args:
        name: Service name

    Returns:
        Service instance from StateManager

    Raises:
        AttributeError: If service name is not recognized
        RuntimeError: If StateManager is not initialized
    """
    if name in _SERVICE_MAPPING:
        state_manager = get_state_manager()
        return getattr(state_manager, _SERVICE_MAPPING[name])

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

