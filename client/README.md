# Spellcasters Playground Clients

This directory contains client libraries and CLI tools to interact with the Spellcasters Playground backend.

## Layout

- client/sse_client.py: Async SSE client library (re-exports from backend/client/sse_client.py for now)
- client/sse_client_main.py: CLI runner to connect to a session SSE stream
- client/bot_client.py: Bot client simulator library (re-exports from backend/client/bot_client.py for now)
- client/bot_client_main.py: CLI runner to register a player, start a match vs a built-in bot, and stream events

Note: At present, these modules re-export from backend/client/ to preserve backward compatibility. In a future cleanup, implementation code will be fully moved here and import paths updated.

## Prerequisites

- Backend server running locally:
  - uv run python -m uvicorn backend.app.main:app --port 8000 --reload

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

Register a new player, start a match vs a built-in bot, and automatically play the match.

### Play with Random Strategy

Use the built-in RandomWalkStrategy:

```bash
uv run python -m client.bot_client_main \
  --base-url http://localhost:8000 \
  --player-name "Random Bot" \
  --builtin-bot-id sample_bot_1 \
  --bot-type random \
  --max-events 100
```

### Play with Custom Bot

Load and play with a custom bot from the `bots/` directory:

```bash
uv run python -m client.bot_client_main \
  --base-url http://localhost:8000 \
  --player-name "Sample Bot 1" \
  --builtin-bot-id sample_bot_2 \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1 \
  --max-events 100
```

### CLI Arguments

- `--base-url`: Backend server URL (default: http://localhost:8000)
- `--player-name`: Name for the registered player (default: "CLI Bot")
- `--builtin-bot-id`: ID of builtin bot opponent (default: sample_bot_1)
- `--max-events`: Maximum number of events to process (default: 100)
- `--log-level`: Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `--bot-type`: Bot strategy type: `random` or `custom` (default: random)
- `--bot-path`: Python module path to custom bot class (required if --bot-type=custom)
  - Format: `module.path.ClassName`
  - Example: `bots.sample_bot1.sample_bot_1.SampleBot1`

## Environment Variables

- SPELLCASTERS_BASE_URL: default backend URL (default http://localhost:8000)
- SPELLCASTERS_SESSION_ID: default session ID for the SSE client CLI
- SPELLCASTERS_PLAYER_NAME: default player name for bot client CLI
- SPELLCASTERS_BUILTIN_BOT_ID: default built-in bot ID for bot client CLI
- SPELLCASTERS_MAX_EVENTS: default number of events to display

## Notes

- Action submission is fully implemented and enabled by default.
- The client supports both built-in strategies (RandomWalkStrategy) and custom bots that implement BotInterface.
- See [Client Bot Integration Design Document](../docs/specs/client-bot-integration/design.md) for detailed architecture and design documentation.

