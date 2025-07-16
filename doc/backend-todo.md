# Spellcasters Playground Backend — TODO Checklist

> Tick each box as you complete the task.  Follow the **Backend Build Blueprint**; this list mirrors and expands the steps for quick tracking.

## 0 — Project Bootstrap

* [ ] Create Poetry project `spellcasters_backend` (Python 3.10)
* [ ] Add dependencies: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`, `pytest`, `httpx`, `sse-starlette`
* [ ] Initialise Git repository & `.gitignore`
* [ ] Create folder tree: `app/`, `tests/`, `logs/`, `docker/`
* [ ] Add `README.md` with project summary & run instructions

## 1 — Core Domain Models & Stores

* [ ] Implement `PlayerMeta` model (`app/models/player.py`)
* [ ] Implement `SessionState` model (`app/models/session.py`)
* [ ] Create `app/stores.py` with in‑memory dicts `PLAYERS`, `SESSIONS` + CRUD helpers
* [ ] Unit tests for models and store helpers

## 2 — Player Registration API

* [ ] Scaffold `FastAPI` instance in `app/main.py`
* [ ] `POST /players/register` endpoint

  * [ ] Reject duplicate `player_name`
  * [ ] Return `player_id` (uuid4)
* [ ] Tests: success & duplicate name cases

## 3 — Bot Submission & Validation

* [ ] Implement `app/bot_validator.py` (syntax + interface check)
* [ ] `POST /bots/submit` endpoint

  * [ ] Verify `player_id` exists
  * [ ] Store latest `bot_code` in `PLAYERS`
* [ ] Tests: valid bot, syntax error, missing interface

## 4 — Game Basics

* [ ] Add `app/engine/constants.py` (BOARD\_SIZE, SPELLS, etc.)
* [ ] Implement `DummyBot` in `app/builtin_bots/random_bot.py`

## 5 — Session Manager & Match Start

* [ ] Create `app/session_manager.py`

  * [ ] `create_session(player1_id, player2_id)`
  * [ ] Spawn `asyncio.Task` running `run_match(session)`
* [ ] `POST /playground/start` endpoint (PvE for now)
* [ ] Integration test: start match, session stored

## 6 — SSE Infrastructure

* [ ] Utility `app/sse.py` to emit JSON events
* [ ] `GET /playground/{session_id}/events` endpoint
* [ ] Manual check with EventSource in browser

## 7 — Action Submission & Timeout

* [ ] `POST /playground/{session_id}/action` endpoint

  * [ ] Validate turn number, player ownership
* [ ] Implement timeout logic (env `TURN_TIMEOUT_SECONDS`, default 5)
* [ ] Unit test: one player timeout path

## 8 — Turn Processor & Game Logic

* [ ] `app/engine/turn_processor.py` applying two `BotAction`s
* [ ] Integrate into session loop
* [ ] Implement `update_stats` helper & use on `game_over`
* [ ] Tests: win, draw scenarios

## 9 — Logging & Replay

* [ ] Append log lines per turn into `session.match_log`
* [ ] Flush `logs/playground/{session_id}.log` at `game_over`
* [ ] `GET /playground/{session_id}/replay` endpoint (instant stream)
* [ ] Test replay endpoint

## 10 — Admin Utilities

* [ ] `POST /admin/sessions/{session_id}/clear` endpoint
* [ ] `GET /admin/players` endpoint (leaderboard snapshot)

## 11 — Configuration & Environment

* [ ] Support env vars: `TURN_DELAY_SECONDS`, `TURN_TIMEOUT_SECONDS`, `MAX_TURNS`
* [ ] Add `.env.example`

## 12 — Packaging & Deployment

* [ ] Create `docker/Dockerfile` (uses uvicorn)
* [ ] Update `README.md` with Docker instructions

## 13 — Testing & QA

* [ ] Unit tests reach ≥ 80 % coverage
* [ ] Integration tests pass (player registration → full match)
* [ ] Load test: 20 concurrent sessions without event‑loop starvation

## 14 — Stretch Goals / Nice‑to‑Have

* [ ] Sprite upload endpoint (PNG validation)
* [ ] Basic bearer‑token auth for admin routes
* [ ] Swap in Redis for stores (future scalability)

---

**Progress Notes**

* Add date + initials when closing a task for easy audit.
