# Backend Build Blueprint (Spellcasters Hackathon)

This document converts **Backend Spec V3** into an executable, incremental delivery plan plus a set of ready‑to‑use prompts for a code‑generation LLM.  Each phase is broken into bite‑sized tasks that build on each other without dead code.  Prompts are provided in the correct order; copy & paste each into the LLM as you progress.

---

## Phase 0 – Project Bootstrap

| Step | Goal                                                                   |
| ---- | ---------------------------------------------------------------------- |
| 0.1  | Create Poetry project + `pyproject.toml` (Python 3.10).                |
| 0.2  | Add deps: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`. |
| 0.3  | Initialise Git repo; add `.gitignore`, `README.md`.                    |
| 0.4  | Create folder structure `app/`, `tests/`, `logs/`.                     |

## Phase 1 – Core Domain Models

| Step | Depends on | Goal                                                                        |
| ---- | ---------- | --------------------------------------------------------------------------- |
| 1.1  | 0.x        | Implement `models/player.py` with `PlayerMeta` (Pydantic).                  |
| 1.2  | 1.1        | Implement `models/session.py` with `SessionState` + helper methods.         |
| 1.3  | 1.2        | Create in‑memory stores (`stores.py`) for players & sessions (simple dict). |

## Phase 2 – Player Registration API

| Step | Depends on | Goal                                                   |
| ---- | ---------- | ------------------------------------------------------ |
| 2.1  | 1.x        | Scaffold `main.py` FastAPI app.                        |
| 2.2  | 2.1        | Implement `POST /players/register` with validations.   |
| 2.3  | 2.2        | Unit tests covering duplicate names & UUID generation. |

## Phase 3 – Bot Submission & Validation

| Step | Depends on | Goal                                                                 |
| ---- | ---------- | -------------------------------------------------------------------- |
| 3.1  | 2.x        | Implement placeholder `bot_validator.py` (syntax + interface check). |
| 3.2  | 3.1        | Implement `POST /bots/submit` endpoint storing code in `stores.py`.  |
| 3.3  | 3.2        | Add basic unit tests (happy path + syntax error).                    |

## Phase 4 – Session Manager & Match Loop

| Step | Depends on | Goal                                                              |
| ---- | ---------- | ----------------------------------------------------------------- |
| 4.1  | 3.x        | Write `engine/game_state.py` (minimal board + constants).         |
| 4.2  | 4.1        | Implement `SessionManager` that spawns `asyncio.Task` per match.  |
| 4.3  | 4.2        | Implement `POST /playground/start` (PvE with built‑in dummy bot). |
| 4.4  | 4.3        | Integration test: start match → session dict created.             |

## Phase 5 – SSE Infrastructure

| Step | Depends on | Goal                                                    |
| ---- | ---------- | ------------------------------------------------------- |
| 5.1  | 4.x        | Utility `sse.py` to stream JSON events (`event: turn`). |
| 5.2  | 5.1        | Implement `GET /playground/{session_id}/events`.        |
| 5.3  | 5.2        | Manual test with browser EventSource logging events.    |

## Phase 6 – Action Submission & Timeout

| Step | Depends on | Goal                                                              |
| ---- | ---------- | ----------------------------------------------------------------- |
| 6.1  | 5.x        | Implement `POST /playground/{session_id}/action` with turn check. |
| 6.2  | 6.1        | Add timeout handling inside `SessionManager.collect_actions()`.   |
| 6.3  | 6.2        | Integration test: one player timeout path.                        |

## Phase 7 – Game Engine Integration

| Step | Depends on | Goal                                                                           |
| ---- | ---------- | ------------------------------------------------------------------------------ |
| 7.1  | 6.x        | Implement `engine/turn_processor.py` applying two `BotAction`s to `GameState`. |
| 7.2  | 7.1        | Wire `turn_processor` into match loop; update stats on game\_over.             |
| 7.3  | 7.2        | Unit tests for win, draw conditions.                                           |

## Phase 8 – Logging & Replay

| Step | Depends on | Goal                                                              |
| ---- | ---------- | ----------------------------------------------------------------- |
| 8.1  | 7.x        | Append per‑turn log lines in session.                             |
| 8.2  | 8.1        | On game\_over flush to `logs/`.                                   |
| 8.3  | 8.2        | Implement `GET /playground/{session_id}/replay` (instant stream). |

## Phase 9 – Admin Endpoints

| Step | Depends on | Goal                                                    |
| ---- | ---------- | ------------------------------------------------------- |
| 9.1  | 8.x        | `POST /admin/sessions/{sid}/clear` deletes from memory. |
| 9.2  | 9.1        | `GET /admin/players` returns leaderboard snapshot.      |

## Phase 10 – Packaging & Delivery

| Step | Depends on | Goal                                      |
| ---- | ---------- | ----------------------------------------- |
| 10.1 | all        | Add `.env.example` + `docker/Dockerfile`. |
| 10.2 | 10.1       | Update README with run instructions.      |

---

## Prompts for Code‑Generation LLM

Paste each prompt into your coding LLM sequentially.

### Prompt 0 – Project Bootstrap

```text
You are ChatGPT‑Coder.
Task: Create a Poetry project called `spellcasters_backend` (Python 3.10). Add dependencies fastapi, uvicorn[standard], pydantic, python‑dotenv. Create folders: app/, tests/, logs/. Add .gitignore for Python & Poetry artefacts. Initialise README.md with project summary.
Output: Changed files ready for commit.
```

### Prompt 1 – Player Meta Model

```text
Task: Inside app/models, add `player.py` with `PlayerMeta` Pydantic model:
fields: player_id (str), player_name (str), submitted_from (Optional[str]), wins, losses, draws, total_matches (all int default 0).
Create tests/test_player_model.py verifying defaults.
```

### Prompt 2 – Session Model & Store

```text
Task: Add app/models/session.py with SessionState model per spec.  Then, add app/stores.py with two dicts: PLAYERS, SESSIONS. Provide helper functions: add_player(meta), get_player(pid), add_session(state), get_session(sid).
Include tests for CRUD helpers.
```

### Prompt 3 – FastAPI Skeleton & Player Registration

```text
Task: Create app/main.py with FastAPI instance. Implement POST /players/register accepting player_name & optional submitted_from. Reject duplicates. Generate uuid4 for player_id. Store via stores.add_player(). Return 201 JSON with player_id.
Add tests using TestClient covering success & duplicate name.
```

### Prompt 4 – Bot Validator & Submission Endpoint

```text
Task: Implement app/bot_validator.py: function validate_bot_code(code:str)->list[str] returning error list (empty if ok). Use ast.parse for syntax, ensure class subclassing BotInterface via ast inspection placeholder.
Add POST /bots/submit expecting player_id & bot_code. Validate id exists & code. Store code in PLAYERS[pid]['bot_code'].
Tests: valid bot, syntax error.
```

````
### Prompt 5 – Game Constants & Dummy Bot
```text
Task: In app/engine/constants.py add BOARD_SIZE, etc. Implement DummyBot in app/builtin_bots/random_bot.py returning random moves.
````

### Prompt 6 – Session Manager & Start Match

```text
Task: Implement app/session_manager.py with create_session(player1_id, player2_id). Spawn asyncio.create_task(run_match(state)). Implement POST /playground/start accordingly (PvE only, builtin_random alias).
Provide smoke test starting match and asserting session appears.
```

### Prompt 7 – SSE Utility & Events Endpoint

```text
Task: Add app/sse.py helper function streaming JSON dicts. Implement GET /playground/{sid}/events returning EventSourceResponse (use sse-starlette).
Manual check with browser EventSource.
```

### Prompt 8 – Action Endpoint & Timeout Logic

```text
Task: Implement POST /playground/{sid}/action payload {player_id, turn, action}. Validate turn progression. Store in session.awaiting_actions.
In session loop, wait until both actions present or timeout (TURN_TIMEOUT_SECONDS) then process turn.
Unit test: one‑player timeout path.
```

### Prompt 9 – Turn Processor & Game Over

```text
Task: Implement app/engine/turn_processor.py with apply_turn(state, a1, a2). Handle HP, win/draw. Update stats via update_stats util.
Add tests for win scenario.
```

### Prompt 10 – Logging & Replay

```text
Task: Append log lines each turn into session.match_log. On game_over flush file to logs/. Implement GET /playground/{sid}/replay streaming all prior turn events instantly.
Test replay endpoint with TestClient.
```

### Prompt 11 – Admin Endpoints

```text
Task: Add POST /admin/sessions/{sid}/clear deleting session & TASK. Add GET /admin/players returning list[PlayerMeta].
```

### Prompt 12 – Docker & README Update

```text
Task: Create Dockerfile exposing uvicorn app: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Update README with docker run instructions.
```