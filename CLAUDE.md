# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
```

### Running the Game
```bash
# Run tournament with all bots
uv run python main.py tournament

# Run tournament without visualization (headless)
uv run python main.py tournament --headless

# List available bots
uv run python main.py match list

# Run specific match between two bots
uv run python main.py match <bot1> <bot2>

# Run multiple matches with stats
uv run python main.py match <bot1> <bot2> --count 10

# Legacy tournament runner
python playground.py 1
```

### Backend Server
```bash
# Start development server with hot reload (from project root)
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Database Management
```bash
# Database is created automatically in data/playground.db

# Remove database (will be recreated on next server start)
rm data/playground.db

# Create database tables manually (if needed)
uv run python -c "import asyncio; from backend.app.core.database import create_tables; asyncio.run(create_tables())"
```

### Client Tools (SSE and Bot Clients)
```bash
# Connect to an existing session and stream events
uv run python -m client.sse_client_main \
  --base-url http://localhost:8000 \
  --session-id <SESSION_ID> \
  --max-events 10

# Register a player and start a match vs builtin bot
uv run python -m client.bot_client_main \
  --base-url http://localhost:8000 \
  --player-name "CLI Bot" \
  --builtin-bot-id sample_bot_1 \
  --max-events 10
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
- **Core**: `backend/app/core/` - Configuration, database setup, authentication
- **Models**: `backend/app/models/` - SQLModel data models for database
- **Services**: `backend/app/services/` - Business logic and game orchestration
- **Database**: SQLite with SQLModel ORM, stored in `data/playground.db`

### Client Architecture
- **SSE Client**: `client/sse_client.py` - Async SSE streaming client
- **Bot Client**: `client/bot_client.py` - Bot client simulator for remote gameplay
- **CLI Tools**: `client/*_main.py` - Command-line interfaces for testing
- **E2E Tests**: `client/tests/e2e/` - End-to-end integration tests

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

# Server
PLAYGROUND_HOST=0.0.0.0
PLAYGROUND_PORT=8000

# Game Settings
PLAYGROUND_TURN_TIMEOUT_SECONDS=5.0
PLAYGROUND_MAX_TURNS_PER_MATCH=100
```

See [backend/README.md](backend/README.md) for full configuration options.

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