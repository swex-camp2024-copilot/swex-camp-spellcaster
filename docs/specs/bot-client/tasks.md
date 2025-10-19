# Bot Client Implementation Tasks

This document outlines the implementation tasks for the bot-client feature, organized by client lifecycle phases. Each task builds on previous tasks and references specific requirements from `requirements.md`.

---

## Implementation Tasks

### 1. Client Initialization

- [x] **1.1 Update CLI argument structure in `client/bot_client_main.py`**
  - Replace `--player-name` and `--builtin-bot-id` with new arguments
  - Add `--player-id` argument (default: OS username via `whoami`)
  - Add `--opponent-id` argument (default: `builtin_sample_1`)
  - Update `--bot-type` to support `random` and `custom` (default: `random`)
  - Update `--bot-path` to be required when `--bot-type=custom`
  - Add environment variable support matching CLI arguments: `BASE_URL`, `PLAYER_ID`, `OPPONENT_ID`, `BOT_TYPE`, `BOT_PATH`, `MAX_EVENTS`, `LOG_LEVEL`
  - **Requirements**: Requirement 2.2, 2.3, 2.4

- [x] **1.2 Implement OS username detection**
  - Create helper function to get OS username via `whoami` command
  - Handle subprocess execution and error cases
  - Return username string or raise clear error
  - **Requirements**: Requirement 1.1, 2.3

- [x] **1.3 Update `load_bot_class()` in `bot_client_main.py`**
  - Keep existing `importlib` loading logic
  - Update to work with `--bot-path` argument
  - Remove `--bot-type` branching for `random` vs `custom`
  - **Requirements**: Requirement 7.1, 7.3, 7.6

- [x] **1.4 Update CLI workflow to instantiate bot based on `--bot-type`**
  - If `--bot-type=random`: instantiate `RandomWalkStrategy()`
  - If `--bot-type=custom`: load bot class from `--bot-path` and instantiate
  - Pass bot instance to `BotClient` constructor
  - **Requirements**: Requirement 7.1, 7.2, 7.4, 7.5

- [x] **1.5 Remove `BotStrategy` and `BotInterfaceAdapter` classes**
  - Delete `BotStrategy` abstract base class from `client/bot_client.py`
  - Delete `BotInterfaceAdapter` wrapper class
  - Update `BotClient` to directly call bot's `decide()` method
  - **Requirements**: Requirement 7.1, 7.7

- [x] **1.6 Update `RandomWalkStrategy` to implement `BotInterface`**
  - Ensure `RandomWalkStrategy` has `name` property
  - Ensure `decide()` method matches `BotInterface` signature
  - Keep existing toggle-based movement logic
  - **Requirements**: Requirement 7.2, 7.9

- [x] **1.7 Update `BotClient.__init__()` to accept bot instance**
  - Change constructor signature to accept `bot_instance` parameter
  - Remove strategy/adapter pattern - directly store bot instance
  - Bot instance should implement `BotInterface` (synchronous `decide()` method)
  - **Requirements**: Requirement 7.1, 7.9

- [x] **1.8 Improve error logging in CLI**
  - Log connection errors with clear messages
  - Log bot loading errors with module path
  - Log player validation errors
  - **Requirements**: Requirement 9.1, 2.10

- [x] **1.9 Update `client/README.md` with new CLI arguments**
  - Document new argument structure (`--player-id`, `--opponent-id`, `--bot-type`, `--bot-path`)
  - Update usage examples for PvE and PvP matches
  - Document environment variables
  - Add match termination behavior section
  - Update troubleshooting tips
  - Add minimum arguments example (uses OS username + random bot)
  - Add custom bot vs builtin example
  - Add PvP match example (two remote players)
  - **Requirements**: Requirement 13.1

- [x] **1.10 Write unit tests for client initialization**
  - Test CLI argument parsing with default values (OS username, `builtin_sample_1`, `random`)
  - Test environment variable override
  - Test `--bot-path` required validation when `--bot-type=custom`
  - Test OS username detection with mock subprocess
  - Test `RandomWalkStrategy` instantiation
  - Test custom bot loading from module path
  - Test error handling for invalid bot path
  - **Requirements**: Requirement 2.3, 2.4, 7.3, 7.4

- [x] **1.11 Write E2E test for minimum arguments match**
  - Test CLI with no arguments (uses OS username + random bot)
  - Verify match completes successfully
  - Use `asgi_client` fixture for backend
  - **Requirements**: Requirement 2.1, 7.2
  - **Note**: E2E tests written but have issues with database persistence between tests - will be addressed in future iteration

---

### 2. Match Start

- [x] **2.1 Remove player registration method from `BotClient`**
  - Remove `register_player()` method
  - Update `BotClient` to not handle registration
  - **Requirements**: Requirement 1.3, 1.4

- [x] **2.2 Implement unified `start_match()` method**
  - Replace `start_match_vs_builtin()` with generic `start_match(player_id, opponent_id, visualize=True)`
  - Automatically detect opponent type based on ID format (starts with `builtin_` = builtin bot)
  - Configure backend request payload with `player_1_config` and `player_2_config`
  - Return session ID
  - **Requirements**: Requirement 2.5, 2.6, 2.7

- [x] **2.3 Verify backend supports `bot_type: "player"` configuration**
  - Review `backend/app/services/session_manager.py`
  - Ensure sessions can be created with remote player configuration
  - Verify player ID validation exists
  - **Requirements**: Requirement 10.1, 10.2

- [x] **2.4 Verify backend validates player existence**
  - Review player validation in session creation endpoint
  - Ensure 404 error returned if player doesn't exist
  - **Requirements**: Requirement 2.9, 1.2, 1.3

- [x] **2.5 Write unit tests for match creation**
  - Test `start_match()` with builtin opponent (`builtin_sample_1`)
  - Test `start_match()` with remote player opponent
  - Test opponent type detection logic
  - Mock HTTP client and verify payload structure
  - **Requirements**: Requirement 2.5, 2.6, 2.7, 2.10

- [x] **2.6 Write backend integration tests for match start**
  - Test session creation with `bot_type: "player"`
  - Test player validation (404 for non-existent player)
  - **Requirements**: Requirement 10.1, 10.2, 2.9

- [x] **2.7 Write E2E test for PvP match**
  - Test match between two remote players
  - Both clients run bot implementations
  - Verify match completes with winner
  - **Requirements**: Requirement 2.7

---

### 3. Match Action Loop (Gameplay)

- [ ] **3.1 Update `play_match()` to call bot's `decide()` directly**
  - Remove strategy adapter calls
  - Call bot instance's `decide()` method directly (synchronous call in async context)
  - Extract game state from `turn_update` event
  - Submit action via `POST /playground/{session_id}/action`
  - **Requirements**: Requirement 6.2, 7.7

- [ ] **3.2 Verify backend handles remote player action timeout**
  - Review `backend/app/services/turn_processor.py`
  - Ensure default action is used when remote player times out
  - Verify timeout is logged in turn_update event
  - **Requirements**: Requirement 10.2, 10.6, 5.8

- [ ] **3.3 Improve error logging in `BotClient`**
  - Log HTTP request failures with URL, method, and status code
  - Log bot decision errors with game state context
  - Log SSE reconnection attempts with retry count
  - **Requirements**: Requirement 9.1, 9.2, 9.3

- [ ] **3.4 Add DEBUG level logging**
  - Log full event payloads when `--log-level=DEBUG`
  - Log bot decision details (state + action)
  - Log HTTP request/response bodies
  - **Requirements**: Requirement 9.5

- [ ] **3.5 Write unit tests for gameplay loop**
  - Test `BotClient` with `RandomWalkStrategy` instance
  - Test `BotClient` with mock custom bot (implements `BotInterface`)
  - Verify `decide()` is called with correct game state
  - Verify action submission with correct payload
  - **Requirements**: Requirement 6.2, 7.7

- [ ] **3.6 Write backend integration tests for action timeout**
  - Test remote player action timeout handling
  - Verify default action is used
  - Verify timeout is logged in turn_update event
  - **Requirements**: Requirement 10.2, 10.6, 5.8

- [ ] **3.7 Write E2E test for custom bot match**
  - Test CLI with custom bot loaded from `bots/`
  - Verify bot's `decide()` method is called
  - Verify actions are submitted correctly
  - **Requirements**: Requirement 7.1, 7.7

- [ ] **3.8 Write E2E test for error scenarios**
  - Test wrong turn number submission (verify 400 error)
  - Test bot decision exception (verify match continues)
  - Test action timeout (verify default action used)
  - Test missing player (verify 404 error)
  - **Requirements**: Requirement 9.2, 9.4, 2.9

- [ ] **3.9 Write E2E test for SSE reconnection**
  - Simulate SSE connection drop
  - Verify client reconnects automatically
  - Verify match continues after reconnection
  - **Requirements**: Requirement 4.1, 4.2, 4.3

---

### 4. Match Termination

- [ ] **4.1 Update `play_match()` to handle game_over event**
  - Detect `game_over` event in event stream
  - Stop processing further events
  - Keep SSE connection active (don't close immediately)
  - Log game result
  - **Requirements**: Requirement 8.1, 8.2, 6.5

- [ ] **4.2 Add terminal prompt for match completion**
  - After `game_over` event, display "Match complete. Press Ctrl+C to exit."
  - Wait for user interrupt
  - **Requirements**: Requirement 8.3

- [ ] **4.3 Implement clean connection closure on Ctrl+C**
  - Handle `KeyboardInterrupt` in CLI main function
  - Close SSE connection gracefully
  - Call `BotClient.aclose()` to cleanup HTTP client
  - **Requirements**: Requirement 8.4, 2.11

- [ ] **4.4 Implement visualizer cleanup on client disconnect**
  - Update `backend/app/services/session_manager.py` to detect SSE disconnection
  - Terminate visualizer process when client disconnects after game_over
  - Clean up session resources
  - **Requirements**: Requirement 8.5, 10.7

- [ ] **4.5 Write unit tests for match termination**
  - Test that client stops processing after `game_over`
  - Test that SSE connection remains active after `game_over`
  - Test cleanup on exit
  - Verify no more events received after `game_over`
  - **Requirements**: Requirement 8.1, 8.2

- [ ] **4.6 Write backend integration tests for visualizer cleanup**
  - Test visualizer cleanup on disconnect
  - Verify session resources are cleaned up
  - **Requirements**: Requirement 10.7, 8.5

- [ ] **4.7 Write E2E test for match termination**
  - Verify client stops processing after `game_over`
  - Verify SSE connection remains active
  - Verify cleanup on exit
  - **Requirements**: Requirement 8.1, 8.2, 8.3
