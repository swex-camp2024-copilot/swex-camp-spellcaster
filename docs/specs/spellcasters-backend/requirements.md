# Spellcasters Playground Backend - Requirements

## Introduction

The Spellcasters Playground Backend is a FastAPI-based system that powers the "Playground" mode of the Spellcasters Hackathon. This backend enables participants to register, submit Python bots, and engage in real-time turn-based matches against built-in opponents or other participants. The system provides live match streaming via Server-Sent Events (SSE), comprehensive match logging, and replay functionality to support an engaging hackathon experience.

## Requirements

### 1. Player Registration System

**User Story**: As a participant, I want to register myself as a player so that I can participate in bot battles and track my performance.

**Acceptance Criteria**:
1. The system SHALL provide a POST /players/register endpoint that accepts player registration data
2. The system SHALL accept player_name and submitted_from fields in the registration payload
3. The system SHALL generate player_id as a URL-friendly slug derived from player_name
4. The system SHALL convert player_name to lowercase and replace non-alphanumeric characters (except spaces) with empty string
5. The system SHALL replace spaces in player_name with hyphens when generating player_id
6. The system SHALL automatically add numeric postfix (_2, _3, etc.) for duplicate slugs
7. The system SHALL keep built-in player IDs unchanged (e.g., "builtin_sample_1")
8. The system SHALL store player metadata including name, ID, submission source, and match statistics
9. The system SHALL initialize match statistics (total_matches, wins, losses, draws) to zero for new players
10. The system SHALL validate that player_name is a non-empty valid string and enforce case-insensitive uniqueness
11. The system SHALL return 409 Conflict when registering a duplicate player_name (case-insensitive)
12. The system SHALL return appropriate error responses for invalid registration data
13. The system SHALL provide a DELETE /players/{player_id} endpoint to remove registered players
14. The system SHALL prevent deletion of built-in players
15. The system SHALL prevent deletion of players with active sessions
16. The system SHALL cascade delete related game results when deleting a player
17. The system SHALL return appropriate error responses for invalid deletion operations

### 2. Match Session Management

**User Story**: As a participant, I want to start a new match session so that I can engage in bot battles with other players or built-in opponents.

**Acceptance Criteria**:
1. The system SHALL provide a POST /playground/start endpoint to initiate new match sessions
2. The system SHALL generate a unique session_id (UUID) for each new match
3. The system SHALL initialize session state with player slots, game state, match log, and turn counter
4. The system SHALL support both human players (via SSE) and built-in bot opponents
5. The system SHALL launch an automated match loop with configurable turn timing (default: 1 second)
6. The system SHALL return the session_id to the client upon successful session creation
7. The system SHALL maintain session state in memory throughout the match duration

### 3. Real-time Match Streaming

**User Story**: As a participant, I want to receive live updates about my match progress so that I can follow the battle in real-time.

**Acceptance Criteria**:
1. The system SHALL provide a GET /playground/{session_id}/events SSE endpoint for live match updates
2. The system SHALL send one event per turn containing turn number, game state, player actions, and events
3. The system SHALL include detailed action information such as moves, spells, targets, and hit results
4. The system SHALL provide descriptive event logs for each turn's actions and outcomes
5. The system SHALL send a final "game_over" event when the match concludes
6. The system SHALL handle SSE connection drops gracefully without stopping the match
7. The system SHALL validate session_id existence before establishing SSE connections

### 4. Player Action Submission

**User Story**: As a participant, I want to submit my bot's actions for each turn so that my bot can participate in the battle.

**Acceptance Criteria**:
1. The system SHALL provide a POST /playground/{session_id}/action endpoint for action submission
2. The system SHALL accept player_id, turn number, and action data in the submission payload
3. The system SHALL validate that the turn number matches the expected next turn
4. The system SHALL store submitted actions in the bot instance and retrieve them when processing turns
5. The system SHALL support move and spell actions with appropriate target validation
6. The system SHALL reject actions with invalid turn numbers with a 400 error response
7. The system SHALL handle malformed actions by skipping them and logging the error
8. The system SHALL distinguish between remote players (submitting via HTTP) and built-in bots (executing decide() logic) using the bot_type field in PlayerConfig
9. The system SHALL create PlayerBot instances for remote players that store and return submitted actions
10. The system SHALL call set_action() on remote player bots when actions are submitted via HTTP
11. The system SHALL clear submitted actions after they are consumed by the game engine to prevent action reuse across multiple turns
12. The system SHALL require a fresh action submission for each turn to maintain proper turn-based gameplay behavior
13. The system SHALL set submitted actions on bot instances BEFORE making them visible to the turn collection system to prevent race conditions where the game engine calls decide() before set_action() completes
14. The system SHALL guarantee atomic action submission where bot.set_action() completes before the action becomes available to collect_actions(), ensuring actions are always available when the game engine needs them

### 5. Turn Timeout Management

**User Story**: As a participant, I want the match to continue even if my opponent doesn't submit actions in time so that games don't stall indefinitely.

**Acceptance Criteria**:
1. The system SHALL implement a configurable timeout period for action submission (default: 5 seconds)
2. The system SHALL automatically skip actions for players who don't submit within the timeout
3. The system SHALL log timeout events with clear indication of which player timed out
4. The system SHALL proceed with turn processing when both actions are received OR timeout triggers
5. The system SHALL continue the match loop regardless of individual player timeouts
6. The system SHALL include timeout information in the match logs
7. The system SHALL send SSE updates even when players time out

### 6. Game Engine Integration

**User Story**: As a system administrator, I want the backend to integrate with the existing game engine so that battles follow the established game rules and mechanics.

**Acceptance Criteria**:
1. The system SHALL integrate with the existing game engine from the /game directory
2. The system SHALL apply player actions using the game engine's rule system
3. The system SHALL update game state through the game engine after each turn
4. The system SHALL determine win/loss/draw conditions using game engine logic
5. The system SHALL validate player actions against game rules before processing
6. The system SHALL handle game engine errors gracefully with appropriate logging
7. The system SHALL rewrite game engine components if needed for backend integration

### 7. Match Completion and Logging

**User Story**: As a participant, I want my matches to be properly recorded so that I can review the battle and track my performance.

**Acceptance Criteria**:
1. The system SHALL detect match end conditions (HP <= 0 or 100 turns reached)
2. The system SHALL determine winners, losers, or draws based on final game state
3. The system SHALL write detailed match logs to logs/playground/{session_id}.log
4. The system SHALL update player statistics (wins, losses, draws, total_matches) after each match
5. The system SHALL maintain session state in memory for replay access
6. The system SHALL format log files with one line per turn for easy parsing
7. The system SHALL include final match outcome in the log file

### 8. Match Replay System

**User Story**: As a participant, I want to replay completed matches so that I can analyze the battle and improve my bot strategies.

**Acceptance Criteria**:
1. The system SHALL provide a GET /playground/{session_id}/replay endpoint for match replay
2. The system SHALL stream all turn events immediately without timing delays
3. The system SHALL provide replay access for any completed session
4. The system SHALL serve replay data from in-memory session state
5. The system SHALL include all turn data, actions, and events in replay streams
6. The system SHALL handle replay requests for non-existent sessions with appropriate errors
7. The system SHALL maintain no access restrictions for replay functionality (hackathon context)

### 9. Built-in Bot System

**User Story**: As a participant, I want to test my bot against built-in opponents so that I can validate my bot's behavior without waiting for other players.

**Acceptance Criteria**:
1. The system SHALL provide pre-defined built-in bots with fixed player IDs and names
2. The system SHALL implement built-in bots as simple Python classes following the bot interface
3. The system SHALL execute built-in bot decisions synchronously within the match loop
4. The system SHALL treat built-in bots transparently to the backend (same interface as player bots)
5. The system SHALL not require SSE communication for built-in bot actions
6. The system SHALL support matches between human players and built-in bots
7. The system SHALL support matches between multiple built-in bots for testing
8. The system SHALL provide multiple built-in bot personalities with different strategies
9. The system SHALL ensure built-in bots follow the same action format as human players
10. The system SHALL handle built-in bot errors without affecting the match flow
11. The system SHALL log built-in bot actions in the same format as player actions

### 10. Error Handling and Resilience

**User Story**: As a system administrator, I want the backend to handle errors gracefully so that individual issues don't crash the entire system.

**Acceptance Criteria**:
1. The system SHALL log all errors with session ID context for debugging
2. The system SHALL handle broken SSE connections by removing handles while continuing matches
3. The system SHALL validate all input data and return appropriate HTTP error codes
4. The system SHALL continue match processing even when individual player actions fail
5. The system SHALL provide meaningful error messages for debugging and user feedback
6. The system SHALL implement proper exception handling throughout the codebase
7. The system SHALL maintain system stability under various error conditions

### 11. Performance and Scalability

**User Story**: As a hackathon organizer, I want the backend to handle multiple concurrent matches so that many participants can play simultaneously.

**Acceptance Criteria**:
1. The system SHALL support multiple concurrent match sessions
2. The system SHALL use asyncio for efficient async request handling
3. The system SHALL implement single-threaded match loops per session for isolation
4. The system SHALL maintain acceptable response times under concurrent load
5. The system SHALL persist session state and player data to a SQLite database file located at `data/playground.db`, resolved to an absolute path based on the repository root to ensure consistent behavior regardless of the process working directory
6. The system SHALL use a separate test database file at `data/test.db` for integration and e2e tests to prevent test data pollution in the production database
7. The system SHALL manage database connections efficiently for concurrent access
8. The system SHALL provide database migration support for schema changes
9. The system SHALL handle SSE connections efficiently for multiple clients, including external clients built using `/client/` libraries
10. The system SHALL provide performance monitoring capabilities for system health

### 12. Admin Management System

**User Story**: As a system administrator, I want to monitor and manage the playground system so that I can ensure smooth operation during the hackathon.

**Acceptance Criteria**:
1. The system SHALL provide a GET /admin/players endpoint to list all registered players
2. The system SHALL include player statistics and registration details in the admin player listing
3. The system SHALL provide a GET /playground/active endpoint to list all currently active sessions
4. The system SHALL include session status, participants, and duration in active session listings
5. The system SHALL provide a DELETE /playground/{session_id} endpoint for administrative session cleanup
6. The system SHALL gracefully terminate sessions and notify connected clients during admin cleanup
7. The system SHALL return appropriate error responses for invalid session IDs in admin operations

### 13. Lobby and Matchmaking System

**User Story**: As a participant, I want to join a matchmaking lobby so that I can automatically be matched with another remote player for PvP battles.

**Acceptance Criteria**:
1. The system SHALL provide a POST /lobby/join endpoint that accepts player_id and bot_config in the request payload
2. The system SHALL validate that the player exists in the database before adding to the lobby queue
3. The system SHALL return 404 Not Found when a non-existent player attempts to join the lobby
4. The system SHALL maintain a FIFO (first-in-first-out) queue for players waiting for matches
5. The system SHALL prevent duplicate entries by checking if a player is already in the queue
6. The system SHALL return 409 Conflict when a player attempts to join the lobby while already in queue
7. The system SHALL implement long-polling on the POST /lobby/join endpoint with a 300-second timeout
8. The system SHALL block the join request until a match is found or timeout occurs
9. The system SHALL automatically match the first two players in the queue when 2+ players are waiting
10. The system SHALL create a new game session with visualization enabled when matching occurs
11. The system SHALL return session_id, opponent_id, and opponent_name to both matched players
12. The system SHALL remove matched players from the queue after session creation
13. The system SHALL provide thread-safe queue operations using asyncio.Lock
14. The system SHALL provide a GET /lobby/status endpoint to query current queue size
15. The system SHALL provide a DELETE /lobby/leave/{player_id} endpoint to remove a player from the queue
16. The system SHALL return 404 Not Found when attempting to remove a player not in the queue
17. The system SHALL integrate with SessionManager to create matched game sessions
18. The system SHALL integrate with DatabaseService to validate players and retrieve player information
19. The system SHALL handle session creation errors gracefully without crashing the lobby service
20. The system SHALL log all lobby operations including joins, matches, and errors with appropriate context