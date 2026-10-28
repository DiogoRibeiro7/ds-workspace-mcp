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

## PyPI Trusted Publishing (one-time setup)

- [ ] Create the GitHub Actions environment `pypi` under repository Settings > Environments.
      Restrict deployments to release tags (for example `v*`) and consider required reviewers.
- [ ] Register the PyPI Trusted Publisher for the project `ds-workspace-mcp`:
      owner `DiogoRibeiro7`, repository `ds-workspace-mcp`,
      workflow `release.yml`, environment `pypi`.
      If the project does not exist on PyPI yet, create a *pending* publisher instead.
- [ ] Confirm the PyPI project name matches `[project].name` in `pyproject.toml`.

## Publishing a version

- [ ] Update the package version in `pyproject.toml` and
      `src/ds_workspace_mcp/__init__.py`, then merge the changes into the intended release commit.
- [ ] Create and push an annotated `vX.Y.Z` tag that matches the package version:
      `git tag -a vX.Y.Z -m "Release vX.Y.Z"` and `git push origin vX.Y.Z`.
- [ ] Confirm both the `build` and `publish` jobs succeed in the GitHub Actions Release workflow.
- [ ] Verify the release appears at https://pypi.org/project/ds-workspace-mcp/ and
      can be installed with `python -m pip install ds-workspace-mcp==X.Y.Z`.

The release workflow publishes only for `v*` tag refs. Manual runs from a branch build
artifacts without publishing. PyPI does not allow overwriting an existing version.
