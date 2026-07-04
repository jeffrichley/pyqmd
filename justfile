# Recipes for pyqmd development
# Note: lint (ruff check) and typecheck (mypy) are deferred to the strict-debt issue.
# 'check' runs tests + coverage only; lint/typecheck are separate recipes for local use.

# Run tests with coverage
test:
    uv run pytest

# Lint source and tests
lint:
    uv run ruff check src tests

# Format source
format:
    uv run ruff format

# Type check
typecheck:
    uv run mypy src

# Run tests + coverage (CI gate)
# lint and typecheck deferred — see strict-debt tracking issue
check:
    uv run pytest
