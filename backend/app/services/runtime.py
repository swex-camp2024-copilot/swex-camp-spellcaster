"""Runtime singletons for shared services across API modules."""

from .sse_manager import SSEManager
from .session_manager import SessionManager

# Shared instances used by API routers
sse_manager = SSEManager()
session_manager = SessionManager(sse_manager=sse_manager)

