# Lobby System Implementation Plan
## Problem Analysis
**Current PvP Issue:** The existing direct PvP mode is broken. When two players try to play against each other:

- Player 1 runs: `--player-id alice --opponent-id bob`
- Player 2 runs: `--player-id bob --opponent-id alice`

Each client independently calls `POST /playground/start`, creating **two separate sessions** instead of one shared session. The backend has no coordination mechanism to let the second player discover and join the existing session.

## Solution: Simple FIFO Lobby with Long-Polling
Based on your requirements, I'll implement a minimal lobby system that:

- Maintains a simple FIFO queue for players waiting to be matched
- Auto-matches when 2+ players are in queue
- Uses long-polling (join endpoint blocks until matched)
- No queue management features (leave, timeout, status) for simplicity
- Server-controlled settings with visualization enabled by default
- CLI uses `--mode lobby` flag

---

## Implementation Tasks
### Phase 1: Backend Lobby System
#### 1.1 Lobby Data Models (backend/app/models/lobby.py)
Create models for lobby system:

- `LobbyJoinRequest` - Player join request with bot config
- `LobbyMatchResponse` - Match result with session_id and opponent info
- `QueueEntry` - Internal queue entry with asyncio.Event for long-polling

#### 1.2 LobbyService (backend/app/services/lobby_service.py)
Implement core lobby logic:

- FIFO queue using `collections.deque`
- `join_queue(player_id, bot_config)` - Add to queue, try match, wait (long-poll)
- `_try_match()` - Auto-match first 2 players, create session, notify both
- Thread-safe with `asyncio.Lock`
- Long-polling via `asyncio.Event.wait()`

#### Key Logic:
```
async def join_queue(player_id, bot_config) -> str:
    # Add to queue with asyncio.Event
    # Try immediate match
    # Wait on event (blocks until matched)
    # Return session_id
```

#### 1.3 Lobby API Endpoints (backend/app/api/lobby.py)
- `POST /lobby/join` - Long-polling endpoint that blocks until matched
  - Request: `{player_id, bot_config}`
  - Response: `{session_id, opponent_id, opponent_name}`
  - Timeout: 300 seconds (5 minutes)

#### 1.4 StateManager Integration
- Add `LobbyService` to `StateManager` (`backend/app/core/state.py`)
- Initialize during startup with reference to `SessionManager`
- Register lobby routes in `main.py`

### Phase 2: Client Library Updates
#### 2.1 BotClient Lobby Support (client/bot_client.py)
Add lobby methods:
- `join_lobby(player_id, bot_config)` - Long-polling join
  - POST to `/lobby/join` with 300s timeout
  - Returns session_id when matched
  - Raises on timeout or error

#### 2.2 CLI Mode Flag (`client/bot_client_main.py`)
Add `--mode` argument:
- `--mode lobby` - Join lobby and auto-match
- `--mode direct` - Direct match with specified opponent (existing behavior)
Update run_bot() logic:
```
if mode == "lobby":
    session_id = await client.join_lobby(player_id, bot_config)
    logger.info(f"Matched! Session: {session_id}")
else:
    session_id = await client.start_match(player_id, opponent_id)
```

### Phase 3: Documentation Updates
#### 3.1 Functional Spec (docs/specs/spellcasters-functional-spec.md)
Add **§5.4 Lobby (PvP Queue)** section:

- FIFO queue mechanics
- Auto-matching algorithm
- Long-polling API contract
- Session creation flow

#### 3.2 Backend Requirements (`docs/specs/spellcasters-backend/requirements.md`)
Add **Requirement 13: Lobby and Matchmaking System:**

- Queue join functionality
- FIFO matching logic
- Long-polling support
- Session creation requirements

#### 3.3 Backend Design (`docs/specs/spellcasters-backend/design.md`)
Add:
- **§3.5 Lobby Models** - Data structures
- **§8 Lobby Service** - Component design with queue logic, matching algorithm

#### 3.4 Backend Tasks (docs/specs/spellcasters-backend/tasks.md)
Add **Task 12: Lobby and PvP Matchmaking System**:

- 12.1 Implement LobbyService with FIFO queue
- 12.2 Create lobby API endpoints
- 12.3 Add long-polling support
- 12.4 Update client for lobby mode
- 12.5 Write comprehensive tests

#### 3.5 Client README (client/README.md)
Update PvP section with lobby mode examples:
```
# Join lobby with random bot
uv run python -m client.bot_client_main --mode lobby

# Join lobby with custom bot
uv run python -m client.bot_client_main \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1
```

#### 3.6 Client Requirements (`docs/specs/bot-client/requirements.md`)
Add **Requirement 12: Lobby Mode Support**:

- Join lobby queue
- Wait for match via long-polling
- Handle timeout and errors
- CLI support

#### 3.7 Client Design (docs/specs/bot-client/design.md)
Add **§6 Lobby Mode Architecture**:

- Lobby join workflow
- Long-polling mechanism
- Error handling
- CLI integration

### Phase 4: Testing
#### 4.1 Backend Unit Tests (`backend/tests/test_lobby_service.py`)
Test LobbyService:

- Queue join and match logic
- FIFO ordering
- Long-polling behavior
- Concurrent joins
- Edge cases (empty queue, single player)

#### 4.2 Backend Integration Tests (`backend/tests/test_lobby_api.py`)
Test lobby endpoints:

- Join endpoint behavior
- Long-polling timeout
- Concurrent client matching
- Error scenarios

#### 4.3 E2E Tests (`client/tests/e2e/test_lobby_pvp.py`)
Test full workflow:

- Two clients join lobby concurrently
- Auto-matched to same session
- Play complete match
- Verify both clients see same events

#### 4.4 Update Existing Tests
- Add lobby scenarios to test_system_integration.py
- Test lobby + visualization integration

---

## Architecture Diagrams
### Lobby Flow
```
Player A                 LobbyService              SessionManager
   |                          |                          |
   |--join_queue()----------->|                          |
   |  (blocks on event.wait()) |                          |
   |                          |<--queue has 1 player     |
   |                          |                          |
Player B                      |                          |
   |                          |                          |
   |--join_queue()----------->|                          |
   |  (blocks on event.wait()) |                          |
   |                          |<--queue has 2 players!   |
   |                          |                          |
   |                          |--create_session()------->|
   |                          |<--session_id-------------|
   |                          |                          |
   |<--event.set()------------|                          |
   |  (returns session_id)    |                          |
   |                          |                          |
   |                          |--event.set()------------>|
   |                          |  (returns session_id)    |
```

### Long-Polling Mechanism
```
# Server side
async def join_queue(player_id, bot_config):
    entry = QueueEntry(event=asyncio.Event())
    queue.append(entry)
    
    await try_match()  # Match if 2+ players
    
    await entry.event.wait()  # Blocks until matched
    return entry.session_id

# Client side
response = await httpx.post("/lobby/join", timeout=300)
session_id = response.json()["session_id"]
```

---

## Key Design Decisions
1. **Long-polling over SSE**: Simpler for this use case - single request/response
1. **FIFO queue**: Fair matching, simple to implement
1. **Auto-match**: No confirmation step, starts immediately
1. **No queue management**: Keeps implementation minimal
1. **Server-controlled settings**: Visualization always enabled for lobby matches
1. **Backward compatible**: Existing direct mode unchanged

---

## File Changes Summary
### New Files (8)
- backend/app/models/lobby.py
- backend/app/services/lobby_service.py
- backend/app/api/lobby.py
- backend/tests/test_lobby_service.py
- backend/tests/test_lobby_api.py
- client/tests/e2e/test_lobby_pvp.py

### Modified Files (10)
- backend/app/core/state.py - Add LobbyService
- backend/app/main.py - Register lobby routes
- client/bot_client.py - Add join_lobby()
- client/bot_client_main.py - Add --mode flag
- client/README.md - Update PvP section
- docs/specs/spellcasters-functional-spec.md - Add §5.4
- docs/specs/spellcasters-backend/requirements.md - Add Req 13
- docs/specs/spellcasters-backend/design.md - Add §8
- docs/specs/spellcasters-backend/tasks.md - Add Task 12
- docs/specs/bot-client/requirements.md - Add Req 12
- docs/specs/bot-client/design.md - Add §6

---

## Testing Strategy
1. Unit: LobbyService queue operations, matching logic
1. Integration: API endpoints, concurrent requests
1. E2E: Full client-to-client workflow
1. Load: Multiple concurrent lobby joins

---

## Success Criteria
✅ Two clients can join lobby and auto-match to same session
✅ Long-polling blocks until match found
✅ Session creation uses server-controlled settings
✅ Visualization enabled by default for lobby matches
✅ CLI supports both direct and lobby modes
✅ All documentation updated
✅ Comprehensive test coverage
✅ Backward compatible with existing direct mode