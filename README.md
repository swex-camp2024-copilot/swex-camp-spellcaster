# 🧙 Spellcasters

**Spellcasters** is a hackathon game challenge where participants program bots to battle in a turn-based, wizard-themed strategy arena. Each bot controls a wizard who can move, cast spells, summon minions, and collect artifacts — all on a 10x10 battlefield.

This repo includes:
- A full game engine
- Bot development framework
- Visualizer with animations (using Pygame)
- Sample smart bots
- Backend server for remote play
- Client tools for networked battles

---

## 🎮 Game Modes

Spellcasters supports four play modes, from simple local testing to multi-player tournaments:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Playground (Local)** | Test bots locally using `main.py` - no server required | Bot development and quick testing |
| **PvC (Client ↔ Server)** | Play against server's builtin bots remotely | Test your bot against standard opponents |
| **PvP (2 Clients ↔ Server)** | Auto-matchmaking between two players' custom bots | Challenge other players |
| **Tournament (Future)** | Multi-client tournament (4/6/16 players) | Hackathon finale competition |

---

## 🎮 How It Works

Each wizard-bot competes by:
- Moving across a grid (like a chess king)
- Casting spells (fireball, shield, teleport, etc.)
- Summoning minions
- Collecting artifacts for health, mana, or cooldown boosts

Bots receive structured game state input each turn and return an action (move + optional spell).

---

## 🚀 Quick Start: Playground (Local)

Get started quickly by testing bots locally - no server setup required!

### Prerequisites

- Python 3.9 or higher
- [UV package manager](https://github.com/astral-sh/uv)

### 1. Install UV (if not already installed)

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### 2. Install Dependencies

```bash
# Install production dependencies
uv sync

# Or install with development tools (recommended for contributors)
uv sync --all-extras

# Setup git hooks (recommended for contributors)
uv run pre-commit install
```

### 3. Test Specific Bots

```bash
# List all available bots
uv run python main.py match list

# Run match between two specific bots
uv run python main.py match "Bot1 Name" "Bot2 Name"

# Run multiple matches and see win statistics
uv run python main.py match "Bot1 Name" "Bot2 Name" --count 10
```

---

## 🌐 Remote Play Modes

Ready to test your bot against others remotely?

### PvC & PvP Modes (Client ↔ Server)

For remote play against server builtin bots (PvC) or other players (PvP), see the [Client README](client/README.md) for detailed instructions on:
- Connecting to the server
- Playing against builtin bots (PvC mode)
- Matchmaking with other players (PvP mode)
- Bot client setup and configuration

### Backend Server Setup

To host your own server for PvC and PvP matches, see the [Backend README](backend/README.md) for:
- Server installation and configuration
- API endpoints documentation
- Database management
- Troubleshooting

---

## 🛠️ Development Tools

This project uses modern Python development tools for code quality and consistency:

### Package Management
- **UV**: Fast Python package manager and resolver
- **pyproject.toml**: Modern Python project configuration

### Code Quality Tools
- **Ruff**: Fast Python linter and formatter (replaces flake8, black, isort)
- **Bandit**: Security vulnerability scanner
- **pytest**: Testing framework with coverage reporting
- **pre-commit**: Git hooks for code quality

### Build Commands

All development tasks can be run using UV commands:
```bash
# Development setup
uv sync --all-extras                    # Install all dependencies
uv run pre-commit install               # Setup git hooks

# Code quality
uv run ruff check .                     # Lint code
uv run ruff format .                    # Format code
uv run ruff format --check .            # Check formatting
uv run bandit -r .                      # Security scan
uv run pytest                          # Run tests
uv run pytest --cov-report=html        # Generate coverage report

# Pre-commit hooks
uv run pre-commit run --all-files       # Run all hooks

# Build and clean
uv build                               # Build package
rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ .ruff_cache/

# Run the game
uv run python main.py match list               # List available bots
uv run python main.py match <bot1> <bot2>      # Run specific match

# Convenience aliases for common workflows
uv run ruff check . && uv run ruff format --check . && uv run bandit -r . && uv run pytest  # Run all checks
```

### CI/CD Pipeline

The project includes a comprehensive GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every push and pull request:

1. **Linting**: Ruff checks for code style and potential issues
2. **Security**: Bandit scans for security vulnerabilities  
3. **Testing**: pytest runs tests across Python 3.9-3.12
4. **Building**: Package build verification

---

## ✍️ Creating Your Own Bot

### Bot Interface

Each bot must implement `BotInterface` with a `decide(state)` method that returns an action dict:

```python
from bots.bot_interface import BotInterface

class MyBot(BotInterface):
    @property
    def name(self) -> str:
        return "My Bot"

    def decide(self, state: dict) -> dict:
        # Analyze game state and return action
        return {
            "move": [dx, dy],      # Movement: -1, 0, or 1 for each axis
            "spell": {             # Optional spell
                "name": "fireball",
                "target": (x, y)
            }
        }
```

### Game State

The `state` dictionary provides everything your bot needs:
- `turn` - Current turn number
- `board_size` - Board dimensions (default 10x10)
- `self` - Your wizard's status (position, HP, mana, cooldowns)
- `opponent` - Opponent wizard's status
- `artifacts` - Available power-ups on the board
- `minions` - Active minions from both sides

### Action Format

**Move**: Array of two integers `[dx, dy]` where each is -1, 0, or 1
- Example: `[1, 0]` moves right, `[0, -1]` moves up

**Spell** (optional): Object with `name` and optional `target`
```python
# Spells requiring target (position tuple)
{"name": "fireball", "target": (5, 5)}
{"name": "teleport", "target": (3, 7)}
{"name": "summon_minion", "target": (4, 4)}

# Spells without target
{"name": "shield"}
{"name": "heal"}
```

Spell names are defined in [game/rules.py](game/rules.py).

### Bot Location

Create your bot in `bots/your_bot_name/` directory:
```
bots/
├── your_bot_name/
│   ├── __init__.py
│   └── your_bot.py       # Your BotInterface implementation
```

The bot will be automatically discovered and loaded by the tournament system.

### Custom Sprites (Optional)

Add custom wizard/minion sprites in `assets/`:
```
assets/
├── wizards/your_wizard.png
├── minions/your_minion.png
```

Use PNGs with transparent backgrounds. Reference them in your bot class properties.

---

## 🧪 Testing Your Bot

Use the Playground (Local) mode to test your bot:

```bash
# Test against specific opponent
uv run python main.py match "Your Bot" "Sample Bot 1"

# Run 100 matches to analyze win rate
uv run python main.py match "Your Bot" "Sample Bot 1" --count 100
```

For remote testing against other players, see [Client README](client/README.md) for PvP mode.