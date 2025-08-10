"""Runtime singletons for shared services across API modules."""

from .sse_manager import SSEManager
from .session_manager import SessionManager
from .match_logger import MatchLogger
from .admin_service import AdminService

# Shared instances used by API routers
sse_manager = SSEManager()
match_logger = MatchLogger()
session_manager = SessionManager(sse_manager=sse_manager, match_logger=match_logger)
admin_service = AdminService(db_service=session_manager._db, session_manager=session_manager)  # reuse DB

