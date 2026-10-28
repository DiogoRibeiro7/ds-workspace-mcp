# v1.1.1 Release Notes

`ds-workspace-mcp` `v1.1.1` is a packaging and release-automation patch on top of `v1.1.0`.
No MCP tools, CLI commands, runtime dependencies, or API contracts changed.

## Changes

- Adds automatic PyPI publishing from version-tagged GitHub Actions releases using
  OIDC Trusted Publishing, without persistent PyPI API tokens.
- Validates that the Git release tag matches the version in `pyproject.toml`.
- Documents PyPI publisher registration and release verification.

## Compatibility

All public functionality and Python support remain unchanged from `v1.1.0`.
