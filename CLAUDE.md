# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spellcasters** is a hackathon game challenge where participants program bots to battle in a turn-based, wizard-themed strategy arena. Each bot controls a wizard who can move, cast spells, summon minions, and collect artifacts — all on a 10x10 battlefield.

**GitHub Project**: [swex-camp-spellcaster](https://github.com/swex-camp2024-copilot/swex-camp-spellcaster)

## Game Modes

The project supports four play modes with standardized terminology:

| Mode | Description | Command/Tool |
|------|-------------|--------------|
| **Playground (Local)** | Test bots locally using `main.py` - no server required | `uv run python main.py tournament` |
| **PvC (Client ↔ Server)** | Remote play against server's builtin bots | `client/bot_client_main.py --mode direct` |
| **PvP (2 Clients ↔ Server)** | Auto-matchmaking between two players' custom bots | `client/bot_client_main.py --mode lobby` |
| **Tournament (Future)** | Multi-client tournament (4/6/16 players) for hackathon finale | To be implemented |

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync --all-extras

# Setup git hooks
uv run pre-commit install
```

### Code Quality
```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Check formatting
uv run ruff format --check .

# Security scan
uv run bandit -r .

# Run all quality checks
uv run ruff check . && uv run ruff format --check . && uv run bandit -r . && uv run pytest
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov-report=html

# Run specific test file
uv run pytest tests/test_specific.py -v

# Run specific test function
uv run pytest tests/test_specific.py::test_function_name -v

# Run backend tests only
uv run pytest backend/tests/ -v

# Run backend tests with coverage
uv run pytest backend/tests/ --cov=backend.app --cov-report=html

# Run client e2e tests (requires backend server running)
uv run pytest client/tests/e2e/ -v
```

### Playground (Local) - Local Bot Testing
```bash
# Run tournament with all available bots (with visualization)
uv run python main.py tournament

# Run tournament without visualization (headless mode - faster)
uv run python main.py tournament --headless

# List all available bots
uv run python main.py match list

# Run specific match between two bots
uv run python main.py match "Bot1 Name" "Bot2 Name"

# Run multiple matches with win statistics
uv run python main.py match "Bot1 Name" "Bot2 Name" --count 10

# Show detailed match logs
uv run python main.py match "Bot1 Name" "Bot2 Name" --verbose
```

### Backend Server (for PvC and PvP Modes)
```bash
# Start development server with hot reload (from project root)
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (no reload)
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
# Health check at http://localhost:8000/health
```

### Database Management
```bash
# Database is created automatically in data/playground.db

# Remove database (will be recreated on next server start)
rm data/playground.db

# Create database tables manually (if needed)
uv run python -c "import asyncio; from backend.app.core.database import create_tables; asyncio.run(create_tables())"
```

### Client Tools (PvC and PvP Modes)
```bash
# SSE Client - Stream events from an existing session
uv run python -m client.sse_client_main \
  --base-url http://localhost:8000 \
  --session-id <SESSION_ID> \
  --max-events 10

# PvC Mode - Play against server builtin bot (random strategy)
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_1 \
  --bot-type random

# PvC Mode - Play against builtin bot with custom bot
uv run python -m client.bot_client_main \
  --player-id myusername \
  --opponent-id builtin_sample_1 \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1

# PvP Mode - Join matchmaking queue with random bot
uv run python -m client.bot_client_main --mode lobby

# PvP Mode - Join matchmaking queue with custom bot
uv run python -m client.bot_client_main \
  --mode lobby \
  --player-id myusername \
  --bot-type custom \
  --bot-path bots.sample_bot1.sample_bot_1.SampleBot1

# Quick start (uses OS username, default random bot, vs builtin_sample_1)
uv run python -m client.bot_client_main

# Note: Bot clients automatically handle event streaming and action submission
```

## Architecture Overview

### Game Engine Architecture
- **Game Core**: `game/` - Core game logic, rules, and engine
  - `engine.py` - Main game simulation engine
  - `rules.py` - Game constants and spell definitions
  - `wizard.py`, `minion.py` - Game entity classes
  - `logger.py` - Match logging and replay system

- **Simulator**: `simulator/` - Match execution and visualization
  - `match.py` - Match runner
  - `visualizer.py` - Pygame-based game visualization

- **Bot Framework**: `bots/` - Bot development framework
  - `bot_interface.py` - Abstract base class defining bot contract
  - Each bot in its own subdirectory with `decide(state)` implementation

### Backend Architecture (FastAPI)
- **API Layer**: `backend/app/api/` - REST endpoints and route handlers
  - `sessions.py` - Session creation and management endpoints
  - `players.py` - Player registration and info endpoints
  - `actions.py` - Action submission endpoints
  - `streaming.py` - SSE event streaming endpoints
  - `replay.py` - Match replay endpoints
- **Core**: `backend/app/core/` - Configuration, database setup, error handling
  - `config.py` - Environment-based settings
  - `database.py` - SQLModel async database setup
  - `state.py` - Application state management
- **Models**: `backend/app/models/` - Pydantic and SQLModel data models
  - `players.py`, `sessions.py`, `events.py`, `actions.py`, `results.py`
- **Services**: `backend/app/services/` - Business logic and game orchestration
  - `session_manager.py` - Core session lifecycle and game loop
  - `game_adapter.py` - Adapter between backend and game engine
  - `turn_processor.py` - Turn-based action processing
  - `player_registry.py` - Player management and validation
  - `builtin_bots.py` - Built-in bot implementations
  - `sse_manager.py` - Server-Sent Events management
  - `match_logger.py` - Match logging and replay
  - `visualizer_adapter.py` - Integration with Pygame visualizer
- **Database**: SQLite with SQLModel ORM, stored in `data/playground.db`

### Client Architecture
- **SSE Client**: `client/sse_client.py` - Async SSE streaming client for event consumption
- **Bot Client**: `client/bot_client.py` - Bot client simulator for remote gameplay
  - `RandomWalkStrategy` - Built-in random move generator for testing
  - `BotInterfaceAdapter` - Adapter to use local bots with remote backend
- **CLI Tools**: `client/*_main.py` - Command-line interfaces for testing
  - `sse_client_main.py` - Stream events from existing sessions
  - `bot_client_main.py` - Register players and play matches
- **E2E Tests**: `client/tests/e2e/` - End-to-end integration tests with real backend

### Bot Development
Bots must implement `BotInterface` with:
- `name` property - unique bot identifier
- `decide(state: Dict[str, Any])` method - returns `{"move": [x, y], "spell": {...}}`
- Optional sprite paths for custom visualization

Game state includes:
- Turn number and board size
- Self and opponent wizard data (position, HP, mana, cooldowns)
- Artifacts and minions on board
- All information needed for decision making

### Key Design Patterns
- **Bot Discovery**: Automatic bot loading from `bots/` directory using reflection
- **Match Logging**: Complete game state snapshots for replay and analysis
- **Modular Architecture**: Clean separation between game engine, visualization, and backend
- **Adapter Pattern**: `game_adapter.py` bridges backend models with game engine; `visualizer_adapter.py` integrates Pygame visualization with backend
- **Event-Driven Architecture**: SSE streaming for real-time game state updates
- **Modern Python**: Uses UV package manager, Pydantic models, type hints throughout

## Project Structure Notes
- Uses `pyproject.toml` for modern Python packaging
- Ruff for linting/formatting (replaces black, isort, flake8)
- pytest for testing framework
- Pre-commit hooks for code quality
- Legacy `requirements.txt` maintained for compatibility
- Assets in `assets/` for custom bot sprites (optional)

## Environment Configuration

The backend uses environment variables for configuration. Create a `.env` file in the project root:

```env
# Database
PLAYGROUND_DATABASE_URL=sqlite+aiosqlite:///./data/playground.db
PLAYGROUND_DATABASE_ECHO=false

# Server
PLAYGROUND_HOST=0.0.0.0
PLAYGROUND_PORT=8000
PLAYGROUND_RELOAD=true

# Game Settings
PLAYGROUND_TURN_TIMEOUT_SECONDS=5.0
PLAYGROUND_MATCH_LOOP_DELAY_SECONDS=1.0
PLAYGROUND_MAX_TURNS_PER_MATCH=100

# Bot Execution
PLAYGROUND_BOT_EXECUTION_TIMEOUT=1.0
PLAYGROUND_MAX_BOT_MEMORY_MB=100
```

See [backend/README.md](backend/README.md) for full configuration options.

## API Endpoints

When the backend server is running, the following endpoints are available:

### Core Endpoints
- `GET /` - API information and status
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

### Player Management
- `POST /players/register` - Register a new player
  - Request: `{"player_name": "username"}`
- `GET /players/{player_id}` - Get player information

### Session Management

**PvC Mode (Player vs Computer)**:
- `POST /playground/start` - Start a game session against builtin bot
  - Accepts `PlayerConfig` for both players
  - Specify builtin opponent via `bot_type: "builtin"` and `bot_id`
  - Returns `session_id` for the created session
  - Optional `visualize` parameter to enable Pygame visualization

**PvP Mode (Player vs Player)**:
- `POST /playground/lobby/join` - Join matchmaking queue
  - Auto-matches with another waiting player (FIFO)
  - Long-polling (up to 5 minutes timeout)
  - Returns `session_id` when matched

### Game Actions
- `POST /playground/{session_id}/action` - Submit an action for current turn
  - Requires `player_id`, `turn`, `move`, and optional `spell`
  - Must match current turn number

### Event Streaming
- `GET /playground/{session_id}/events` - SSE stream of game events
  - Real-time turn events, game state updates, and game over notifications
  - Automatic reconnection support

### Match Replay
- `GET /playground/{session_id}/replay` - Get complete match history and replay data
  - Includes all turns, actions, and final results

### Admin
- `GET /admin/players` - List all registered players (admin only)

## Troubleshooting

### Port already in use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uv run uvicorn backend.app.main:app --reload --port 8001
```

### Database issues
```bash
# Remove and recreate database
rm data/playground.db

# Database will be recreated automatically on next server start
```

### Import errors
```bash
# Ensure you're in project root
pwd  # Should end with 'swex-camp-spellcaster'

# Reinstall dependencies
uv sync --all-extras
```

## CI/CD

The project includes GitHub Actions workflows in `.github/workflows/`:
- `ci.yml` - Runs linting, security scans, tests, and builds on push/PR
- `claude.yml` - Claude PR Assistant workflow
- `claude-code-review.yml` - Claude Code Review workflow