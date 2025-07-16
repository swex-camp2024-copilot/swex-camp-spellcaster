# Spellcasters Playground Backend — **Revised Specification**

## 1 . Player Registration

### Endpoint

```
POST /players/register
```

**Request Body** (application/json)

```json
{
  "player_name": "FireMage",
  "submitted_from": "pasted"
}
```

**Response 200**

```json
{
  "player_id": "e7f2…",
  "player_name": "FireMage"
}
```

• `player_id` is a UUIDv4 generated server‑side.
• Names must be unique (case‑insensitive); duplicates ⇒ 409.

### Metadata (DB table `players`)

| field           | type               | notes              |
| --------------- | ------------------ | ------------------ |
| player\_id      | uuid PK            | returned to client |
| player\_name    | varchar(50) UNIQUE |                    |
| submitted\_from | varchar(10)        |                    |
| total\_matches  | int default 0      |                    |
| wins            | int default 0      |                    |
| losses          | int default 0      |                    |
| draws           | int default 0      |                    |
| created\_at     | timestamp          |                    |
| updated\_at     | timestamp          |                    |

Stats are incremented at **Match End** (see § 4.5).

---

## 2 . Starting a Playground Match

```
POST /playground/start
```

**Request Body**

```json
{
  "player_id": "e7f2…",
  "opponent_type": "builtin",          // "builtin" | "player"
  "opponent_id": null,                  // required if opponent_type=="player"
  "tick_delay_ms": 1000                 // optional, default 1000
}
```

Returns

```json
{ "session_id": "a1b2…" }
```

The server then:

1. Builds `player_1` from requesting user’s bot (must already be stored/validated).
2. Builds `player_2`:

   * **builtin** → load default opponent bot class.
   * **player** → load bot for `opponent_id` (read‑only).
3. Registers session in `SessionStore` and schedules an `asyncio.Task` running `match_loop(session_id)`.

---

## 3 . Session Data Model (in‑memory)

```python
class Session(TypedDict):
    session_id: str
    tick_delay_ms: int
    player_1: PlayerSide  # see below
    player_2: PlayerSide
    current_state: GameState
    pending_actions: dict[str, BotAction]  # keyed by player_id for next turn
    turn_index: int
    event_sinks: list[SSEEmitter]  # connected clients
    match_log: list[str]
    created_at: datetime

class PlayerSide(TypedDict):
    player_id: str | None  # None for builtin bot
    bot_instance: BotInterface
    action_source: Literal["builtin", "http"]
```

---

## 4 . Match Execution Flow

### 4.1 Tick Loop (single session)

```python
while not game_over and turn_index < 100:
    await collect_actions_or_timeout()
    new_state, events = engine.apply_turn(current_state, pending_actions)
    broadcast_sse_turn(new_state, events)
    pending_actions = {}
    turn_index += 1
    await asyncio.sleep(tick_delay_ms/1000)
```

* `collect_actions_or_timeout` waits until both HTTP actions arrive **or** timeout elapses (5 s default, configurable via `PLAYGROUND_ACTION_TIMEOUT`) and fills missing entries with `None`.

### 4.2 HTTP Action Endpoint

```
POST /playground/{session_id}/action
```

Body

```json
{
  "player_id": "e7f2…",
  "turn": 6,
  "action": { "move": [1,0], "spell": null }
}
```

Validation:

* session must exist
* `player_id` must match `player_1.player_id` **or** `player_2.player_id`
* `turn == session.turn_index + 1`
  On success store in `pending_actions`.

### 4.3 Timeout Handling

If a player’s action is missing after timeout:

* Replace with `None` during engine call = “no action”.
* Add log line: `<name> took no action (timeout)`.

### 4.4 SSE Event Format

Events sent with `event: turn` and `data:` JSON:

```json
{
  "turn": 5,
  "state": { ... },
  "actions": { "PlayerA": {...}, "PlayerB": null },
  "log": "PlayerB took no action (timeout)"
}
```

On match end ⇒ `event: game_over` payload:

```json
{ "winner": "PlayerA", "reason": "hp_zero" }
```

### 4.5 Stats Update & Log File

* After loop exits, update `players` table (wins/losses/draws/total\_matches).
* Serialize `match_log` to `logs/playground/{session_id}.log`.
* Keep session in memory for `IDLE_TTL_MIN` (default 30).
  Admin may delete sooner via `DELETE /playground/{session_id}`.

---

## 5 . Replay

```
GET /playground/{session_id}/replay
```

* If session still in memory → stream recorded turn events with `event: replay_turn` (no delay).
* Else → **404**.

---

## 6 . Admin Endpoints

| Method | Path                      | Purpose                                               |
| ------ | ------------------------- | ----------------------------------------------------- |
| DELETE | /playground/{session\_id} | Immediate cleanup of session + memory + log retention |
| GET    | /playground/active        | List active sessions + age                            |

(No auth layer for hackathon context.)

---

## 7 . Bot Validation (optional, can be toggled)

* Re‑use validation pipeline from Tournament: syntax check, subclass of `BotInterface`, ability to instantiate.
* Failure ⇒ reply **400** at `/playground/start`.

---

## 8 . Implementation Notes

* Use **FastAPI** + **sse-starlette** for SSE helpers.
* Session store: simple dict protected by `asyncio.Lock`; consider `ttl_cache` style cleanup.
* Ensure directory `logs/playground` exists on app start.
* `GameState`, `BotAction` import from shared `models.py` to avoid duplication.
* Limit simultaneous sessions via env `PLAYGROUND_MAX_SESSIONS`.

---

## 9 . Testing Matrix

| Test Case                       | Expected                          |
| ------------------------------- | --------------------------------- |
| Registration duplicate name     | 409 Conflict                      |
| Start match vs builtin          | 200 + session\_id                 |
| Action with bad turn index      | 400                               |
| Timeout path                    | Turn logged with "no action"      |
| SSE stream disconnect/reconnect | New connect gets next turn events |
| Replay after memory TTL         | 404                               |
| Concurrent sessions (N)         | All run independently             |

---

## 10 . Open Items (for future Arena/Tournament work)

1. Auth / role separation when competition scope expands.
2. Persistent DB vs in‑memory store for high player counts.
3. Rate limiting for `/action` endpoint.
4. Security hardening around `exec()` sandbox.
