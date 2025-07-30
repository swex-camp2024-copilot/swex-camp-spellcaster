# Spellcasters Backend Specification

## Overview

This backend module powers the "Playground" mode of the Spellcasters Hackathon. It allows participants to connect via SSE, submit Python bots, and engage in auto-looping turn-based matches vs built-in opponents or other participants.

Framework: **FastAPI** Language: **Python 3.10+** Execution model: **Single-threaded match loop with restricted bot code evaluation**

---

## Key Features

- Player registration and metadata tracking
- SSE support for live match updates
- Per-session turn handling with timeout logic
- Action collection and synchronization
- Post-match replay and log persistence

---

## Player Registration

### Endpoint (POST /players/register)

- Accepts player details:

```json
{
  "player_name": "FireMage",
  "submitted_from": "pasted"
}
```

- Returns a generated `player_id` (UUID string)

### Stored Player Metadata:

```python
{
  "player_name": str,
  "player_id": str,
  "submitted_from": str,  # e.g., "upload", "pasted"
  "total_matches": int,
  "wins": int,
  "losses": int,
  "draws": int
}
```

- Used to track participation, leaderboard scores, and UI feedback

---

## Session Lifecycle

### Match Start (POST /playground/start)

- Creates a unique `session_id` (e.g. UUID)

- Initializes in-memory session state:

  ```python
  session = {
    "session_id": str,
    "player_1": {
      "bot": BotInterface instance,
      "handle": "builtin" or SSE connection
    },
    "player_2": {
      "bot": BotInterface instance,
      "handle": "builtin" or SSE connection
    },
    "current_game_state": dict,
    "match_log": List[str],
    "turn_index": int
  }
  ```

- Launches match loop with auto-tick and optional delay (default: 1s)

- Returns session ID to frontend

---

## SSE Updates

### SSE Endpoint (GET /playground/{session\_id}/events)

- Client connects with `session_id` as path param
- Backend sends one event per turn:

```json
{
  "turn": 5,
  "game_state": { ... },
  "actions": [
    {"player": "PlayerA", "move": [4,5], "spell": {"type": "fireball", "target": [6,5], "hit": true}},
    {"player": "PlayerB", "move": [3,5], "spell": {"type": "shield"}}
  ],
  "events": ["PlayerA casts fireball at [6,5] (HIT)", "PlayerB shields"],
  "log_line": "Turn 5 completed. PlayerA hit PlayerB for 20 damage."
}
```

- Final event: `{ "event": "game_over", "winner": "PlayerA" }`

---

## Player Action Submission

### Endpoint (POST /playground/{session\_id}/action)

Payload:

```json
{
  "player_id": "PlayerA",
  "turn": 6,
  "action": { "move": [1, 0], "spell": null }
}
```

Rules:

- Backend validates `turn == session.turn_index + 1`
- Action stored until both players submit or timeout (see below)

### Timeout

- If one player doesn’t submit within 5 seconds (configurable):
  - Their action is skipped
  - Log includes: `"PlayerB took no action (timeout)"`

---

## Turn Processing

- Once both actions are received (or timeout triggers):
  - Game engine applies both actions
  - Updates game state
  - Increments turn counter
  - Sends SSE with turn result

---

## Match End

Conditions:

- One bot reaches HP <= 0 → win/loss
- 100 turns reached → draw

Actions:

- Send final `game_over` SSE event
- Write `logs/playground/{session_id}.log` (text format, 1 line per turn)
- Keep session state in memory (admin clears manually)

---

## Replay Support

### Endpoint (GET /playground/{session\_id}/replay)

- Streams all turn events immediately from memory
- No timing delays
- No access restrictions (hackathon context)

---

## Error Handling

- Invalid turn number → reject with 400 error
- Malformed bot action → skip and log
- Broken SSE connection → remove handle, match continues
- Backend logs all errors with session ID context

---

## Architecture Notes

- FastAPI async endpoints
- Background match loop per session using asyncio
- Match logs flushed to disk only at match end
- Sprite rendering handled by visualizer, not backend

---

## Testing Plan

- ✅ Unit tests

  - Game engine logic
  - Bot validation and isolation
  - Timeout and action fallback

- ✅ Integration tests

  - Full Playground match run (mock bots)
  - SSE connection lifecycle
  - Replay from completed session

- ✅ Manual QA

  - Log inspection
  - Visualizer runs using log file
  - Latency and timeout edge cases

---

## Next Steps

1. Implement player registration and metadata tracking
2. Implement session manager with turn loop controller
3. Build SSE endpoints and event emitter
4. Create bot action intake + timeout logic
5. Integrate replay and logging
6. Wire to frontend playground UI

