# Contributing

## Setup

```bash
poetry install
```

## Development Workflow

Run the local quality gate before opening a pull request:

```bash
poetry run ruff check .
poetry run ruff format --check src tests examples
poetry run mypy
poetry run pytest -m "not integration"
```

If `make` is available, `make quality` runs the same default gate.

Run integration coverage before release or when changing transports, example clients, server startup, or MCP protocol behavior:

```bash
poetry run pytest -m integration tests/integration tests/test_examples.py -vv
```

You can also use the local CLI:

```bash
poetry run ds-workspace-mcp list-datasets
poetry run ds-workspace-mcp profile-dataset sample_clinic_usage.csv
```

## Scope Rules

- Keep file access constrained to `MCP_DATA_ROOT`.
- Put pure data logic in focused modules rather than `server.py`.
- Keep MCP adapter code thin.
- Add tests for every new helper or feature path.
- Prefer structured Pydantic outputs for public tool results.

## Pull Requests

- Keep changes scoped to one feature or one cleanup theme.
- Update `README.md` when user-facing behavior changes.
- Update `ROADMAP.md` or `CHANGELOG.md` when milestone status changes.
- Include test coverage for new features and validation failures.
- Use the pull request template checklist to record which quality gates were run.
