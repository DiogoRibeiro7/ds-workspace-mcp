# Security Policy

## Reporting

If you discover a security issue in this repository, do not open a public GitHub issue with exploit details.

Report it privately to the maintainer first and include:

- affected version or commit
- reproduction steps
- expected impact
- any suggested mitigation

## Scope

The highest priority issues are:

- path traversal around dataset resolution
- unsafe SQL execution in DuckDB or SQLite tools
- accidental exposure of local file-system data outside `MCP_DATA_ROOT`
- authentication or transport issues if HTTP protection is later enabled

## Hardening Expectations

- All read paths must stay inside the configured data root.
- SQL tools must remain read-only and bounded.
- User-facing errors should avoid leaking unnecessary local path details.
