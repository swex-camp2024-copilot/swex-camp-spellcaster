"""Application state management for the Spellcasters Playground Backend.

This module provides centralized state coordination, lifecycle management,
and health monitoring for all backend services.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from ..services.admin_service import AdminService
from ..services.database import DatabaseService
from ..services.match_logger import MatchLogger
from ..services.session_manager import SessionManager
from ..services.sse_manager import SSEManager

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service initialization status."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class StateManager:
    """Centralized application state manager.

    Manages lifecycle, health, and statistics for all backend services.
    Provides dependency injection and service coordination.
    """

    def __init__(self):
        """Initialize the state manager."""
        self._status = ServiceStatus.UNINITIALIZED
        self._startup_time: Optional[datetime] = None
        self._shutdown_time: Optional[datetime] = None
        self._initialization_errors: Dict[str, str] = {}

        # Service instances
        self._db_service: Optional[DatabaseService] = None
        self._sse_manager: Optional[SSEManager] = None
        self._match_logger: Optional[MatchLogger] = None
        self._session_manager: Optional[SessionManager] = None
        self._admin_service: Optional[AdminService] = None

        # Service status tracking
        self._service_status: Dict[str, ServiceStatus] = {
            "database": ServiceStatus.UNINITIALIZED,
            "sse_manager": ServiceStatus.UNINITIALIZED,
            "match_logger": ServiceStatus.UNINITIALIZED,
            "session_manager": ServiceStatus.UNINITIALIZED,
            "admin_service": ServiceStatus.UNINITIALIZED,
        }

    @property
    def status(self) -> ServiceStatus:
        """Get overall state manager status."""
        return self._status

    @property
    def is_ready(self) -> bool:
        """Check if all services are ready."""
        return self._status == ServiceStatus.READY and all(
            status == ServiceStatus.READY for status in self._service_status.values()
        )

    @property
    def db_service(self) -> DatabaseService:
        """Get database service instance."""
        if not self._db_service:
            raise RuntimeError("Database service not initialized")
        return self._db_service

    @property
    def sse_manager(self) -> SSEManager:
        """Get SSE manager instance."""
        if not self._sse_manager:
            raise RuntimeError("SSE manager not initialized")
        return self._sse_manager

    @property
    def match_logger(self) -> MatchLogger:
        """Get match logger instance."""
        if not self._match_logger:
            raise RuntimeError("Match logger not initialized")
        return self._match_logger

    @property
    def session_manager(self) -> SessionManager:
        """Get session manager instance."""
        if not self._session_manager:
            raise RuntimeError("Session manager not initialized")
        return self._session_manager

    @property
    def admin_service(self) -> AdminService:
        """Get admin service instance."""
        if not self._admin_service:
            raise RuntimeError("Admin service not initialized")
        return self._admin_service

    async def initialize(self) -> None:
        """Initialize all services with proper dependency management.

        Raises:
            RuntimeError: If initialization fails
        """
        if self._status != ServiceStatus.UNINITIALIZED:
            logger.warning(f"State manager already initialized with status: {self._status}")
            return

        logger.info("Initializing state manager...")
        self._status = ServiceStatus.INITIALIZING
        self._startup_time = datetime.now()

        try:
            # Initialize database service
            await self._initialize_database()

            # Initialize SSE manager (no dependencies)
            await self._initialize_sse_manager()

            # Initialize match logger (no dependencies)
            await self._initialize_match_logger()

            # Initialize session manager (depends on SSE and match logger)
            await self._initialize_session_manager()

            # Initialize admin service (depends on database and session manager)
            await self._initialize_admin_service()

            # All services initialized successfully
            self._status = ServiceStatus.READY
            logger.info("State manager initialized successfully")

        except Exception as e:
            self._status = ServiceStatus.ERROR
            logger.error(f"State manager initialization failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize state manager: {e}") from e

    async def _initialize_database(self) -> None:
        """Initialize database service."""
        service_name = "database"
        try:
            logger.info(f"Initializing {service_name}...")
            self._service_status[service_name] = ServiceStatus.INITIALIZING

            self._db_service = DatabaseService()
            # Database initialization happens through create_tables() in lifespan

            self._service_status[service_name] = ServiceStatus.READY
            logger.info(f"{service_name} initialized")

        except Exception as e:
            self._service_status[service_name] = ServiceStatus.ERROR
            self._initialization_errors[service_name] = str(e)
            logger.error(f"Failed to initialize {service_name}: {e}")
            raise

    async def _initialize_sse_manager(self) -> None:
        """Initialize SSE manager."""
        service_name = "sse_manager"
        try:
            logger.info(f"Initializing {service_name}...")
            self._service_status[service_name] = ServiceStatus.INITIALIZING

            self._sse_manager = SSEManager()

            self._service_status[service_name] = ServiceStatus.READY
            logger.info(f"{service_name} initialized")

        except Exception as e:
            self._service_status[service_name] = ServiceStatus.ERROR
            self._initialization_errors[service_name] = str(e)
            logger.error(f"Failed to initialize {service_name}: {e}")
            raise

    async def _initialize_match_logger(self) -> None:
        """Initialize match logger."""
        service_name = "match_logger"
        try:
            logger.info(f"Initializing {service_name}...")
            self._service_status[service_name] = ServiceStatus.INITIALIZING

            self._match_logger = MatchLogger()

            self._service_status[service_name] = ServiceStatus.READY
            logger.info(f"{service_name} initialized")

        except Exception as e:
            self._service_status[service_name] = ServiceStatus.ERROR
            self._initialization_errors[service_name] = str(e)
            logger.error(f"Failed to initialize {service_name}: {e}")
            raise

    async def _initialize_session_manager(self) -> None:
        """Initialize session manager."""
        service_name = "session_manager"
        try:
            logger.info(f"Initializing {service_name}...")
            self._service_status[service_name] = ServiceStatus.INITIALIZING

            if not self._sse_manager or not self._match_logger:
                raise RuntimeError("SSE manager and match logger must be initialized first")

            self._session_manager = SessionManager(
                sse_manager=self._sse_manager,
                match_logger=self._match_logger
            )

            self._service_status[service_name] = ServiceStatus.READY
            logger.info(f"{service_name} initialized")

        except Exception as e:
            self._service_status[service_name] = ServiceStatus.ERROR
            self._initialization_errors[service_name] = str(e)
            logger.error(f"Failed to initialize {service_name}: {e}")
            raise

    async def _initialize_admin_service(self) -> None:
        """Initialize admin service."""
        service_name = "admin_service"
        try:
            logger.info(f"Initializing {service_name}...")
            self._service_status[service_name] = ServiceStatus.INITIALIZING

            if not self._db_service or not self._session_manager:
                raise RuntimeError("Database service and session manager must be initialized first")

            self._admin_service = AdminService(
                db_service=self._db_service,
                session_manager=self._session_manager
            )

            self._service_status[service_name] = ServiceStatus.READY
            logger.info(f"{service_name} initialized")

        except Exception as e:
            self._service_status[service_name] = ServiceStatus.ERROR
            self._initialization_errors[service_name] = str(e)
            logger.error(f"Failed to initialize {service_name}: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown all services.

        Performs cleanup in reverse dependency order.
        """
        if self._status == ServiceStatus.SHUTDOWN:
            logger.warning("State manager already shutdown")
            return

        logger.info("Shutting down state manager...")
        self._shutdown_time = datetime.now()

        # Shutdown in reverse order of initialization
        try:
            # Shutdown admin service
            if self._admin_service:
                logger.info("Shutting down admin service...")
                self._service_status["admin_service"] = ServiceStatus.SHUTDOWN

            # Shutdown session manager
            if self._session_manager:
                logger.info("Shutting down session manager...")
                # Terminate all active sessions
                session_ids = await self._session_manager.list_active_sessions()
                for session_id in session_ids:
                    try:
                        await self._session_manager.terminate_session(session_id)
                    except Exception as e:
                        logger.error(f"Error terminating session {session_id}: {e}")
                self._service_status["session_manager"] = ServiceStatus.SHUTDOWN

            # Shutdown match logger
            if self._match_logger:
                logger.info("Shutting down match logger...")
                self._service_status["match_logger"] = ServiceStatus.SHUTDOWN

            # Shutdown SSE manager
            if self._sse_manager:
                logger.info("Shutting down SSE manager...")
                # Disconnect all SSE connections
                await self._sse_manager.disconnect_all()
                self._service_status["sse_manager"] = ServiceStatus.SHUTDOWN

            # Shutdown database service
            if self._db_service:
                logger.info("Shutting down database service...")
                self._service_status["database"] = ServiceStatus.SHUTDOWN

            self._status = ServiceStatus.SHUTDOWN
            logger.info("State manager shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            raise

    def get_health(self) -> Dict[str, Any]:
        """Get health status of all services.

        Returns:
            Dictionary with health information
        """
        uptime_seconds = None
        if self._startup_time:
            uptime_seconds = (datetime.now() - self._startup_time).total_seconds()

        return {
            "status": self._status.value,
            "is_ready": self.is_ready,
            "uptime_seconds": uptime_seconds,
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            "services": {
                name: status.value for name, status in self._service_status.items()
            },
            "initialization_errors": self._initialization_errors if self._initialization_errors else None,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics.

        Returns:
            Dictionary with system statistics
        """
        stats = {
            "uptime_seconds": None,
            "active_sessions": 0,
            "active_sse_connections": 0,
            "total_players": 0,
        }

        if self._startup_time:
            stats["uptime_seconds"] = (datetime.now() - self._startup_time).total_seconds()

        if self._session_manager:
            # Note: list_active_sessions is async but get_statistics is sync
            # For now, we'll just count sessions from the internal state
            stats["active_sessions"] = len(self._session_manager._sessions)

        if self._sse_manager:
            stats["active_sse_connections"] = self._sse_manager.get_connection_count()

        return stats


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global state manager instance.

    Returns:
        StateManager instance

    Raises:
        RuntimeError: If state manager is not initialized
    """
    global _state_manager
    if _state_manager is None:
        raise RuntimeError("State manager not initialized. Call initialize_state_manager() first.")
    return _state_manager


async def initialize_state_manager() -> StateManager:
    """Initialize the global state manager.

    Returns:
        Initialized StateManager instance
    """
    global _state_manager
    if _state_manager is not None:
        logger.warning("State manager already initialized")
        return _state_manager

    _state_manager = StateManager()
    await _state_manager.initialize()
    return _state_manager


async def shutdown_state_manager() -> None:
    """Shutdown the global state manager."""
    global _state_manager
    if _state_manager is None:
        logger.warning("State manager not initialized, nothing to shutdown")
        return

    await _state_manager.shutdown()
    _state_manager = None
