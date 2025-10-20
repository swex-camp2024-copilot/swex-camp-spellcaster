# Spellcasters Backend Server

FastAPI-based backend server for **PvC** (Player vs Computer) and **PvP** (Player vs Player) remote play modes. This server enables real-time turn-based bot battles with SSE streaming, player registration, matchmaking, and comprehensive match logging.

> **Note**: For game mode terminology and local testing, see the [Main README](../README.md).
> - **Playground (Local)**: No server needed - use `main.py` for local bot testing
> - **PvC Mode**: Remote play against server's builtin bots (this server required)
> - **PvP Mode**: Auto-matchmaking between players (this server required)
> - **Tournament Mode**: Coming soon for hackathon finale

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- [UV package manager](https://github.com/astral-sh/uv) installed
- Project dependencies installed: `uv sync` (from project root)

### Start the FastAPI Server

From the **project root directory** (not from `/backend`):

```bash
# Make sure dependencies are installed
uv sync

# Start the development server with hot reload
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Or start without reload for production-like testing
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

The server will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Alternative: Run from Backend Directory

If you prefer to run from the `/backend` directory:

```bash
cd backend

# Start with module path
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Development Commands

### Run Tests
```bash
# From project root
uv run python -m pytest backend/tests/ -v

# From backend directory
cd backend
uv run python -m pytest tests/ -v

# Run tests with coverage
uv run python -m pytest tests/ --cov=app --cov-report=html
```

### Database Operations
```bash
# Test database table creation
cd backend
uv run python -c "import asyncio; from app.core.database import create_tables; asyncio.run(create_tables())"

# Check database file (created automatically)
ls -la data/playground.db
```

### Code Quality

For general development commands (linting, formatting, security scans), see the [Main README](../README.md#development-tools).

Backend-specific quality checks:
```bash
# From project root - check only backend code
uv run ruff check backend/
uv run ruff format backend/
uv run bandit -r backend/
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI application entry point
│   ├── core/             # Core configuration and database
│   │   ├── config.py     # Settings management
│   │   ├── database.py   # SQLModel database setup
│   │   └── exceptions.py # Custom exception classes
│   ├── models/           # Pydantic and SQLModel data models
│   │   ├── players.py    # Player-related models
│   │   ├── sessions.py   # Session and game state models
│   │   ├── events.py     # SSE event models
│   │   ├── actions.py    # Action and move models
│   │   ├── results.py    # Game result models
│   │   ├── database.py   # SQLModel database tables
│   │   └── errors.py     # Error response models
│   ├── api/              # API endpoints (to be implemented)
│   ├── services/         # Business logic services (to be implemented)
│   └── utils/            # Utility functions
├── tests/                # Unit and integration tests
│   ├── conftest.py       # Test configuration and fixtures
│   └── test_models.py    # Comprehensive model tests
├── client/               # SSE and bot clients (to be implemented)
├── logs/                 # Match and system logs
│   └── playground/       # Match-specific logs
└── data/
    └── playground.db     # SQLite database (created automatically)
```

## 🔧 Configuration

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

## 🔍 API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation.

### Available Endpoints
- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

### Available Endpoints
- `POST /players/register` - Register a new player
- `GET /players/{player_id}` - Get player information
- `POST /playground/start` - Start a game session (PvC mode - specify builtin opponent)
- `POST /playground/lobby/join` - Join matchmaking queue (PvP mode - auto-match with another player)
- `GET /playground/{session_id}/events` - SSE event stream (real-time game updates)
- `POST /playground/{session_id}/action` - Submit player action for current turn
- `GET /playground/{session_id}/replay` - Get complete match replay data
- `GET /admin/players` - List all registered players (admin only)

## 📝 Testing

The backend includes comprehensive tests covering all data models:

```bash
# Run all tests
uv run python -m pytest backend/tests/ -v

# Run specific test file
uv run python -m pytest backend/tests/test_models.py -v

# Run with coverage report
uv run python -m pytest backend/tests/ --cov=backend.app --cov-report=html

# View coverage report
open backend/htmlcov/index.html
```
