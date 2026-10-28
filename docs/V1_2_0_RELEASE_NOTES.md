# v1.2.0 Release Notes

`ds-workspace-mcp` `v1.2.0` extends the local analytical workspace with
configurable DuckDB result caching and an optional, bounded CSV export tool.

## Added

- A thread-safe DuckDB query-result LRU cache keyed by normalized SQL, dataset
  identity, file size, modification time, and the applied result row limit.
  Entries are copied before reuse, and cache size and enablement are configurable.
- `export_query_result_to_csv`, an MCP tool that runs an existing safe DuckDB
  `SELECT` or `WITH` query and writes the bounded result to a new CSV under
  `MCP_DATA_ROOT`. The tool is disabled by default.
- Independent export limits for rows, columns, and encoded output bytes. Files
  are published atomically, and existing files are never overwritten.

## Improved

- CSV parsing now handles UTF-8 BOMs and reports empty, malformed, and mixed-
  encoding inputs explicitly, without silently dropping excess fields.
- Errors identify the relevant row, column, SQL-length, timeout, or byte limit
  configuration setting.
- The public API contract, security model, and deployment documentation now
  cover the optional CSV write boundary and its safeguards.

## Configuration

The following new settings are optional:

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `MCP_QUERY_CACHE_ENABLED` | `true` | Enable DuckDB result caching. |
| `MCP_QUERY_CACHE_MAX_ENTRIES` | `32` | Maximum cached query results. |
| `MCP_QUERY_EXPORT_ENABLED` | `false` | Enable the CSV export tool. |
| `MCP_MAX_EXPORT_ROWS` | `1000` | Maximum rows per exported CSV. |
| `MCP_MAX_EXPORT_COLUMNS` | `100` | Maximum columns per exported CSV. |
| `MCP_MAX_EXPORT_BYTES` | `5000000` | Maximum encoded bytes per export, also bounded by `MCP_MAX_DATASET_BYTES`. |

Existing users do not need to change their configuration. Enable export only
when clients are trusted to create files inside the configured data directory.

## Compatibility and limits

- Python `>=3.11,<3.13` is supported; no new required runtime dependencies.
- The existing MCP tool and result contracts remain compatible. The new export
  tool and configuration fields are additive.
- Cache invalidation uses size and modification time, not content hashing.
  Disable query caching for volatile SQL functions or if queries must always
  be re-executed.
- Export preserves data values, including formula-like strings. Inspect
  untrusted CSV data before opening it in spreadsheet software.

## Installation

After the `v1.2.0` Git tag has been published through PyPI Trusted Publishing:

```bash
python -m pip install --upgrade ds-workspace-mcp==1.2.0
```
