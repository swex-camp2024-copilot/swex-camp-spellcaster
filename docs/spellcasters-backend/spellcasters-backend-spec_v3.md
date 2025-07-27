# Spellcasters Backend Specification — REVISION 3

This document supersedes **“Spellcasters Backend”**. It fixes open points and inconsistencies and adds clarifying implementation details.

---

## 1. Review Summary

| #  | Topic                                    | Issue                                                                                                       | Resolution                                                                                                                                         |
| -- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **Player ⇆ Bot mapping**                 | Registration returns a `player_id`, but there is no endpoint that uploads bot code or links it to a player. | Add **/bots/submit** endpoint that stores bot code against `player_id`. Session start now takes two `player_id` values and loads their latest bot. |
| 2  | **Duplicate player names**               | Spec does not enforce uniqueness.                                                                           | Registration rejects duplicate `player_name` (400).                                                                                                |
| 3  | **Action sender identity**               | POST /action uses `player_id`, but `session.player_1`/`player_2` store only `bot` + `handle`.               | Store full `player_meta` in session and validate `player_id` matches registered slot.                                                              |
| 4  | **SSE JSON payload**                     | SSE ‘data: …’ must be a single string.                                                                      | Serialize payload with `json.dumps` before writing to stream.                                                                                      |
| 5  | **Turn timeout default**                 | Hard‑coded 5 s; no config hook.                                                                             | Expose `TURN_TIMEOUT_SECONDS` env var (default 5).                                                                                                 |
| 6  | **Restricted exec may block event‑loop** | `exec()` of untrusted code can be CPU heavy.                                                                | Run bot `decide()` inside a separate `ThreadPoolExecutor` with 100 ms timeout using `asyncio.to_thread`.                                           |
| 7  | **Match log write timing**               | Wording conflicted (per‑turn console vs file at end).                                                       | Clarify: log lines are appended in memory per turn; full file is flushed once at `game_over`.                                                      |
| 8  | **Stat persistence**                     | Metadata wins/losses… not updated.                                                                          | Add helper `update_stats(player_id, result)` in match end.                                                                                         |
| 9  | **Concurrent sessions**                  | Spec said single‑threaded but multiple sessions may run.                                                    | Each session runs its loop in an independent `asyncio.Task`; no shared state mutation.                                                             |
| 10 | **Replay after cleanup**                 | Replay endpoint undefined after admin cleanup.                                                              | Replay only while session object remains; admin cleanup deletes replay capability.                                                                 |

---

## 2. Enhanced API Surface

### 2.1 Player Registration

`POST /players/register`

```jsonc
{
  "player_name": "FireMage",
  "submitted_from": "pasted" // optional
}
```

Response ‑ `201 Created`

```jsonc
{
  "player_id": "uuid‑v4",
  "message": "Registration successful"
}
```

Rules

- Reject 400 if `player_name` already exists.
- Persist metadata row (default counters to 0).

### 2.2 Bot Submission

`POST /bots/submit`

```jsonc
{
  "player_id": "uuid‑v4",
  "bot_code": "<base64‑encoded or plain text>"
}
```

Flow

1. Verify `player_id`.
2. Static validation:
   - `class` implementing `BotInterface` exists.
   - Compiles without `SyntaxError`.
3. Store latest code (overwrites prior) in memory / DB.
4. Return 201 or 400 with error list.

> **Note**: Sprite upload handled by separate endpoint (future work – reuse rules from earlier spec).

### 2.3 Start Playground Match

`POST /playground/start`

```jsonc
{
  "player_1_id": "uuid‑p1",
  "player_2_id": "builtin_random" // or uuid‑p2 for PvP
}
```

Returns

```jsonc
{
  "session_id": "uuid‑session",
  "sse_url": "/playground/{session_id}/events"
}
```

Validation

- Both IDs must exist (`builtin_…` are reserved aliases).
- Instantiate bots via latest code snapshot or built‑in bot factory.

### 2.4 Submit Action

`POST /playground/{session_id}/action` Unchanged; payload validated that `player_id` matches one of the two players.

### 2.5 SSE Events

Sent with `event: turn` or `event: game_over` fields for easy client routing.

---

## 3. In‑Memory Data Models (Pydantic)

```python
class PlayerMeta(BaseModel):
    player_id: str
    player_name: str
    submitted_from: str | None = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_matches: int = 0

class SessionState(BaseModel):
    session_id: str
    player_1_id: str
    player_2_id: str
    current_game_state: dict
    match_log: list[str]
    turn_index: int = 0
    awaiting_actions: dict[str, BotAction] = {}
```

---

## 4. Concurrency & Execution

- **Bot Code Isolation**: Executed inside `ThreadPoolExecutor(max_workers=1)` per session to avoid blocking the main asyncio loop. 100 ms hard timeout enforced via `concurrent.futures.TimeoutError`.
- **RestrictedPython** config restricts built‑ins (no `open`, `import os`, etc.) but exposes `math`, `random`, `collections` through controlled globals.
- **Session Loop**: background `asyncio.Task` created on match start:
  ```python
  async def run_match(session: SessionState):
      while not game_over:
          await collect_actions()
          apply_turn()
          await asyncio.sleep(TURN_DELAY)
  ```

---

## 5. Environment Variables

| Name                   | Default | Description                        |
| ---------------------- | ------- | ---------------------------------- |
| `TURN_DELAY_SECONDS`   | `1`     | Delay between processed turns      |
| `TURN_TIMEOUT_SECONDS` | `5`     | Wait for player action before skip |
| `MAX_TURNS`            | `100`   | Draw threshold                     |

---

## 6. Logging & Persistence

- **In‑game log** (`session.match_log`) captures per‑turn text lines.
- On `game_over`, write to `logs/playground/{session_id}.log`.
- Add summary footer: winner, turns played, timestamps.

---

## 7. Statistic Update Helper

```python
def update_stats(winner_id: str | None, p1: str, p2: str):
    for pid in (p1, p2):
        meta = players[pid]
        meta.total_matches += 1
    if winner_id is None:
        players[p1].draws += 1
        players[p2].draws += 1
    else:
        players[winner_id].wins += 1
        loser = p2 if winner_id == p1 else p1
        players[loser].losses += 1
```

---

## 8. Admin Utilities

- `POST /admin/sessions/{session_id}/clear` – delete session from memory.
- `GET  /admin/players` – list all player metadata.
- Authentication: none (in‑room hackathon).  ⚠️ Add bearer token if reused later.

---

## 9. Testing Matrix

- **Unit** – player registration, bot validation, timeout logic.
- **Integration** – full PvP and PvE match; SSE consumption with `httpx` + `sseclient`.
- **Load** – spin 20 concurrent sessions; ensure no event‑loop starvation.

---

## 10. Implementation Checklist

1. `players` store (simple dict, later Redis / SQLite).
2. `/players/register` + `/bots/submit` endpoints.
3. Bot validator utility.
4. Session manager + state models.
5. SSE emitter util (encodes JSON string, sets `Content-Type: text/event-stream`).
6. Background match loop with timeouts.
7. Logging + disk flush.
8. Stats update.
9. Replay endpoint.
10. Admin cleanup endpoints.

---

> **End of Revision 1**

