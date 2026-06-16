# Release Checklist

## Pre-release

- [x] Review `README.md` for accuracy.
- [x] Review `ROADMAP.md` milestone status.
- [x] Update `CHANGELOG.md`.
- [x] Confirm package version in `pyproject.toml` and `src/ds_workspace_mcp/__init__.py`.
- [x] Review new tools, resources, prompts, and CLI commands for naming consistency.

## Validation

- [x] Run `poetry run ruff check .`
- [x] Run `poetry run mypy`
- [x] Run `poetry run pytest`
- [x] Run `poetry build`
- [x] Smoke-test the stdio example.
- [x] Smoke-test the HTTP example against a local server session.

## Packaging

- [x] Confirm license, contribution, and security docs are present.
- [x] Confirm console scripts work as documented.
- [x] Confirm example files and sample data are included in the repository.
- [x] Confirm `.github/workflows/release.yml` matches the intended release process.
- [x] Confirm the release workflow builds artifacts and matches the GitHub-tag-based release process.

## Release Notes

- [x] Summarize major user-facing additions.
- [x] Call out known limitations and heuristic features.
