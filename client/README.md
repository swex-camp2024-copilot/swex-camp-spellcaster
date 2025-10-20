# Spellcasters Client Tools

Client libraries and CLI tools for remote play modes: **PvC** (Player vs Computer) and **PvP** (Player vs Player).

> **Note**: For game mode terminology and local testing, see the [Main README](../README.md).
> - **Playground (Local)**: No client/server needed - use `main.py` for local bot testing
> - **PvC Mode**: Remote play against server's builtin bots (this client + backend server)
> - **PvP Mode**: Auto-matchmaking between players (this client + backend server)
> - **Tournament Mode**: Coming soon for hackathon finale

## Prerequisites

- Backend server running locally:

```bash
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- Player registration (if not using OS username):

```bash
curl -X POST http://localhost:8000/players/register \
  -H "Content-Type: application/json" \
  -d '{"player_name": "your-username"}'
```

## Client Overview

- `client/sse_client.py`: Async SSE client library for event streaming
- `client/sse_client_main.py`: CLI runner to connect to a session SSE stream
- `client/bot_client.py`: Bot client simulator library for remote gameplay
- `client/bot_client_main.py`: CLI runner to play matches against builtin bots or other remote players

### SSE Client

Connect to an existing session and print the first N events.

```
uv run python -m client.sse_client_main \
  --base-url http://localhost:8000 \
  --session-id <SESSION_ID> \
  --max-events 10
```

To obtain a session ID quickly, you can create a session:

```
curl -s -X POST http://localhost:8000/playground/start \
  -H 'Content-Type: application/json' \
  -d '{"player_1_config":{"player_id":"builtin_sample_1","bot_type":"builtin","bot_id":"sample_bot_1"},"player_2_config":{"player_id":"builtin_sample_2","bot_type":"builtin","bot_id":"sample_bot_2"}}'
```

### Bot Client CLI

The Bot Client CLI allows you to play matches remotely in **PvC** (vs builtin bots) or **PvP** (vs other players) modes. It automatically handles event streaming, bot decision-making, and action submission.

#### Quick Start (Minimum Arguments)

Run a PvC match using your OS username and the default random bot:

```bash
uv run python -m client.bot_client_main
```

This uses:
- Player ID: Current OS username (via `whoami`)
- Mode: PvC (default)
- Opponent: `builtin_sample_1` (default builtin bot)
- Bot: `RandomWalkStrategy` (simple random movement)

---

## PvC Mode (Player vs Computer)

Play against the server's builtin bots. Perfect for testing your bot against standard opponents.

### PvC with Random Bot Strategy

```bash
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_2 \
  --bot-type random
```

### PvC with Custom Bot

Load a custom bot from the `bots/` directory:

```bash
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_1 \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1
```

### Available Builtin Opponents

- `builtin_sample_1` - Sample bot with basic strategy
- `builtin_sample_2` - Alternative sample bot
- More builtin bots may be available - check server documentation

---

## PvP Mode (Player vs Player)

Auto-matchmaking for real-time battles between two players. Players join a queue and are automatically matched.

### Quick Start - Join PvP Queue

```bash
uv run python -m client.bot_client_main --mode lobby
```

The client will:
1. Join the PvP matchmaking queue
2. Wait for another player to join (long-polling, up to 5 minutes)
3. Automatically match and start the game
4. Play the match with visualization enabled

### PvP with Custom Bot

```bash
uv run python -m client.bot_client_main \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1
```

### PvP Example: Two Players (Different Terminals)

```bash
# Terminal 1 (Player 1 - joins first, waits for match)
uv run python -m client.bot_client_main \
  --player-id alice \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1

# Terminal 2 (Player 2 - joins second, both auto-match immediately)
uv run python -m client.bot_client_main \
  --player-id bob \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.tactical_bot.tactical_bot.TacticalBot
```

**PvP Matchmaking Details:**
- Players matched in **FIFO** (first-in, first-out) order
- When 2+ players waiting, first two are automatically matched
- Both players receive the same `session_id`
- Match starts immediately with visualization enabled
- 5-minute timeout if no match found

---

## Tournament Mode (Future)

Multi-player tournament mode (4/6/16 players) is planned for the hackathon finale. Stay tuned!

---

## Bot Client Instructions

### CLI Arguments

- `--base-url`: Backend server URL (default: `http://localhost:8000`, env: `BASE_URL`)
- `--player-id`: Registered player ID (default: OS username via `whoami`, env: `PLAYER_ID`)
- `--mode`: Play mode: `direct` (PvC) or `lobby` (PvP) (default: `direct`, env: `MODE`)
  - `direct` - PvC mode: Play against specified builtin bot
  - `lobby` - PvP mode: Join matchmaking queue for auto-match
- `--opponent-id`: Builtin bot ID for PvC mode (e.g., `builtin_sample_1`) (default: `builtin_sample_1`, env: `OPPONENT_ID`)
  - **Only used in PvC mode (`--mode direct`)**
  - Ignored in PvP mode
- `--bot-type`: Bot strategy: `random` or `custom` (default: `random`, env: `BOT_TYPE`)
  - `random` - Use built-in random movement bot
  - `custom` - Load custom bot from `bots/` directory
- `--bot-path`: Module path for custom bot (required if `--bot-type=custom`, env: `BOT_PATH`)
  - Format: `module.path.ClassName`
  - Example: `bots.sample_bot1.sample_bot_1.SampleBot1`
- `--max-events`: Maximum events to process (default: `100`, env: `MAX_EVENTS`)
- `--log-level`: Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`, env: `LOG_LEVEL`)

### Environment Variables

All CLI arguments can be set via environment variables:

```bash
export BASE_URL=http://localhost:8000
export PLAYER_ID=myusername
export MODE=lobby                    # 'direct' (PvC) or 'lobby' (PvP)
export OPPONENT_ID=builtin_sample_1  # only used in PvC mode (MODE=direct)
export BOT_TYPE=custom               # 'random' or 'custom'
export BOT_PATH=bots.sample_bot1.sample_bot_1.SampleBot1
export MAX_EVENTS=100
export LOG_LEVEL=INFO

uv run python -m client.bot_client_main
```

### Match Termination

When a match ends:

1. The client displays `"Match complete. Press Ctrl+C to exit."`
2. The SSE connection remains active (no more events received)
3. Press `Ctrl+C` to terminate the client
4. The backend closes the session and terminates the visualizer window

### Troubleshooting

**Player not found (404 error)**:

- Register your player first via `POST /players/register`
- Or use an existing registered player ID

**Backend connection failed**:

- Ensure backend server is running at the specified URL
- Check firewall settings if using remote backend

**Bot loading error**:

- Verify bot path is correct (e.g., `bots.sample_bot1.sample_bot_1.SampleBot1`)
- Ensure bot implements `BotInterface` with `name` property and `decide()` method
- Check bot module is in Python path (run from project root)

**Wrong turn number (400 error)**:

- This usually indicates network latency or bot taking too long
- Backend will use default action and match continues
- Consider optimizing bot's `decide()` method

---

## Testing

### Run Fast Tests (Default)

```bash
# Run all client tests (skips slow E2E tests by default)
uv run pytest client/tests -v

# Fast tests complete in ~2 seconds
```

### Run Slow Tests

Some E2E tests are marked as slow (~60s each) because they run full game simulations. These are skipped by default but can be run explicitly:

```bash
# Run only slow tests
uv run pytest client/tests -v -m slow

# Run all tests including slow ones
uv run pytest client/tests -v -m ""
```

### Test Markers

- `@pytest.mark.slow` - Tests that take 60+ seconds (game simulations)
- Default behavior: Skip slow tests to keep CI fast
