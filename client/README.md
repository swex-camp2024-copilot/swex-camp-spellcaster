# Spellcasters Playground Clients

This directory contains client libraries and CLI tools to interact with the Spellcasters Playground backend.

## Layout

- `client/sse_client.py`: Async SSE client library for event streaming
- `client/sse_client_main.py`: CLI runner to connect to a session SSE stream
- `client/bot_client.py`: Bot client simulator library for remote gameplay
- `client/bot_client_main.py`: CLI runner to play matches against builtin bots or other remote players

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

## SSE Client CLI

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

## Bot Client CLI

The Bot Client CLI allows you to play matches remotely against builtin bots or other remote players. It automatically handles event streaming, bot decision-making, and action submission.

### Quick Start (Minimum Arguments)

Run a match using your OS username and the default random bot:

```bash
uv run python -m client.bot_client_main
```

This uses:

- Player ID: Current OS username (via `whoami`)
- Opponent: `builtin_sample_1` (default builtin bot)
- Bot: `RandomWalkStrategy` (simple random movement)

### Play vs Builtin Bot (Random Strategy)

```bash
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_2 \
  --bot-type random
```

### Play vs Builtin Bot (Custom Bot)

Load a custom bot from the `bots/` directory:

```bash
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_1 \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1
```

### Play vs Another Remote Player (PvP)

**Lobby mode** provides automatic matchmaking for PvP gameplay. Players join a FIFO queue and are automatically matched when two players are waiting.

#### Quick Start - Join Lobby with Random Bot

```bash
uv run python -m client.bot_client_main --mode lobby
```

The client will:
1. Join the lobby queue
2. Wait for another player to join (long-polling, up to 5 minutes)
3. Automatically match and start the game
4. Play the match with visualization enabled

#### Join Lobby with Custom Bot

```bash
uv run python -m client.bot_client_main \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1
```

#### Two Players Joining Lobby (Different Terminals)

```bash
# Terminal 1 (joins first, waits for match)
uv run python -m client.bot_client_main \
  --player-id alice \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1

# Terminal 2 (joins second, both auto-match immediately)
uv run python -m client.bot_client_main \
  --player-id bob \
  --mode lobby \
  --bot-type custom \
  --bot-path bots.tactical_bot.tactical_bot.TacticalBot
```

**How Lobby Matching Works:**
- Players are matched in **FIFO** (first-in, first-out) order
- When 2+ players are waiting, the first two are automatically matched
- Both players' requests return with the same `session_id`
- The match starts immediately with visualization enabled
- If no match is found within 5 minutes, the request times out

### Direct Mode (Specify Opponent)

For direct matches against builtin bots or coordinated testing, use direct mode:

```bash
# vs builtin bot (default mode)
uv run python -m client.bot_client_main \
  --mode direct \
  --opponent-id builtin_sample_1

# Shorthand (--mode direct is default)
uv run python -m client.bot_client_main \
  --opponent-id builtin_sample_1
```

### CLI Arguments

- `--base-url`: Backend server URL (default: `http://localhost:8000`, env: `BASE_URL`)
- `--player-id`: Existing registered player ID (default: OS username via `whoami`, env: `PLAYER_ID`)
- `--mode`: Match mode: `direct` (specify opponent) or `lobby` (auto-match via queue) (default: `direct`, env: `MODE`)
- `--opponent-id`: Opponent ID - builtin bot (e.g., `builtin_sample_1`) or remote player (default: `builtin_sample_1`, env: `OPPONENT_ID`)
  - **Only used in direct mode**
- `--bot-type`: Bot strategy: `random` or `custom` (default: `random`, env: `BOT_TYPE`)
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
export MODE=lobby                    # or 'direct'
export OPPONENT_ID=builtin_sample_1  # only used in direct mode
export BOT_TYPE=custom
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

## Notes

- Action submission is fully automatic - the client handles all action timing
- Matches are fully automated - no manual intervention needed
- Custom bots must implement `BotInterface` from `bots/bot_interface.py`
- The client supports automatic SSE reconnection with exponential backoff
- Game state is provided to the bot's `decide()` method on every turn

