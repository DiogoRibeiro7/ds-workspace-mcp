# Release Checklist

## Pre-release

- [ ] Review `README.md` for accuracy.
- [ ] Review `ROADMAP.md` milestone status.
- [ ] Update `CHANGELOG.md`.
- [ ] Confirm package version in `pyproject.toml` and `src/ds_workspace_mcp/__init__.py`.
- [ ] Review new tools, resources, prompts, and CLI commands for naming consistency.

## Validation

- [x] Run `poetry run ruff check .`
- [x] Run `poetry run mypy`
- [x] Run `poetry run pytest`
- [ ] Run `poetry build`
- [ ] Smoke-test the stdio example.
- [ ] Smoke-test the HTTP example against a local server session.

## Packaging

- [ ] Confirm license, contribution, and security docs are present.
- [ ] Confirm console scripts work as documented.
- [ ] Confirm example files and sample data are included in the repository.

## Release Notes

- [ ] Summarize major user-facing additions.
- [ ] Call out known limitations and heuristic features.
