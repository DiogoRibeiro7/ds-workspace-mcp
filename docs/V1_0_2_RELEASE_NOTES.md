# v1.0.2 Release Notes

`ds-workspace-mcp` `v1.0.2` is a repository-quality patch release on top of the stable `1.0.x` MCP server surface.

## Highlights

- adds GitHub and Zenodo citation metadata
- adds GitHub issue templates, a pull request template, and Dependabot configuration
- adds a Makefile for repeatable local development, quality, test, build, and cleanup commands
- adds editor and Git attributes for consistent formatting and line endings
- documents the default quality gate in the README and contributor guide
- migrates packaging metadata to PEP 621 `[project]` fields

## Compatibility

This release does not intentionally change MCP tools, resources, prompts, CLI commands, or documented environment variables.

## Dependency Maintenance

This release includes the merged Dependabot lockfile updates available on `main` before the release was prepared.

## Validation Summary

Validated with:

- `poetry check`
- `poetry run ruff check .`
- `poetry run ruff format --check src tests examples`
- `poetry run mypy`
- `poetry run pytest -m "not integration"`
- `poetry run pytest -m integration tests/integration tests/test_examples.py -vv`
- `poetry build`
