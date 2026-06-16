# v1.0.1 Release Notes

`ds-workspace-mcp` `v1.0.1` is a post-release patch update on top of `v1.0.0`.

## Highlights

- upgrades `pytest` to `9.1.0`
- addresses the open GitHub Dependabot alert for `GHSA-6w46-j5rx-g56g` / `CVE-2025-71176`
- keeps the tested `1.0.x` application surface unchanged

## Why This Release Exists

The `v1.0.0` tag was pushed successfully, but:

- GitHub still reported an open Dependabot alert because the repository lockfile used `pytest 8.4.2`
- the repository release workflow was still framed around PyPI publishing, which is not part of the core product goals for this repo

This patch release fixes the dependency alert in-repo and aligns the release story back to GitHub-tagged releases and release artifacts.

## Validation Summary

Validated with:

- `poetry run ruff check .`
- `poetry run mypy`
- `poetry run pytest`
