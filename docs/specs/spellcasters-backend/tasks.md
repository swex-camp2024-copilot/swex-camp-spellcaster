# Spellcasters Playground Backend - Implementation Tasks

## Overview

This implementation plan converts the feature design into a series of incremental coding tasks for test-driven development. Each task builds on previous tasks and can be executed by a coding agent.

## Implementation Tasks

### 1. Project Foundation and Data Models

- [x] 1.1 Create FastAPI project structure in `/backend` directory
  - Set up directory structure with `app/`, `tests/`, and configuration files
  - Update `pyproject.toml`/`requirements.txt` with FastAPI, Pydantic, SQLModel, SQLite dependencies
  - Initialize SQLite database at permanent path `data/playground.db` and ensure `data/` directory is created at startup
  - Resolve database file path to an absolute path based on the repository root so execution is independent of current working directory
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
  - Ensure absolute database path resolution and auto-create `data/` directory prior to engine initialization
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

- [x] 2.5 Change player ID generation from UUID to slug-based format
  - Implement slug generation logic in `DatabaseService._generate_player_slug()`
  - Update `DatabaseService.create_player()` to use slug-based IDs with deduplication
  - Add deduplication with numeric postfix (_2, _3, etc.) when slug already exists
  - Keep built-in player IDs unchanged (e.g., "builtin_sample_1", "builtin_tactical")
  - Add comprehensive unit tests for slug generation (basic, special characters, spaces, case)
  - Add integration tests for slug generation and deduplication in real scenarios
  - Update functional spec (data model, API examples, player ID generation section)
  - Update requirements spec (add slug generation acceptance criteria)
  - Update design spec (Player model description, add Player ID Generation Strategy section)
  - **Requirements**: Human-readable player IDs for better API usability and developer experience

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

- [x] 5.1 Implement SSE connection management in `app/services/sse_manager.py`
  - Create connection tracking and cleanup functionality
  - Handle client disconnections gracefully
  - Implement event broadcasting to connected clients
  - **Requirements**: 3.1, 3.6, 3.7 (SSE connection management and validation)

- [x] 5.2 Create SSE streaming endpoints in `app/api/streaming.py`
  - Implement `GET /playground/{session_id}/events` endpoint
  - Add proper SSE headers and event formatting
  - Handle connection lifecycle and error scenarios
  - Unit tests for SSE connection management
  - **Requirements**: 3.1, 3.2, 3.5 (SSE endpoint and event streaming)

- [x] 5.3 Integrate SSE with session management
  - Connect session events to SSE broadcasting
  - Implement turn updates and game over events
  - Add heartbeat and connection health monitoring
  - Integration tests for real-time streaming
  - Test event broadcasting and client disconnection handling
  - **Requirements**: 3.2, 3.3, 3.4 (Real-time match updates and event formatting)

### 6. SSE Client for Real-World Simulation

- [x] 6.1 Create SSE client library in `/client/sse_client.py`
  - Implement Python SSE client that connects to backend streaming endpoints
  - Add robust connection management and event parsing functionality
  - Handle connection lifecycle, reconnection scenarios, and error recovery
  - Provide clean API for consuming SSE events from the playground backend
  - **Requirements**: Real-world client simulation for SSE communication
 
- [x] 6.2 Implement bot client simulator in `/client/bot_client.py`
  - Create realistic bot client that simulates actual player bot behavior
  - Implement complete player registration and session joining workflow
  - Add action submission, turn coordination, and game state processing (submission stubbed until 7.1)
  - Include configurable bot strategies and decision-making logic
  - **Requirements**: Realistic simulation of player bot interaction with backend
 
- [x] 6.3 Create integration tests using real clients in `/client/tests/e2e/test_real_clients.py`
  - Test complete workflow using actual SSE and bot clients from `/client/`
  - Verify end-to-end functionality with realistic client behavior
  - Test multiple concurrent real clients and session isolation
  - Validate system behavior under realistic usage patterns
  - **Requirements**: 3.6, 3.7, 4.4, 5.5 (Real-world SSE integration validation)

### 7. Player Action Processing

- [x] 7.1 Implement action submission endpoints in `/backend/app/api/actions.py`
  - Create `POST /playground/{session_id}/action` endpoint
  - Add action validation and turn verification
  - Handle action storage and processing coordination
  - **Requirements**: 4.1, 4.2, 4.3, 4.6, 4.7 (Action submission and validation)

- [x] 7.2 Create `TurnProcessor` in `/backend/app/services/turn_processor.py`
  - Implement action collection with timeout handling
  - Add turn validation and game rule enforcement
  - Create turn result generation and state updates
  - **Requirements**: 4.4, 5.3, 5.7 (Turn processing and action coordination)

- [x] 7.3 Integrate action processing with game engine
  - Connect player actions to game engine execution
  - Implement move and spell validation
  - Handle action results and state updates
  - **Requirements**: 6.3, 6.5 (Action validation and game rule integration)

- [x] 7.4 Write tests for action processing
  - Unit tests for action validation and turn processing
  - Test timeout scenarios and invalid actions
  - Integration tests for complete action flow
  - **Requirements**: Testing strategy for action processing reliability

- [x] 7.5 Integrate remote player action submission with game loop
  - Re-implement PlayerBot to store and return submitted actions instead of executing bot code
  - Update SessionManager to create PlayerBot instances for `bot_type="player"`
  - Update SessionManager.submit_action to call set_action() on PlayerBot instances
  - Add unit tests for PlayerBot action storage and retrieval
  - Verify remote player actions are incorporated into gameplay
  - **Requirements**: 4.4, 4.8, 4.9, 4.10 (Remote player action integration with game loop)

### 8. Match Logging and Replay System

- [x] 8.1 Implement match logging in `/backend/app/services/match_logger.py`
  - Create structured logging for all match events
  - Implement file-based log storage in `logs/playground/` directory
  - Add move history tracking and game result recording
  - **Requirements**: 7.1, 7.3, 7.6, 7.7 (Match logging and file management)

- [x] 8.2 Create replay endpoints in `/backend/app/api/replay.py`
  - Implement `GET /playground/{session_id}/replay` endpoint
  - Add replay streaming without timing delays
  - Handle replay data serving from session state
  - **Requirements**: 8.1, 8.2, 8.4, 8.5 (Replay functionality and data access)

- [x] 8.3 Integrate logging with session management
  - Connect match events to logging system
  - Update player statistics after match completion
  - Implement proper cleanup and data persistence
  - **Requirements**: 7.2, 7.4, 7.5 (Winner determination and statistics tracking)

- [x] 8.4 Write tests for logging and replay
  - Unit tests for match logging functionality
  - Test replay data generation and streaming
  - Verify log file format and data integrity
  - **Requirements**: Testing strategy for data persistence and replay accuracy

### 9. Admin Management System

- [x] 9.1 Implement `AdminService` class in `/backend/app/services/admin_service.py`
  - Create admin operations for player and session management
  - Implement player statistics aggregation and formatting
  - Add active session monitoring and cleanup functionality
  - **Requirements**: 12.1, 12.2, 12.3, 12.4 (Administrative monitoring and management capabilities)

- [x] 9.2 Create admin API endpoints in `/backend/app/api/admin.py`
  - Implement `GET /admin/players` endpoint with player statistics
  - Implement `GET /playground/active` endpoint for session monitoring
  - Implement `DELETE /playground/{session_id}` endpoint for session cleanup
  - Add proper error handling and validation for admin operations
  - **Requirements**: 12.1, 12.3, 12.5, 12.8 (Admin endpoints for system monitoring and management)

- [x] 9.3 Integrate admin functionality with existing services
  - Connect `AdminService` with `SessionManager` for session cleanup
  - Wire admin endpoints to database service for player information
  - Implement graceful session termination with SSE client notification
  - **Requirements**: 12.6, 12.7 (Complete admin system integration)

- [x] 9.4 Write tests for admin management system
  - Unit tests for `AdminService` functionality
  - Integration tests for admin API endpoints
  - Test session cleanup and client notification scenarios
  - Test error handling for invalid admin operations
  - **Requirements**: Testing strategy for admin system reliability

### 10. System Integration and Error Handling

- [x] 10.1 Implement global error handlers in `/backend/app/core/error_handlers.py`
  - Create FastAPI exception handlers for all custom exceptions
  - Add proper HTTP status codes and error responses
  - Implement security-aware error logging
  - **Requirements**: 10.1, 10.3, 10.4, 10.5, 10.6 (Global error handling and meaningful messages)

- [x] 10.2 Create application state management in `/backend/app/core/state.py`
  - Implement `StateManager` with all service integrations
  - Add lifecycle management for all components
  - Create system health and statistics endpoints
  - **Requirements**: Central state coordination and system monitoring

- [x] 10.3 Wire all components together in `/backend/app/main.py`
  - Initialize all services and register API routes
  - Add proper dependency injection and configuration
  - Implement application startup and shutdown hooks
  - **Requirements**: Complete system integration

- [x] 10.4 Write comprehensive integration tests
  - End-to-end tests for complete match workflows
  - Test concurrent session handling and SSE streaming
  - Verify proper component integration and data flow
  - **Requirements**: Testing strategy for system reliability

### 11. Security and Validation

- [ ] 11.1 Implement input validation middleware in `/backend/app/core/validation.py`
  - Add comprehensive request validation for all endpoints
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

### 12. Lobby and PvP Matchmaking System

- [x] 12.1 Implement `LobbyService` in `/backend/app/services/lobby_service.py`
  - Create FIFO queue using `collections.deque` for player matchmaking
  - Implement `join_queue()` method with long-polling using `asyncio.Event`
  - Implement `_try_match()` method for automatic matching when 2+ players in queue
  - Add thread-safe queue operations using `asyncio.Lock`
  - Integrate with `SessionManager` for session creation
  - Integrate with `DatabaseService` for player validation
  - Add queue management methods (`get_queue_size`, `get_player_position`, `remove_from_queue`)
  - **Requirements**: 13.1, 13.2, 13.4, 13.5, 13.9, 13.10, 13.13, 13.17, 13.18 (Core lobby service with FIFO queue and auto-matching)

- [x] 12.2 Create lobby data models in `/backend/app/models/lobby.py`
  - Implement `LobbyJoinRequest` model for queue join requests
  - Implement `LobbyMatchResponse` model for match results
  - Implement `QueueEntry` internal class with `asyncio.Event` for long-polling
  - Add `wait_for_match()` and `set_match_result()` methods to `QueueEntry`
  - **Requirements**: 13.1, 13.11, 13.12 (Data models for lobby requests and responses)

- [x] 12.3 Implement lobby API endpoints in `/backend/app/api/lobby.py`
  - Create `POST /lobby/join` endpoint with 300-second timeout for long-polling
  - Create `GET /lobby/status` endpoint for queue size monitoring
  - Create `DELETE /lobby/leave/{player_id}` endpoint for queue removal
  - Add proper error handling for `PlayerNotFoundError` and `PlayerAlreadyInLobbyError`
  - Wire endpoints to `LobbyService` via runtime state
  - **Requirements**: 13.1, 13.7, 13.8, 13.14, 13.15, 13.16 (Lobby API with long-polling support)

- [x] 12.4 Add lobby exception handling in `/backend/app/core/exceptions.py` and `/backend/app/core/error_handlers.py`
  - Create `PlayerAlreadyInLobbyError` exception class with 409 status code
  - Implement exception handler for `PlayerAlreadyInLobbyError`
  - Register handler in `register_error_handlers()`
  - **Requirements**: 13.3, 13.6 (Proper error responses for lobby operations)

- [x] 12.5 Integrate `LobbyService` with `StateManager` in `/backend/app/core/state.py`
  - Add `_lobby_service` property to `StateManager`
  - Implement `_initialize_lobby_service()` with dependencies
  - Add lobby service to service status tracking
  - Wire lobby service to runtime module
  - **Requirements**: 13.17, 13.18 (Lobby service lifecycle and dependency management)

- [x] 12.6 Update client with lobby mode support
  - Add `join_lobby()` method to `/client/bot_client.py` with 300-second timeout
  - Add `--mode` CLI argument to `/client/bot_client_main.py` (direct/lobby)
  - Update `run_bot()` function to handle lobby mode vs direct mode
  - Add lobby mode documentation to `/client/README.md`
  - **Requirements**: 13.8, 13.20 (Client-side lobby support and documentation)

- [x] 12.7 Write unit tests for `LobbyService` in `/backend/tests/test_lobby_service.py`
  - Test single player waiting scenario (entry creation, queue state)
  - Test automatic matching when 2 players join
  - Test FIFO ordering (first player gets matched with second player)
  - Test duplicate join prevention (`PlayerAlreadyInLobbyError`)
  - Test player not found scenario (`PlayerNotFoundError`)
  - Test queue size and player position queries
  - Test queue removal functionality
  - **Requirements**: 13.4, 13.5, 13.9, 13.13, 13.19 (Comprehensive lobby service testing)

- [x] 12.8 Write integration tests for lobby API in `/backend/tests/test_lobby_api.py`
  - Test successful lobby join and match flow with 2 players
  - Test player not found error (404) when joining lobby
  - Test duplicate join error (409) when player already in queue
  - Test lobby status endpoint for queue size monitoring
  - Test lobby leave endpoint for queue removal
  - Test leave endpoint error (404) when player not in queue
  - **Requirements**: 13.3, 13.6, 13.14, 13.15, 13.16 (Complete lobby API testing)

- [x] 12.9 Update documentation for lobby system
  - Add §5.4 Lobby (PvP Queue) section to functional spec with API docs
  - Add Requirement 13 to backend requirements spec
  - Add §3.5 Lobby Models to backend design spec
  - Add §8 Lobby Service component to backend design spec
  - Update client README with lobby mode examples and workflow
  - **Requirements**: 13.20 (Complete documentation for lobby feature)

### 13. Test Database Isolation

- [x] 13.1 Implement test database override for e2e tests
  - Update `client/tests/conftest.py` with session-scoped `override_test_database` fixture
  - Override `PLAYGROUND_DATABASE_URL` environment variable to use `data/test.db`
  - Add automatic cleanup to remove test database after test session completion
  - Make `asgi_client` fixture depend on `override_test_database` to ensure proper initialization order
  - **Requirements**: 11.6 (Separate test database to prevent production data pollution)

- [x] 13.2 Update specification documents for test database
  - Update `requirements.md` Requirement 11.6 to document test database usage
  - Update `design.md` Core Data Storage section to distinguish production and test databases
  - Add Test Database Configuration section to design.md Testing Strategy
  - Document database override mechanism and cleanup process
  - **Requirements**: Complete documentation of test database isolation strategy

- [ ] 13.3 Add tests to verify database isolation
  - Create test to verify e2e tests use `data/test.db` (not `data/playground.db`)
  - Test that production database is not modified during e2e test execution
  - Verify test database cleanup occurs after test session
  - Test database path resolution is correct across different working directories
  - **Requirements**: 11.6 (Verify test database isolation works correctly)

### 14. Fix PvP Action Reuse Bug

- [x] 14.1 Fix PlayerBot action clearing in `backend/app/models/bots.py`
  - Clear `_last_action` after returning it in `decide()` method
  - Ensures each action is consumed exactly once
  - Prevents action reuse across multiple turns
  - **Requirements**: 4.4, 4.8, 4.9, 4.10, 4.11, 4.12 (Proper remote player action handling and consumption)

- [x] 14.2 Fix HumanBot action clearing in `backend/app/models/bots.py`
  - Apply same fix to `HumanBot.decide()` for consistency
  - Clear action after use to prevent reuse
  - **Requirements**: Same as 14.1

- [x] 14.3 Add unit tests for action clearing behavior
  - Test that actions are cleared after `decide()` is called (`test_player_bot_clears_action_after_use`)
  - Test that subsequent `decide()` calls return default actions
  - Test action clearing with spells (`test_player_bot_action_clearing_with_spell`)
  - **Requirements**: Testing strategy for bot behavior and bug fix validation

- [x] 14.4 Enhance PvP integration test
  - Update `test_bot_client_player_vs_player_match` to run for 5 turns
  - Track and verify both players' positions change over time
  - Add assertions for continuous movement of BOTH players
  - Verify action reuse bug is fixed
  - **Requirements**: 13.9, 13.19 (PvP match validation and continuous gameplay)

- [x] 14.5 Update specification documents
  - Update requirements.md to clarify action consumption behavior (4.11, 4.12)
  - Update design.md PlayerBot section with action clearing details
  - Document importance of fresh action submission per turn
  - **Requirements**: Complete documentation of action lifecycle and bug fix

- [x] 14.6 Fix race condition in `submit_action()`
  - Reorder operations in `session_manager.py:submit_action()` to set action on bot BEFORE storing in turn processor
  - Add comprehensive docstring explaining the race condition and why ordering matters
  - Ensures `bot.set_action()` completes before action becomes visible to `collect_actions()`
  - Prevents game engine from calling `bot.decide()` before action is set
  - **Root Cause**: `collect_actions()` saw action in turn processor and returned before `bot.set_action()` completed, causing `decide()` to return default [0,0]
  - **Fix**: Set action on bot instance first, then store in turn processor
  - **Requirements**: 4.13, 4.14 (Atomic action submission and race prevention)

- [x] 14.7 Add integration test for race condition fix
  - Create `test_pvp_no_race_condition_in_action_submission` in `client/tests/e2e/test_real_clients.py`
  - Test with two deterministic bots (AlwaysMoveRightBot and AlwaysMoveDownBot)
  - Verify both players move on every turn (no default [0,0] actions from race)
  - Track positions for 5+ turns to detect any race condition occurrences
  - Test validates that actions are available when `bot.decide()` is called
  - **Requirements**: Complete validation of race condition fix

- [x] 14.8 Update specifications for race condition fix
  - Document race condition in design.md with code examples and detailed explanation
  - Add requirements 4.13-4.14 for atomic action submission guarantees
  - Explain why BOTH action clearing AND race fix are needed together
  - Document symptoms of the race condition (one player stuck, one moving)
  - Document the fix: reordering operations in `submit_action()`
  - **Requirements**: Complete documentation of timing guarantees and race prevention strategy

## Implementation Summary for Task 14

Task 14 addressed TWO related but distinct bugs in PvP gameplay:

### Bug 1: Action Reuse (Fixed in 14.1-14.2)
- **Problem**: Actions were never cleared after use, causing indefinite reuse
- **Solution**: Clear `_last_action` in both PlayerBot and HumanBot after returning it
- **Impact**: Each turn now requires fresh action submission

### Bug 2: Race Condition (Fixed in 14.6)
- **Problem**: `submit_action()` made actions visible to match loop before setting them on bot instances
- **Race Window**: `collect_actions()` → `execute_turn()` → `bot.decide()` called before `bot.set_action()` completed
- **Symptom**: Player submitted actions successfully but didn't move (returned default [0,0])
- **Solution**: Reorder operations - set action on bot FIRST, then store in turn processor
- **Impact**: Actions guaranteed available when game engine calls `decide()`

### Why Both Fixes Are Required

1. **Without Action Clearing**: Old actions replayed indefinitely → wrong behavior
2. **Without Race Fix**: Actions submitted but not available when needed → default [0,0] → no movement
3. **With Both Fixes**: Proper turn-based gameplay where both players move correctly

The complete solution ensures:
- ✅ Actions never reused across turns (clearing)
- ✅ Actions always available when engine needs them (ordering)
- ✅ Both players move correctly in PvP matches
- ✅ No race conditions in concurrent action submission
- ✅ All tests pass including enhanced PvP tests

## Task Execution Notes

- Each task builds incrementally on previous tasks
- All tasks include comprehensive testing
- Tasks focus on code implementation that can be executed by a coding agent
- Requirements references ensure complete coverage of the specification
- Integration happens progressively throughout the implementation 