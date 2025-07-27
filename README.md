# 🧙 Spellcasters

**Spellcasters** is a hackathon game challenge where participants program bots to battle in a turn-based, wizard-themed strategy arena. Each bot controls a wizard who can move, cast spells, summon minions, and collect artifacts — all on a 10x10 battlefield.

This repo includes:
- A full game engine
- Bot development framework
- Visualizer with animations (using Pygame)
- Sample smart bots

---

## 🎮 How It Works

Each wizard-bot competes by:
- Moving across a grid (like a chess king)
- Casting spells (fireball, shield, teleport, etc.)
- Summoning minions
- Collecting artifacts for health, mana, or cooldown boosts

Bots receive structured game state input each turn and return an action (move + optional spell).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- [UV package manager](https://github.com/astral-sh/uv) (recommended) or pip

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

# Or install with development tools
uv sync --all-extras
```

### 3. Run a Tournament

```bash
# Using UV
uv run python main.py tournament

# Or run without visualization (headless mode)
uv run python main.py tournament --headless

# Using the convenience script (legacy)
python playground.py 1
```

### 4. Development Setup (for contributors)

```bash
# Complete development setup
uv sync --all-extras
uv run pre-commit install
```

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
uv run python main.py tournament                # Run tournament
uv run python main.py tournament --headless    # Run without visualization
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

### Migration from Legacy Setup

If you're migrating from the old pip-based setup:

1. **Install UV**: Follow the installation instructions above
2. **Remove old virtual environment**: `rm -rf venv/` (optional)
3. **Install with UV**: `uv sync --all-extras`
4. **Setup development tools**: `uv run pre-commit install`
5. **Update your workflow**: Use `uv run` instead of direct Python calls

**Legacy files maintained for compatibility:**
- `requirements.txt` - Generated from `requirements.in`, still used by some bots
- `playground.py` - Original tournament runner script
- Virtual environment workflows still work if you prefer them

**New recommended workflow:**
- `pyproject.toml` - Modern Python project configuration
- `uv` commands for dependency management and task execution
- GitHub Actions for CI/CD

---

## 🧠 Bot Interface

To participate in the game, each bot must implement a decide(state) method. This method is called every turn and must return an action dict.
Ask your AI assistant to give you more details.

---

## 📥 State Input Format

The state dictionary includes everything your bot needs to make decisions - your AI assistant can provide you more details on this.

---

## ✍️ Add Your Own Bot

Create a new folder/module in bots/, and implement the required decide(state) logic.
Your main task is to implement how decide method works for your bot. Method needs to return an object like this:
```python
{
    "move": move,
    "spell": spell
}
```
Move must be an array of two integers where one represent your movement on x-axis and another one movement on y-axis. Numbers must be in range from -1 to 1.

Spell format is defined as below:
```python 
{
    "name": spell_name,
    "target": position
}
```
Spell name must be one of the values defined in rules.py. Position is a tuple representing coordinates on the board.

Spells shield and heal do not require target to be provided.

---

## 🤖 Testing Your Bot

You can use the `playground.py` script to test your bot against others:

1. **Run a Single Tournament**:
   ```bash
   python playground.py 1
   ```
   This will run one tournament with all available bots.

2. **Run Multiple Tournaments**:
   ```bash
   python playground.py 100
   ```
   This will run 100 tournaments and calculate win rates for the target bot.

3. **Analyze Bot Performance**:
   The script outputs match results and final win rates, which you can use to analyze and improve your bot's strategy.

---

## 📥 Add Sprites
Place custom assets in assets/:

```
assets/
├── wizards/
├── minions/
```

Use PNGs with transparent backgrounds. Add the path to your sprite using the respective properties in the bot class.
NOTE: It is not necessary to add sprites to play the game - if the custom sprite is not provided then the default one(s) will be used.