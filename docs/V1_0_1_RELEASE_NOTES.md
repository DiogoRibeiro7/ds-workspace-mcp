# v1.0.1 Release Notes

`ds-workspace-mcp` `v1.0.1` is a post-release patch update on top of `v1.0.0`.

## Highlights

- upgrades `pytest` to `9.1.0`
- addresses the open GitHub Dependabot alert for `GHSA-6w46-j5rx-g56g` / `CVE-2025-71176`
- keeps the tested `1.0.x` application surface unchanged

## Why This Release Exists

The `v1.0.0` tag was pushed successfully, but:

- GitHub still reported an open Dependabot alert because the repository lockfile used `pytest 8.4.2`
- the PyPI publish job failed because the repository had no `PYPI_API_TOKEN` secret configured and the fallback trusted-publisher claims did not match a configured PyPI publisher

This patch release fixes the dependency alert in-repo. PyPI publishing still requires repository or PyPI-side configuration before tagging the next release.

## Validation Summary

Validated with:

- `poetry run ruff check .`
- `poetry run mypy`
- `poetry run pytest`
