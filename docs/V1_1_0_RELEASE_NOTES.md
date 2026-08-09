# v1.1.0 Release Notes

`ds-workspace-mcp` `v1.1.0` is a minor release that expands the stable analytical MCP surface with safer SQL execution, richer dataset support, stronger modeling diagnostics, report persistence improvements, and reproducible evaluation metadata.

## Highlights

- hardens DuckDB and SQLite execution with stricter read-only controls, relation allowlisting, and timeout handling
- adds generalized dataset support for Parquet, JSON, Excel, schema diffing, drift diagnostics, and safe group-by aggregation
- improves profiling with bounded distribution, categorical quality, duplicate-row, key-candidate, identifier, and free-text diagnostics
- upgrades modeling readiness with leakage evidence, executable validation guidance, statistically valid dummy baselines, and transparent forecast baselines
- adds reproducible evaluation manifests to experiment plans, modeling reports, dummy baselines, and forecast baselines
- makes report storage transactional with overwrite controls, content hashes, search, compare, copy, rename, delete, section extraction, and Docker persistence
- refactors server composition into a FastMCP application factory with domain-specific MCP registrations

## Compatibility

This release adds MCP tools, CLI commands, and structured response fields in line with the documented minor-release compatibility policy. Existing public names remain supported.

## Known Limitations

- analytical guidance remains heuristic and should be reviewed before operational decisions
- forecast baselines initially require regular inferred frequencies
- SQL timeout enforcement is best-effort interruption and still relies on configured operational bounds
- HTTP authentication remains a shared-token layer rather than scoped identity

## Validation Summary

Validated with:

- `poetry run ruff format --check src tests examples`
- `poetry run ruff check .`
- `poetry run mypy .`
- `poetry run pytest`
- `poetry build`
