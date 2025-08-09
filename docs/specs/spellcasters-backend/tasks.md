# Spellcasters Playground Backend - Implementation Tasks

## Overview

This implementation plan converts the feature design into a series of incremental coding tasks for test-driven development. Each task builds on previous tasks and can be executed by a coding agent.

## Implementation Tasks

### 1. Project Foundation and Data Models

- [x] 1.1 Create FastAPI project structure in `/backend` directory
  - Set up directory structure with `app/`, `tsts/`, and configuration files
  - Update `pyproject.toml`/`requirements.txt` with FastAPI, Pydantic, SQLModel, SQLite dependencies
  - Initialize SQLite database and create database directory structure
  - Initialize `main.py` with basic FastAPI app
  - **Requirements**: Foundation for all backend functionality

- [x] 1.2 Implement core data models in `/backend/app/models/`
  - Create `players.py` with `PlayerRegistration` and `Player` models
  - Create `sessions.py` with `GameState`, `PlayerSlot`, and `TurnStatus` models
  - Create `events.py` with SSE event models (`SSETurnEvent`, `SSEGameOverEvent`)
  - Create `actions.py` with `PlayerAction`, `ActionData`, `Move`, `MoveHistory` models
  - Create `results.py` with `GameResult`, `GameResultType`, `PlayerGameStats` models
  - Create `database.py` with SQLModel database models (`PlayerDB`, `SessionDB`, `GameResultDB`)
  - Set up database connection and table creation logic
  - **Requirements**: 1.4, 2.3, 3.2, 4.3, 7.3, 8.4 (Data models for all system components)

- [x] 1.3 Create error handling framework in `/backend/app/core/exceptions.py`
  - Implement `PlaygroundError` base exception and derived classes
  - Create `ErrorResponse` model for consistent error responses
  - **Requirements**: 9.1, 9.5 (Error handling and meaningful error messages)

- [x] 1.4 Write unit tests for all data models
  - Test model validation, serialization, and edge cases
  - Ensure proper type checking and field constraints
  - **Requirements**: Testing strategy for data integrity

### 2. Player Management System

- [x] 2.1 Implement `DatabaseService` class in `/backend/app/services/database.py`
  - Create SQLite database connection and session management
  - Implement CRUD operations for players, sessions, and game results
  - Add player deletion with constraint validation and cascade delete
  - Add database migration support and table creation
  - Handle database connection pooling and error recovery
  - **Requirements**: Database persistence for all player and session data, player deletion

- [x] 2.2 Implement `PlayerRegistry` class in `/backend/app/services/player_registry.py`
  - Create player registration, retrieval, and statistics tracking
  - Add player deletion with validation and constraint checking
  - Integrate `DatabaseService` with `PlayerRegistry` for player storage
  - Implement built-in player pre-registration functionality
  - Replace in-memory storage with database operations
  - Handle UUID generation and player data management
  - **Requirements**: 1.1, 1.3, 1.4, 1.5, 1.8-1.12 (Persistent player registration, metadata, and deletion)

- [x] 2.3 Create player registration API endpoints in `/backend/app/api/players.py`
  - Implement `POST /players/register` endpoint
  - Implement `DELETE /players/{player_id}` endpoint
  - Add input validation and error handling
  - Wire endpoints to `PlayerRegistry` service
  - **Requirements**: 1.1, 1.6, 1.7, 1.8-1.12 (Player registration and deletion endpoints with validation)

- [x] 2.4 Write comprehensive tests for player management
  - Unit tests for `PlayerRegistry` functionality including deletion
  - Integration tests for player registration and deletion endpoints
  - Test error scenarios and edge cases for both registration and deletion
  - Test constraint validation for player deletion
  - **Requirements**: Testing strategy and error handling validation for registration and deletion

### 3. Bot System Implementation

- [x] 3.1 Create abstract `BotInterface` in `/backend/app/models/bots.py`
  - Implement base class with player reference and required methods
  - Define interface for game decision making
  - **Requirements**: 9.1, 9.2, 9.3 (Built-in bot interface and player references)

- [x] 3.2 Implement `BuiltinBotRegistry` in `/backend/app/services/builtin_bots.py`
  - Create hard-coded built-in player definitions
  - Implement bot factory methods and bot listing functionality
  - Register sample bots with proper player associations
  - **Requirements**: 9.1, 9.2, 9.7, 9.8 (Built-in bot system with pre-defined players)

- [x] 3.3 Create `PlayerBot` implementation and factory
  - Implement player bot class that inherits from `BotInterface`
  - Create `PlayerBotFactory` for bot creation with player references
  - Handle both existing player reuse and new player registration scenarios
  - **Requirements**: 9.4, 9.9 (Player bot interface compliance and creation)

- [x] 3.4 Integrate existing game engine with bot interface
  - Create adapter in `/backend/app/services/game_adapter.py` to bridge existing `/game` code
  - Modify game engine to work with new `BotInterface`
  - Ensure proper game state extraction and turn processing
  - **Requirements**: 6.1, 6.2, 6.4, 6.6 (Game engine integration and rule validation)

- [x] 3.5 Write tests for bot system
  - Unit tests for bot interface implementations
  - Test built-in bot registry and factory methods
  - Integration tests for game engine adapter
  - **Requirements**: Testing strategy for bot system integrity

### 4. Session Management and Game Flow

- [x] 4.1 Implement `SessionManager` in `/backend/app/services/session_manager.py`
  - Create session creation, state management, and cleanup functionality
  - Implement match loop coordination and turn processing
  - Handle both built-in and player bot integration
  - **Requirements**: 2.1, 2.2, 2.3, 2.7 (Session creation and state management)

- [x] 4.2 Create session API endpoints in `/backend/app/api/sessions.py`
  - Implement `POST /playground/start` endpoint
  - Add session validation and error handling
  - Wire endpoints to `SessionManager` service
  - Unit tests for session creation and management
  - **Requirements**: 2.1, 2.6 (Session creation endpoint)

- [x] 4.3 Implement turn processing and action coordination
  - Create turn collection and synchronization logic in `SessionManager`
  - Implement timeout handling for player actions
  - Add game state updates and logging
  - Test turn processing and timeout scenarios
  - Integration tests for complete game flow
  - **Requirements**: 4.1, 4.3, 4.4, 5.1, 5.2, 5.4, 5.5 (Action processing and timeout management)

### 5. Real-time Streaming (SSE)

- [ ] 5.1 Implement SSE connection management in `app/services/sse_manager.py`
  - Create connection tracking and cleanup functionality
  - Handle client disconnections gracefully
  - Implement event broadcasting to connected clients
  - **Requirements**: 3.1, 3.6, 3.7 (SSE connection management and validation)

- [ ] 5.2 Create SSE streaming endpoints in `app/api/streaming.py`
  - Implement `GET /playground/{session_id}/events` endpoint
  - Add proper SSE headers and event formatting
  - Handle connection lifecycle and error scenarios
  - Unit tests for SSE connection management
  - **Requirements**: 3.1, 3.2, 3.5 (SSE endpoint and event streaming)

- [ ] 5.3 Integrate SSE with session management
  - Connect session events to SSE broadcasting
  - Implement turn updates and game over events
  - Add heartbeat and connection health monitoring
  - Integration tests for real-time streaming
  - Test event broadcasting and client disconnection handling
  - **Requirements**: 3.2, 3.3, 3.4 (Real-time match updates and event formatting)

### 6. SSE Client for Real-World Simulation

- [ ] 6.1 Create SSE client library in `/backend/client/sse_client.py`
  - Implement Python SSE client that connects to backend streaming endpoints
  - Add robust connection management and event parsing functionality
  - Handle connection lifecycle, reconnection scenarios, and error recovery
  - Provide clean API for consuming SSE events from the playground backend
  - **Requirements**: Real-world client simulation for SSE communication

- [ ] 6.2 Implement bot client simulator in `/backend/client/bot_client.py`
  - Create realistic bot client that simulates actual player bot behavior
  - Implement complete player registration and session joining workflow
  - Add action submission, turn coordination, and game state processing
  - Include configurable bot strategies and decision-making logic
  - **Requirements**: Realistic simulation of player bot interaction with backend

- [ ] 6.3 Create integration tests using real clients in `/backend/tests/e2e/test_real_clients.py`
  - Test complete workflow using actual SSE and bot clients from `/backend/client/`
  - Verify end-to-end functionality with realistic client behavior
  - Test multiple concurrent real clients and session isolation
  - Validate system behavior under realistic usage patterns
  - **Requirements**: 3.6, 3.7, 4.4, 5.5 (Real-world SSE integration validation)

### 7. Player Action Processing

- [ ] 7.1 Implement action submission endpoints in `/backend/app/api/actions.py`
  - Create `POST /playground/{session_id}/action` endpoint
  - Add action validation and turn verification
  - Handle action storage and processing coordination
  - **Requirements**: 4.1, 4.2, 4.3, 4.6, 4.7 (Action submission and validation)

- [ ] 7.2 Create `TurnProcessor` in `/backend/app/services/turn_processor.py`
  - Implement action collection with timeout handling
  - Add turn validation and game rule enforcement
  - Create turn result generation and state updates
  - **Requirements**: 4.4, 5.3, 5.7 (Turn processing and action coordination)

- [ ] 7.3 Integrate action processing with game engine
  - Connect player actions to game engine execution
  - Implement move and spell validation
  - Handle action results and state updates
  - **Requirements**: 6.3, 6.5 (Action validation and game rule integration)

- [ ] 7.4 Write tests for action processing
  - Unit tests for action validation and turn processing
  - Test timeout scenarios and invalid actions
  - Integration tests for complete action flow
  - **Requirements**: Testing strategy for action processing reliability

### 8. Match Logging and Replay System

- [ ] 8.1 Implement match logging in `/backend/app/services/match_logger.py`
  - Create structured logging for all match events
  - Implement file-based log storage in `logs/playground/` directory
  - Add move history tracking and game result recording
  - **Requirements**: 7.1, 7.3, 7.6, 7.7 (Match logging and file management)

- [ ] 8.2 Create replay endpoints in `/backend/app/api/replay.py`
  - Implement `GET /playground/{session_id}/replay` endpoint
  - Add replay streaming without timing delays
  - Handle replay data serving from session state
  - **Requirements**: 8.1, 8.2, 8.4, 8.5 (Replay functionality and data access)

- [ ] 8.3 Integrate logging with session management
  - Connect match events to logging system
  - Update player statistics after match completion
  - Implement proper cleanup and data persistence
  - **Requirements**: 7.2, 7.4, 7.5 (Winner determination and statistics tracking)

- [ ] 8.4 Write tests for logging and replay
  - Unit tests for match logging functionality
  - Test replay data generation and streaming
  - Verify log file format and data integrity
  - **Requirements**: Testing strategy for data persistence and replay accuracy

### 9. Admin Management System

- [ ] 9.1 Implement `AdminService` class in `/backend/app/services/admin_service.py`
  - Create admin operations for player and session management
  - Implement player statistics aggregation and formatting
  - Add active session monitoring and cleanup functionality
  - Handle administrative logging and audit trails
  - **Requirements**: 12.1, 12.2, 12.3, 12.4 (Administrative monitoring and management capabilities)

- [ ] 9.2 Create admin API endpoints in `/backend/app/api/admin.py`
  - Implement `GET /admin/players` endpoint with player statistics
  - Implement `GET /playground/active` endpoint for session monitoring
  - Implement `DELETE /playground/{session_id}` endpoint for session cleanup
  - Add proper error handling and validation for admin operations
  - **Requirements**: 12.1, 12.3, 12.5, 12.8 (Admin endpoints for system monitoring and management)

- [ ] 9.3 Integrate admin functionality with existing services
  - Connect `AdminService` with `SessionManager` for session cleanup
  - Wire admin endpoints to database service for player information
  - Implement graceful session termination with SSE client notification
  - Add admin action logging for audit purposes
  - **Requirements**: 12.6, 12.7 (Complete admin system integration)

- [ ] 9.4 Write tests for admin management system
  - Unit tests for `AdminService` functionality
  - Integration tests for admin API endpoints
  - Test session cleanup and client notification scenarios
  - Test error handling for invalid admin operations
  - **Requirements**: Testing strategy for admin system reliability

### 10. System Integration and Error Handling

- [ ] 10.1 Implement global error handlers in `/backend/app/core/error_handlers.py`
  - Create FastAPI exception handlers for all custom exceptions
  - Add proper HTTP status codes and error responses
  - Implement security-aware error logging
  - **Requirements**: 10.1, 10.3, 10.4, 10.5, 10.6 (Global error handling and meaningful messages)

- [ ] 10.2 Create application state management in `/backend/app/core/state.py`
  - Implement `StateManager` with all service integrations
  - Add lifecycle management for all components
  - Create system health and statistics endpoints
  - **Requirements**: Central state coordination and system monitoring

- [ ] 10.3 Wire all components together in `/backend/app/main.py`
  - Initialize all services and register API routes
  - Add proper dependency injection and configuration
  - Implement application startup and shutdown hooks
  - **Requirements**: Complete system integration

- [ ] 10.4 Write comprehensive integration tests
  - End-to-end tests for complete match workflows
  - Test concurrent session handling and SSE streaming
  - Verify proper component integration and data flow
  - **Requirements**: Testing strategy for system reliability

### 11. Security and Validation

- [ ] 11.1 Implement input validation middleware in `/backend/app/core/validation.py`
  - Add comprehensive request validation for all endpoints
  - Implement rate limiting and abuse prevention
  - Create security headers and CORS configuration
  - Test input validation and error scenarios
  - Security tests for malformed requests and edge cases
  - **Requirements**: 10.7 (Input validation and security measures)

- [ ] 11.2 Add bot execution safety measures
  - Implement timeout enforcement for bot decisions
  - Add error handling for bot execution failures
  - Create resource monitoring and limits
  - Verify timeout enforcement and resource limits
  - **Requirements**: 10.2, 10.5 (Bot execution security and error handling)

## Task Execution Notes

- Each task builds incrementally on previous tasks
- All tasks include comprehensive testing
- Tasks focus on code implementation that can be executed by a coding agent
- Requirements references ensure complete coverage of the specification
- Integration happens progressively throughout the implementation 