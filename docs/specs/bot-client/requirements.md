# Bot Client Integration Requirements

## Introduction

This document specifies the requirements for the **bot-client** feature of the Spellcasters Hackathon project. The feature enables remote bot clients to play matches against the backend server via HTTP/SSE communication, supporting both simple built-in strategies and existing `BotInterface` implementations.

The bot-client system provides:

- Remote player registration and match participation
- Real-time game event streaming via Server-Sent Events (SSE)
- Automated action submission based on bot decisions
- Dynamic bot strategy selection and switching
- Resilient error handling and automatic reconnection
- Command-line interface for easy bot execution

This enhancement builds upon the existing client implementation to provide production-ready functionality with comprehensive error handling, strategy flexibility, and complete test coverage.

---

## Requirements

### 1. Player Identity and Registration

**User Story**: As a bot developer, I want to use my existing player identity or have the system automatically use my OS username, so that I can participate in matches without manual registration steps.

**Acceptance Criteria**:

1. **WHEN** the CLI is invoked without `--player-id`, **THEN** the CLI SHALL use the current OS username (via `whoami` command) as the default player identifier.
2. **WHERE** a player identifier is used, **THEN** the backend SHALL verify the player exists in the database.
3. **IF** the player does not exist in the backend, **THEN** the backend SHALL return a 404 Not Found error with a message indicating the player needs to be registered first.
4. **WHEN** players need to be registered (outside CLI scope), **THEN** they can use the backend's `POST /players/register` endpoint with a player name.
5. **WHILE** registering a player via the backend API, **IF** the player name already exists, **THEN** the backend SHALL return a 409 Conflict error.
6. **WHERE** the registration request includes optional sprite paths, **THEN** the backend SHALL store these paths with the player record.
7. **WHEN** registration is successful, **THEN** the backend SHALL return the player ID, player name, and registration timestamp.

---

### 2. Match Creation and CLI Interface

**User Story**: As a bot developer, I want to easily start and play a match using a simple CLI command, so that I can test my bot's strategy remotely against other players or builtin bots.

**Acceptance Criteria**:

1. **WHEN** the CLI is invoked with minimum required arguments, **THEN** it SHALL:
   - Use the specified player identity (or current OS user as default)
   - Start a match against the specified opponent
   - Automatically play the match to completion using the bot strategy
   - Display events as JSON lines
   - Exit when the match completes
2. **WHERE** the following CLI arguments are supported, **THEN** they SHALL function as specified:
   - `--base-url` - Backend URL (default: http://localhost:8000, env: `BASE_URL`)
   - `--player-id` - Existing registered player ID in backend (default: current OS user via `whoami`, env: `PLAYER_ID`)
   - `--opponent-id` - Opponent ID: either a connected player waiting online, or a builtin bot (e.g., `builtin_sample_1`, default: `builtin_sample_1`, env: `OPPONENT_ID`)
   - `--bot-type` - Bot strategy: `random` or `custom` (default: `random`, env: `BOT_TYPE`)
   - `--bot-path` - Module path to custom bot class (required if `--bot-type=custom`, env: `BOT_PATH`)
   - `--max-events` - Event limit (default: 100, env: `MAX_EVENTS`)
   - `--log-level` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO, env: `LOG_LEVEL`)
3. **WHEN** `--player-id` is not provided, **THEN** the CLI SHALL default to the current OS username obtained via `whoami` command.
4. **WHEN** `--bot-type` is `custom`, **THEN** `--bot-path` SHALL be required; **IF** not provided, the CLI SHALL display an error and exit.
5. **WHEN** the client starts a match, **THEN** it SHALL call the backend with player and opponent configurations to create a session.
6. **WHERE** the opponent ID starts with `builtin_`, **THEN** the backend SHALL configure the opponent with `bot_type: "builtin"` and extract the bot ID.
7. **WHERE** the opponent ID is a regular player ID, **THEN** the backend SHALL configure the opponent with `bot_type: "player"` for a remote player match.
8. **WHEN** the match is created, **THEN** the backend SHALL immediately start the game loop in a background task.
9. **IF** the player ID does not exist in the backend, **THEN** the backend SHALL return a 404 Not Found error.
10. **IF** the opponent ID is invalid (neither a valid player nor builtin bot), **THEN** the backend SHALL return a 400 Bad Request error.
11. **WHEN** the match is created with `visualize: true`, **THEN** the backend SHALL enable the Pygame visualizer for the session.
12. **IF** the backend is unreachable, **THEN** the CLI SHALL display a connection error and exit.
13. **IF** the user interrupts with Ctrl+C, **THEN** the CLI SHALL close connections cleanly and exit.

---

### 3. SSE Event Streaming

**User Story**: As a bot client, I want to receive real-time game events via SSE, so that I can react to game state changes immediately.

**Acceptance Criteria**:

1. **WHEN** the client connects to `/playground/{session_id}/events`, **THEN** the backend SHALL establish an SSE stream with `Content-Type: text/event-stream`.
2. **WHILE** the session is active, **THEN** the backend SHALL broadcast the following event types:
   - `session_start` - Match initialization with player info
   - `turn_update` - Turn results with updated game state
   - `heartbeat` - Keepalive event every 5 seconds
   - `game_over` - Match conclusion with winner and final state
   - `error` - Error notifications with type and message
3. **WHEN** a `turn_update` event is broadcast, **THEN** it SHALL include:
   - Current turn number
   - Complete game state (wizards, minions, artifacts)
   - Actions submitted by both players (or defaults)
   - Event log entries for the turn
   - Timestamp
4. **WHEN** a `game_over` event is broadcast, **THEN** it SHALL include:
   - Winner player ID (or null for draw)
   - Final game state
   - Game result summary (turns played, damage dealt)
   - Reason for game end (hp_zero, max_turns)
5. **WHILE** the connection is active, **IF** no events occur, **THEN** the backend SHALL send heartbeat events every 5 seconds.
6. **IF** the session does not exist, **THEN** the backend SHALL return a 404 Not Found error.

---

### 4. SSE Connection Resilience

**User Story**: As a bot client, I want automatic reconnection when the SSE connection drops, so that my bot can continue playing without manual intervention.

**Acceptance Criteria**:

1. **WHEN** the SSE connection is lost due to network error, **THEN** the client SHALL automatically attempt to reconnect.
2. **WHILE** reconnecting, **THEN** the client SHALL use exponential backoff starting at 0.5 seconds, doubling each retry, up to a maximum of 8 seconds.
3. **WHERE** reconnection attempts fail, **THEN** the client SHALL retry up to 5 times before giving up.
4. **WHEN** reconnection succeeds, **THEN** the client SHALL resume streaming from the current game state.
5. **IF** the maximum retry limit is exceeded, **THEN** the client SHALL log an error and exit gracefully.
6. **WHILE** reconnecting, **THEN** the client SHALL log each attempt with the retry count and backoff duration.
7. **WHERE** the session has ended during disconnection, **THEN** the backend SHALL send a `game_over` event upon reconnection.

---

### 5. Action Submission

**User Story**: As a bot client, I want to submit my bot's action decisions to the backend, so that my bot can participate in the match.

**Acceptance Criteria**:

1. **WHEN** the client calls `submit_action()` with valid parameters, **THEN** the backend SHALL accept and queue the action for the specified turn.
2. **WHERE** the action submission includes player ID, turn number, and action data, **THEN** the backend SHALL validate all three fields.
3. **IF** the turn number does not match the expected turn (current + 1), **THEN** the backend SHALL return a 400 Bad Request error.
4. **IF** the player ID does not belong to the session, **THEN** the backend SHALL return a 403 Forbidden error.
5. **WHEN** an action is successfully queued, **THEN** the backend SHALL return a 200 OK response.
6. **WHERE** the action data includes a move delta `[dx, dy]`, **THEN** the backend SHALL validate the move is within game rules.
7. **WHERE** the action data includes a spell, **THEN** the backend SHALL validate the spell name and target (if applicable).
8. **IF** an action is not submitted within `TURN_TIMEOUT_SECONDS` (default 5s), **THEN** the backend SHALL use a default action (no move, no spell).

---

### 6. Automated Match Playing

**User Story**: As a bot client, I want to automatically play a complete match without manual intervention, so that matches can run unattended.

**Acceptance Criteria**:

1. **WHEN** the client starts a match, **THEN** it SHALL automatically combine event streaming with action submission (automatic mode is the only supported mode - no manual mode).
2. **WHILE** streaming events, **WHEN** a `turn_update` event is received, **THEN** the client SHALL:
   - Extract the game state from the event
   - Call the bot's `decide()` method with the game state
   - Automatically submit the resulting action for turn + 1 via `POST /playground/{session_id}/action`
   - Yield the event to the caller
3. **IF** the bot's `decide()` method raises an exception, **THEN** the client SHALL:
   - Log the error with full stack trace
   - Continue streaming events (no action submitted)
   - Allow the backend to use a default action
4. **IF** action submission fails (network error or validation error), **THEN** the client SHALL:
   - Log the error
   - Continue streaming events
   - Attempt to submit the next turn's action
5. **WHEN** a `game_over` event is received, **THEN** the client SHALL stop processing and exit the match loop.
6. **WHERE** a `max_events` limit is specified, **THEN** the client SHALL stop after processing that many events.

---

### 7. Bot Implementation Loading

**User Story**: As a bot developer, I want to specify different bot implementations at the beginning of each match, so that I can test various bot strategies remotely without code changes.

**Acceptance Criteria**:

1. **WHEN** the CLI receives `--bot-path <module.path.ClassName>`, **THEN** it SHALL dynamically load the specified bot class from the `bots/` directory.
2. **WHERE** no `--bot-path` is provided, **THEN** the CLI SHALL use a default `RandomWalkStrategy` bot.
3. **WHERE** the bot path is invalid or the class doesn't exist, **THEN** the CLI SHALL display a clear error message and exit.
4. **WHEN** the bot class is loaded, **THEN** the CLI SHALL instantiate it with no constructor arguments.
5. **WHEN** the bot is successfully loaded, **THEN** the CLI SHALL log the bot name and confirm it's ready.
6. **WHERE** the current directory is not in `sys.path`, **THEN** the loader SHALL add it to enable bot imports.
7. **WHILE** playing a match, **WHEN** a `turn_update` event is received, **THEN** the client SHALL:
   - Call the bot's `decide()` method with the game state
   - Automatically submit the bot's action via `POST /playground/{session_id}/action`
8. **WHEN** starting a new match (or tournament in the future), **THEN** the user SHALL be able to specify a different bot implementation via `--bot-path`.
9. **WHERE** the bot conforms to the `BotInterface`, **THEN** it SHALL implement a `decide(state)` method that returns an action dict with:
   - `move`: A list `[dx, dy]` with movement delta
   - `spell`: Either a spell dict or `None`

---

### 8. Match Termination and Cleanup

**User Story**: As a bot developer, I want the client and server to properly clean up when a match ends, so that resources are released and I know the match is complete.

**Acceptance Criteria**:

1. **WHEN** a `game_over` event is received (winner decided), **THEN** the client SHALL:
   - Display the final game result
   - Stop processing further events
   - Keep the SSE connection active (not closed immediately)
2. **WHILE** the client is still running after game over, **THEN** the client SHALL NOT receive any future SSE events from that session.
3. **WHEN** the match ends, **THEN** the CLI SHALL display a message prompting the user to close/terminate the client (e.g., "Match complete. Press Ctrl+C to exit.").
4. **WHEN** the user terminates the client (Ctrl+C or exit), **THEN** the client SHALL:
   - Close the SSE connection
   - Signal the backend that the client has disconnected
5. **WHEN** the client disconnects after match completion, **THEN** the backend SHALL:
   - Close the game session
   - Terminate the Pygame visualizer window (if active)
   - Clean up session resources
6. **IF** the visualizer window is manually closed by the user, **THEN** the backend SHALL clean up the session but keep serving the SSE stream until client disconnects.

---

### 9. Error Handling and Logging

**User Story**: As a bot developer, I want clear error messages and detailed logging, so that I can debug issues quickly.

**Acceptance Criteria**:

1. **WHEN** any HTTP request fails, **THEN** the client SHALL:
   - Log the request URL and method
   - Log the error type and message
   - Include the HTTP status code if available
   - Raise an exception with context
2. **WHEN** the bot's `decide()` method fails, **THEN** the client SHALL:
   - Log the full exception with stack trace
   - Log the game state that caused the error
   - Continue processing without crashing
3. **WHERE** SSE reconnection occurs, **THEN** the client SHALL log:
   - Disconnection reason
   - Retry attempt number
   - Backoff duration
   - Reconnection success/failure
4. **WHEN** action submission is rejected by the backend, **THEN** the client SHALL:
   - Log the validation error details
   - Log the submitted action data
   - Log the expected vs actual turn number (if applicable)
5. **WHERE** logging level is set to DEBUG, **THEN** the client SHALL additionally log:
   - Full event payloads
   - Bot decision details
   - HTTP request/response bodies
6. **IF** a critical error occurs that prevents match continuation, **THEN** the client SHALL log a clear error summary before exiting.

---

### 10. Backend Support for Remote Players

**User Story**: As a backend developer, I want to support remote player actions, so that remote bots can participate in matches.

**Acceptance Criteria**:

1. **WHEN** a session is created with `player_1_config.bot_type: "player"`, **THEN** the backend SHALL:
   - NOT instantiate a bot for that player
   - Wait for actions via `/playground/{session_id}/action`
   - Use the provided player_id for identity
2. **WHILE** processing a turn, **IF** a player is remote, **THEN** the backend SHALL:
   - Wait up to `TURN_TIMEOUT_SECONDS` for an action
   - Use a default action if no submission within timeout
   - Validate the submitted action before applying
3. **WHEN** validating a remote player action, **THEN** the backend SHALL check:
   - Player ID matches one of the session participants
   - Turn number is current turn + 1
   - Action data is valid according to game rules
4. **WHERE** both players submit actions before timeout, **THEN** the backend SHALL process the turn immediately.
5. **IF** a remote player submits an action for the wrong turn, **THEN** the backend SHALL reject it with a clear error message.
6. **WHEN** a turn times out for a remote player, **THEN** the backend SHALL:
   - Use a default action (no move, no spell)
   - Log the timeout event
   - Include the timeout in the turn_update event
7. **WHEN** the client disconnects after a match ends, **THEN** the backend SHALL terminate the visualizer process and clean up session resources.

---

### 11. Configuration and Defaults

**User Story**: As a system administrator, I want configurable timeouts and limits, so that I can tune the system for different environments.

**Acceptance Criteria**:

1. **WHERE** SSE client configuration is provided, **THEN** it SHALL support:
   - `connect_timeout_seconds` (default: 5.0)
   - `read_timeout_seconds` (default: 30.0)
   - `reconnect_initial_backoff` (default: 0.5)
   - `reconnect_max_backoff` (default: 8.0)
   - `max_retries` (default: 5)
2. **WHERE** no configuration is provided, **THEN** the client SHALL use sensible defaults.
3. **WHEN** backend configuration is set via environment variables, **THEN** it SHALL respect:
   - `PLAYGROUND_TURN_TIMEOUT_SECONDS` (default: 5.0)
   - `PLAYGROUND_MAX_TURNS_PER_MATCH` (default: 100)
   - `PLAYGROUND_MATCH_LOOP_DELAY_SECONDS` (default: 1.0)
4. **IF** configuration values are invalid (negative, zero, non-numeric), **THEN** the system SHALL reject them with a validation error.

---

### 12. Lobby Mode Support

**User Story**: As a bot developer, I want to automatically match with other remote players via a lobby queue, so that I can play PvP matches without coordinating opponents manually.

**Acceptance Criteria**:

1. **WHEN** the CLI is invoked with `--mode lobby`, **THEN** the client SHALL join the matchmaking lobby queue instead of creating a direct match.
2. **WHERE** `--mode` is not specified, **THEN** the client SHALL default to `direct` mode (match against specified opponent).
3. **WHEN** joining the lobby queue, **THEN** the client SHALL:
   - Call `POST /lobby/join` with player_id and bot_config
   - Block (long-polling) until a match is found or timeout occurs
   - Wait up to 300 seconds for matchmaking
4. **WHILE** waiting in the lobby queue, **THEN** the client SHALL display a message indicating "Joining lobby queue, waiting for opponent..."
5. **WHEN** a match is found, **THEN** the backend SHALL:
   - Automatically match the first 2 players in the FIFO queue
   - Create a new game session with visualization enabled
   - Return session_id, opponent_id, and opponent_name to both players
6. **AFTER** receiving the match response, **THEN** the client SHALL:
   - Display the matched opponent information
   - Proceed to event streaming and automated gameplay
   - Play the match identically to direct mode
7. **IF** the player_id does not exist in the backend, **THEN** the backend SHALL return a 404 Not Found error.
8. **IF** the player is already in the lobby queue, **THEN** the backend SHALL return a 409 Conflict error with message "Player already in lobby queue".
9. **IF** no match is found within 300 seconds, **THEN** the client SHALL receive a timeout error and exit gracefully.
10. **WHEN** using lobby mode, **THEN** the `--opponent-id` argument SHALL be ignored (matchmaking determines opponent).
11. **WHERE** lobby mode is used with custom bots, **THEN** the client SHALL support `--bot-type custom` and `--bot-path` identically to direct mode.
12. **WHEN** using lobby mode, **THEN** the CLI SHALL support environment variable `MODE=lobby` as an alternative to `--mode lobby`.
13. **WHILE** in lobby queue, **IF** the user interrupts with Ctrl+C, **THEN** the client SHALL exit and the backend MAY remove the player from the queue.
14. **WHERE** visualization is enabled, **THEN** the backend SHALL automatically enable the Pygame visualizer for lobby matches.
15. **WHEN** both players are matched and the session starts, **THEN** the match SHALL proceed with the same turn-based gameplay as direct mode.

---

## Out of Scope

The following items are explicitly out of scope for this feature:

- Authentication and authorization (planned for future)
- Rate limiting (planned for future)
- Multi-bot coordination (single bot per client only)
- Tournament management via client (separate feature)
- Bot code upload via API (builtin bots only)
- Web-based UI for bot management
- Persistent bot statistics and rankings
- Bot versioning and rollback

