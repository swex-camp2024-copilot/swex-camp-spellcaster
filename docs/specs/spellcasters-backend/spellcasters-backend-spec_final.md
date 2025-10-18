# Spellcasters Backend Functional Specification (SWEX 2025 Hackathon)

> **Status:** Review draft — consolidated from v1/v2/v3. All prior open questions resolved on **Aug 10, 2025** (Asia/Singapore). **Scope is Playground only**; Tournament features are deferred to a separate spec. Some DB tables are reserved for future Tournament support (see §3.4).

---

## 0. Purpose & Scope

This document specifies the backend for the **Spellcasters** hackathon project (Playground only). It covers:

* Player registration and identity
* Built‑in bots (no upload API in this version)
* **Playground** (adhoc 1v1 arena) matches
* Persistence, APIs, data models, and event flows (SSE)
* Operational, logging, and testing requirements

**Out of scope for this doc**: Tournament orchestration and endpoints (a separate spec will define those). Authentication/authorization remains out of scope for the hackathon.

---

## 1. Final Assumptions & Decisions

* **Admin auth:** **None** for hackathon (no bearer token).
* **Rate limiting:** **None** for now (including `/action`).
* **Bot execution time:** **100 ms** per `decide()` (soft budget); turn/action hard timeout **`TURN_TIMEOUT_SECONDS = 5`** seconds.
* **Replay retention:** **In‑memory only** until session cleanup (no DB replay table).
* **Built‑in bots (IDs per design):**

  * Player IDs: `builtin_sample_1`, `builtin_tactical`
  * Bot classes: `sample_bot_1`, `tactical_bot`
* **Persistence:** **SQLite** via **SQLModel**. Database file is **`data/playground.db`** resolved to an **absolute path** from repo root.

---

## 2. Architecture Overview

**Language/Framework:** Python 3.10+, **FastAPI**. Async I/O for HTTP/SSE. Game engine is deterministic per turn, fed by two `BotAction`s.

**Key components**

* **PlayerRegistry** — register players, maintain stats (in `/backend/app/services/player_registry.py`)
* **BuiltinBots** — manage **built‑in** bot instances/factories (in `/backend/app/services/builtin_bots.py`)
* **SessionManager** — create/run/cleanup Playground match sessions, hold in‑memory state, emit SSE (in `/backend/app/services/session_manager.py`)
* **StateManager** — centralized lifecycle management for all services, health monitoring, and statistics (in `/backend/app/core/state.py`)
* **SSEManager** — manage SSE connections per session, broadcast events (in `/backend/app/services/sse_manager.py`)
* **MatchLogger** — record turn events for replay (in `/backend/app/services/match_logger.py`)
* **TurnProcessor** — coordinate turn execution, action collection (in `/backend/app/services/turn_processor.py`)
* **GameAdapter** — bridge between backend and game engine (in `/backend/app/services/game_adapter.py`)
* **ErrorHandlers** — global exception handling with security-aware logging (in `/backend/app/core/error_handlers.py`)
* **Storage** — SQLite via **SQLModel**; in-memory replay logs

**Concurrency model**: each active match runs in its own `asyncio.Task`; within a match, logic is single‑threaded. Built-in bots execute synchronously within the match loop.

**Service Initialization**: All services are initialized and managed by the `StateManager` during application startup via lifespan hooks. The `runtime` module provides lazy access to services using Python's module-level `__getattr__` for backward compatibility.

---

## 3. Data Model (SQLite, SQLModel)

> Use **SQLModel** models (Pydantic v2) to initialize schema. All timestamps in UTC. DB file path: `data/playground.db` (absolute).

### 3.1 Players

```
players(
  player_id           TEXT PRIMARY KEY,  -- UUIDv4
  player_name         TEXT UNIQUE NOT NULL,
  is_builtin          INTEGER NOT NULL DEFAULT 0,    -- 0/1 boolean
  sprite_path         TEXT,                           -- optional asset hint
  minion_sprite_path  TEXT,                           -- optional asset hint
  submitted_from      TEXT,                           -- e.g. "online", "seed"
  total_matches       INTEGER NOT NULL DEFAULT 0,
  wins                INTEGER NOT NULL DEFAULT 0,
  losses              INTEGER NOT NULL DEFAULT 0,
  draws               INTEGER NOT NULL DEFAULT 0,
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL
)
```

### 3.2 Sessions (Playground)

```
sessions(
  session_id   TEXT PRIMARY KEY, -- UUIDv4
  p1_id        TEXT NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
  p2_id        TEXT NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
  status       TEXT NOT NULL CHECK (status IN ('running','completed','aborted')),
  started_at   TEXT,
  ended_at     TEXT
)
```

### 3.3 Game Results

```
game_results(
  result_id    TEXT PRIMARY KEY, -- UUIDv4
  session_id   TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  winner_id    TEXT,             -- NULL for draw
  turns_played INTEGER,
  damage_p1    INTEGER,
  damage_p2    INTEGER,
  summary      TEXT,
  created_at   TEXT NOT NULL
)
```

### 3.4 Tournaments (Reserved for future spec)

```
tournaments(
  tournament_id TEXT PRIMARY KEY, -- UUIDv4
  name          TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('draft','ready','running','completed')),
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
)

tournament_players(
  tournament_id TEXT NOT NULL REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
  player_id     TEXT NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
  PRIMARY KEY (tournament_id, player_id)
)

matches(
  match_id      TEXT PRIMARY KEY, -- UUIDv4
  tournament_id TEXT REFERENCES tournaments(tournament_id),
  p1_id         TEXT NOT NULL,
  p2_id         TEXT NOT NULL,
  scheduled_ord INTEGER,
  status        TEXT NOT NULL CHECK (status IN ('pending','running','completed','aborted')),
  winner_id     TEXT,
  turns_played  INTEGER,
  started_at    TEXT,
  ended_at      TEXT
)
```

> Tables present for forward‑compatibility; Tournament endpoints and flows are **not** part of this spec.

---

## 4. Configuration (Env Vars)

Configuration is managed via `/backend/app/core/config.py` using Pydantic Settings. Environment variables can be prefixed with `PLAYGROUND_`.

| Name                                 | Default                                    | Description                               |
| ------------------------------------ | ------------------------------------------ | ----------------------------------------- |
| `PLAYGROUND_DATABASE_URL`            | `sqlite+aiosqlite:///./data/playground.db` | SQLite database connection URL            |
| `PLAYGROUND_HOST`                    | `0.0.0.0`                                  | Server bind host                          |
| `PLAYGROUND_PORT`                    | `8000`                                     | Server bind port                          |
| `PLAYGROUND_TURN_TIMEOUT_SECONDS`    | `5.0`                                      | Wait for player action before skip        |
| `PLAYGROUND_MAX_TURNS_PER_MATCH`     | `100`                                      | Draw threshold                            |
| `PLAYGROUND_MATCH_LOOP_DELAY_SECONDS`| `1.0`                                      | Delay between processed turns             |
| `PLAYGROUND_SESSION_CLEANUP_MINUTES` | `30`                                       | Keep finished session in memory           |
| `PLAYGROUND_MAX_CONCURRENT_SESSIONS` | `50`                                       | Safety cap for concurrent sessions        |

See `/backend/app/core/config.py` for complete configuration details.

---

## 5. API Specification

All responses are JSON. Errors use structured `ErrorResponse` model with proper HTTP status codes:

```json
{
  "error": "ERROR_TYPE",
  "message": "Human-readable error message",
  "details": { "...": "..." },
  "session_id": "optional-session-id",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

See `/backend/app/models/errors.py` for specialized error response types (ValidationErrorResponse, TimeoutErrorResponse, etc.).

### 5.1 Health & Monitoring

**GET** `/health` — Comprehensive health check with StateManager status

Response:
```json
{
  "status": "healthy|degraded|unhealthy",
  "service": "spellcasters-playground-backend",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "state_manager": {
    "status": "ready",
    "is_ready": true,
    "uptime_seconds": 1234.5,
    "services": {
      "database": "ready",
      "sse_manager": "ready",
      "match_logger": "ready",
      "session_manager": "ready",
      "admin_service": "ready"
    }
  }
}
```

**GET** `/stats` — System statistics

Response:
```json
{
  "service": "spellcasters-playground-backend",
  "version": "1.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "statistics": {
    "uptime_seconds": 1234.5,
    "active_sessions": 5,
    "active_sse_connections": 8,
    "total_players": 42
  }
}
```

**GET** `/` — Root endpoint with API information

### 5.2 Players

**POST** `/players/register`

* Request:

```json
{ "name": "FireMage", "submission_method": "http" }
```

* Rules: `name` unique (case‑insensitive). Failure ⇒ 409.
* Response `201 Created`:

```json
{
  "player_id": "uuid-v4",
  "name": "FireMage",
  "submission_method": "http",
  "is_builtin": false,
  "total_matches": 0,
  "wins": 0,
  "losses": 0,
  "draws": 0,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**GET** `/players/{player_id}` — returns player metadata and basic stats.

**DELETE** `/players/{player_id}` — delete a player if not builtin and not part of running sessions; cascades `game_results`. Returns `204 No Content`.

### 5.3 Playground (Arena)

**POST** `/playground/start`

* Request:

```json
{
  "player_1_config": {
    "bot_type": "builtin|http",
    "bot_id": "sample_bot_1",
    "player_id": "optional-uuid"
  },
  "player_2_config": {
    "bot_type": "builtin",
    "bot_id": "sample_bot_2"
  }
}
```

* Validates configurations and creates session. Built-ins use `bot_id` directly, HTTP bots require `player_id`.
* Response `200 OK`:

```json
{ "session_id": "uuid-session" }
```

Client should then connect to `/playground/{session_id}/events` for SSE stream.

**POST** `/playground/{session_id}/action`

* Request:

```json
{ "player_id": "uuid-p1", "turn": 6, "action": { "move": [1,0], "spell": null } }
```

* Validates: session exists; player belongs to session; `turn == turn_index + 1`. On success, stores pending action.

**GET** `/playground/{session_id}/events` (SSE)

* Emits `event: turn_update` with `data: <json-string>` each turn and finally `event: game_over`.
* `data` example:

```json
{
  "turn": 5,
  "state": { "...": "..." },
  "actions": [ {"player_id": "p1", "resolved": {"move": [1,0]}}, {"player_id": "p2", "resolved": null} ],
  "events": ["p2 timeout"],
  "log_line": "p2 timed out"
}
```

**GET** `/playground/{session_id}/replay`

* Streams recorded turn events with `event: replay_turn` (no delay) if the session is still retained; otherwise 404.

**Admin (hackathon; no auth)**

* `GET /playground/active` — list active sessions.
* `DELETE /playground/{session_id}` — cleanup immediately.
* `GET /admin/players` — list players with stats (and builtin flag).

> **No Bot upload endpoints** in this version; bots are built‑in only.

---

## 6. Error Handling & State Management

### 6.1 Global Error Handlers

All exceptions are handled by centralized error handlers in `/backend/app/core/error_handlers.py`:

* **PlaygroundError** base class for all custom exceptions with:
  - HTTP status code
  - Error message
  - Optional session_id
  - Optional details dictionary

* **Specialized handlers** for 15+ exception types:
  - PlayerNotFoundError, PlayerRegistrationError
  - SessionNotFoundError, SessionAlreadyActiveError
  - InvalidActionError, InvalidTurnError
  - BotExecutionError, BotTimeoutError
  - GameEngineError, DatabaseError
  - ValidationError, SSEConnectionError
  - AuthorizationError, RateLimitError
  - ConfigurationError

* **Security-aware logging**: Sanitizes sensitive data before logging
* **Structured responses**: Uses ErrorResponse models with proper HTTP status codes
* **Pydantic validation**: Automatic handling of request validation errors

All handlers are registered via `register_error_handlers(app)` during application startup.

### 6.2 State Manager

The `StateManager` in `/backend/app/core/state.py` provides centralized lifecycle management:

* **Service initialization** in proper dependency order:
  1. DatabaseService
  2. SSEManager
  3. MatchLogger
  4. SessionManager (depends on SSE + MatchLogger)
  5. AdminService (depends on Database + SessionManager)

* **Health monitoring** via `get_health()`:
  - Overall system status (ready/degraded/unhealthy)
  - Individual service states
  - Uptime tracking
  - Initialization error tracking

* **Statistics collection** via `get_statistics()`:
  - Active sessions count
  - Active SSE connections count
  - System uptime
  - Total players

* **Graceful shutdown** in reverse dependency order:
  - Terminates all active sessions
  - Disconnects all SSE streams
  - Cleans up all services

The StateManager is initialized during FastAPI lifespan startup and cleaned up on shutdown.

### 6.3 Service Access Pattern

Services are accessed via `/backend/app/services/runtime.py` which uses Python's module-level `__getattr__` for lazy loading:

```python
from backend.app.services import runtime

# Access services lazily
session = await runtime.session_manager.get_session(session_id)
await runtime.sse_manager.broadcast(session_id, event)
```

This provides backward compatibility while using the centralized StateManager.

---

## 7. Session Lifecycle & Engine

### 7.1 In‑Memory Session (per match)

```python
class PlayerSide(TypedDict):
    player_id: str | None  # None for builtin
    bot_instance: BotInterface
    action_source: Literal["builtin", "http"]

class Session(TypedDict):
    session_id: str
    tick_delay_ms: int
    player_1: PlayerSide
    player_2: PlayerSide
    current_state: GameState
    pending_actions: dict[str, BotAction]  # by player_id
    turn_index: int
    event_sinks: list[SSEEmitter]
    match_log: list[str]
    created_at: datetime
```

### 7.2 Loop (per turn)

```
while not game_over and turn_index < MAX_TURNS:
  await collect_actions_or_timeout()
  new_state, events = engine.apply_turn(current_state, pending_actions)
  broadcast_sse_turn(new_state, events)
  pending_actions = {}
  turn_index += 1
  await asyncio.sleep(TURN_DELAY_SECONDS)
```

### 7.3 Bot Execution Isolation

* `decide(state)` executed via `asyncio.to_thread(...)` into a per‑session `ThreadPoolExecutor(max_workers=1)` with wall‑clock limit **BOT\_DECIDE\_TIMEOUT\_MS**. Timeout ⇒ treat as **no action** and log.
* Restricted built‑ins; deny `open`, `import os`, `subprocess`, etc. Whitelist safe modules (`math`, `random`).

### 7.4 End & Stats Update

* `game_over` when any HP ≤ 0 or `MAX_TURNS` reached (draw).
* Update `players` stats: increment `total_matches`; apply win/loss/draw for both.
* Insert `game_results` row; append summary line to `match_log`; write file `logs/playground/{session_id}.log`.
* Keep session in memory for **PLAYGROUND\_IDLE\_TTL\_MIN**.

---

## 8. SSE Event Contract

* Content‑Type: `text/event-stream`; `Cache-Control: no-cache`.
* Each message uses `event: <type>` + `data: <json-string>` (stringified via `json.dumps`).
* Events:

  * `turn_update` —

    ```json
    { "turn": n, "state": {…}, "actions": [{"player_id": "…", "resolved": {…}}, …], "events": ["…"], "log_line": "…" }
    ```
  * `game_over` — `{ "winner": "player_id|null", "reason": "hp_zero|max_turns" }`
  * `replay_turn` — same as `turn_update`, emitted by replay endpoint.

---

## 9. Interaction Diagrams (Key Journeys)

### 9.1 Player Registration — obtain unique Player ID

```mermaid
sequenceDiagram
  actor User
  participant API as FastAPI
  participant PlayerSvc as PlayerService
  participant DB as SQLite

  User->>API: POST /players/register {player_name}
  API->>PlayerSvc: validate name uniqueness
  PlayerSvc->>DB: INSERT players(...)
  DB-->>PlayerSvc: ok
  PlayerSvc-->>API: player_id
  API-->>User: 201 {player_id, player_name}
```

### 9.2 Playground Game — adhoc 1v1 arena

```mermaid
sequenceDiagram
  actor P1 as Player 1
  actor P2 as Player 2 / Built-in
  participant API as FastAPI
  participant BotSvc as BotService
  participant Sess as SessionManager
  participant Eng as GameEngine
  participant SSE as SSE Stream

  P1->>API: POST /playground/start {player_1_id, player_2_id}
  API->>BotSvc: load builtin bot for builtin ids
  BotSvc-->>API: bot instance(s)
  API->>Sess: create session + task
  Sess-->>P1: {session_id, sse_url}
  P1-->>SSE: GET /events (subscribe)
  loop each turn
    P1->>API: POST /{session}/action {player_id, turn, action}
    Sess->>Eng: apply_turn(state, actions)
    Eng-->>Sess: new_state + events
    Sess-->>SSE: event: turn_update / data: {...}
  end
  Sess-->>SSE: event: game_over
  Sess->>File: write logs/playground/{session_id}.log
```

---

## 10. Error Handling & Edge Cases

* Duplicate player name ⇒ `409 Conflict`.
* Invalid `session_id` / not participant ⇒ `404` / `403`.
* Bad `turn` index ⇒ `400`.
* SSE disconnects: do **not** terminate the match; new subscribers can attach and receive subsequent turns.
* Timeout: missing action after `TURN_TIMEOUT_SECONDS` ⇒ treat as no‑op and log.
* Built‑in bot failures ⇒ log and treat as no action for that turn.

---

## 11. Implementation Notes & Recommendations

### 11.1 Core Modules

* **`/backend/app/main.py`** — FastAPI application with lifespan hooks for StateManager initialization
* **`/backend/app/core/`** — Core functionality:
  - `state.py` — StateManager for service lifecycle
  - `error_handlers.py` — Global exception handling
  - `exceptions.py` — Custom exception classes
  - `config.py` — Pydantic Settings configuration
  - `database.py` — SQLModel database initialization

* **`/backend/app/services/`** — Business logic services:
  - `session_manager.py` — Session lifecycle and match orchestration
  - `sse_manager.py` — SSE connection management and broadcasting
  - `match_logger.py` — Turn event logging for replay
  - `turn_processor.py` — Turn execution coordination
  - `player_registry.py` — Player registration and stats
  - `builtin_bots.py` — Built-in bot management
  - `game_adapter.py` — Game engine integration
  - `admin_service.py` — Admin operations
  - `database.py` — Database operations
  - `runtime.py` — Lazy service accessor pattern

* **`/backend/app/api/`** — API route handlers:
  - `players.py` — Player endpoints
  - `sessions.py` — Session creation
  - `actions.py` — Action submission
  - `streaming.py` — SSE streaming
  - `replay.py` — Replay streaming
  - `admin.py` — Admin endpoints

* **`/backend/app/models/`** — Pydantic/SQLModel data models:
  - `database.py` — Database models
  - `players.py` — Player models
  - `sessions.py` — Session and game state models
  - `actions.py` — Action models
  - `events.py` — SSE event models
  - `errors.py` — Error response models

### 11.2 Key Implementation Details

* **StateManager lifecycle**: Initialized in FastAPI lifespan startup, services initialized in dependency order, graceful shutdown in reverse order
* **Service access**: Use `from backend.app.services import runtime` and access services via properties (e.g., `runtime.session_manager`)
* **Error handling**: All exceptions flow through centralized handlers, security-aware logging, structured error responses
* **SSE management**: Connection tracking per session, graceful disconnect on shutdown, heartbeat events
* **Replay**: In-memory turn event storage via MatchLogger, fast streaming without delays
* **Sessions**: In-memory state with async coordination, background match tasks, automatic cleanup
* **Built-in bots**: Loaded via `builtin_bots.py`, mapped to specific bot IDs (`sample_bot_1`, `sample_bot_2`, etc.)

### 11.3 Testing

* **Unit tests**: Individual service components, models, utilities
* **Integration tests**: Complete workflows in `/backend/tests/test_system_integration.py`
  - End-to-end match flows
  - Concurrent session handling
  - SSE streaming
  - Error propagation
  - Component integration
* **Test fixtures**: `/backend/tests/conftest.py` with test_client, database fixtures
* Run tests: `uv run pytest` or `uv run pytest backend/tests/test_system_integration.py -v`

---

## 12. Testing Matrix

* **Unit**: player registration; duplicate name; engine `apply_turn`; timeout path; stats update; player deletion rules.
* **Integration**: PvE and PvP match; SSE stream consumption; replay; concurrent sessions.
  - See `/backend/tests/test_system_integration.py` for comprehensive integration tests
  - Tests cover: complete match workflows, concurrent sessions, SSE streaming, error handling, component integration
* **Admin**: `/admin/players` returns expected shape; health/stats endpoints.
* **Load (lightweight)**: 20 concurrent Playground sessions; ensure event‑loop responsive.

---

## 13. Glossary

* **Playground**: on‑demand 1v1 match (player vs player or built‑in).
* **SSE**: Server‑Sent Events; uni‑directional push over HTTP.
* **Replay**: fast stream of recorded turn events of a finished session retained in memory.
* **StateManager**: centralized service lifecycle manager providing initialization, health monitoring, and graceful shutdown.
* **ErrorHandlers**: global exception handling system with security-aware logging and structured error responses.
* **MatchLogger**: service that records turn events in memory for replay functionality.
* **SSEManager**: manages SSE connections per session and broadcasts events to connected clients.
* **Runtime**: module-level service accessor using `__getattr__` for lazy loading from StateManager.
