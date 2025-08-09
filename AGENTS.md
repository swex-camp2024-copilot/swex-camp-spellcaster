# Spellcasters Agent Guidelines

## Build/Test/Lint Commands
- **Test all**: `pytest`
- **Test single file**: `pytest tests/test_filename.py`
- **Test specific test**: `pytest tests/test_filename.py::test_function_name`
- **Lint/format**: `ruff check` and `ruff format`
- **Security check**: `bandit -r .`
- **Coverage**: `pytest --cov=.`

## Code Style Guidelines
- **Line length**: 120 characters max (configured in pyproject.toml)
- **Imports**: Use absolute imports, grouped by standard library, third-party, local
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Type hints**: Required for all functions using typing module
- **Docstrings**: Google-style format, but not required for all functions (see pyproject.toml ignores)
- **Error handling**: Use custom exceptions, proper try-except blocks
- **Dependencies**: Pydantic for models, FastAPI for backend, SQLModel for DB

## Project Structure
- Backend API in `backend/app/` with models, services, API routes
- Game engine in `game/` directory
- Bot implementations in `bots/` directory
- Tests in `tests/` with pytest framework