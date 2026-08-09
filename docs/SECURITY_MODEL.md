# Security Model

## Scope

`ds-workspace-mcp` is designed for local analytical workflows and controlled self-hosted deployments. It is not a multi-tenant service and does not implement user accounts, per-user authorization, or durable audit storage.

The primary security goal is to let an MCP client inspect local datasets without granting arbitrary filesystem or SQL execution access.

## Trust Boundaries

### Trusted

- the host machine running the server
- the configured `MCP_DATA_ROOT` directory
- the process environment and `.env` file
- the operator who starts the server

### Partially trusted

- MCP clients and assistants that call the server
- SQL strings submitted to DuckDB and SQLite tools
- dataset files placed inside `MCP_DATA_ROOT`

### Untrusted

- file paths supplied by clients
- malformed CSV content
- bearer tokens presented over HTTP

## Security Controls

### Filesystem isolation

- CSV and SQLite access is rooted under `MCP_DATA_ROOT`.
- dataset and database paths are resolved to absolute paths before use.
- path traversal attempts such as `../secret.csv` are rejected.
- only `.csv` files are accepted for CSV tools.
- only `.sqlite`, `.sqlite3`, and `.db` files are accepted for SQLite tools.

This isolates the MCP surface from arbitrary host files, but it does not protect against sensitive data being placed inside `MCP_DATA_ROOT` itself.

### Read-only SQL execution

DuckDB controls:

- queries must be a single `SELECT` or `WITH` statement
- DuckDB external access is disabled on the in-memory query connection
- DuckDB extension autoload/autoinstall, community extensions, and persistent secrets are disabled
- DuckDB configuration is locked before user SQL executes
- user SQL is parsed and base relation references are allowlisted to the registered in-memory `dataset` relation
- CTEs, aliases, subqueries, joins, quoted identifiers, and window functions are validated structurally rather than by substring checks
- CTEs may not shadow the allowed `dataset` relation
- destructive and schema-changing statements are rejected as defense in depth
- external file and scan functions such as `read_csv`, `read_parquet`, `read_json`, `glob`, `sniff_csv`, `query`, and similar helpers are rejected as defense in depth
- a final row limit is always applied
- best-effort query interruption is attempted when execution exceeds `MCP_SQL_TIMEOUT_MS`

SQLite controls:

- databases are opened in read-only mode
- queries must be a single `SELECT` or `WITH` statement
- destructive and schema-changing statements are rejected
- a final row limit is always applied
- a progress-handler timeout interrupts long-running queries after `MCP_SQL_TIMEOUT_MS`

SQLite controls reduce accidental or hostile misuse through application-layer checks and read-only handles. DuckDB uses both engine-level external-access restrictions and application-level structural validation.

### Transport and auth

Supported transports:

- `stdio`
- `streamable-http`

`stdio` has no built-in auth layer because the client already controls local process launch.

`streamable-http` optionally supports a shared bearer token through `MCP_API_KEY`.

Properties of the current HTTP auth model:

- authentication is on or off for the whole server
- there are no user identities or scopes
- tokens are compared using constant-time digest comparison
- the advertised auth metadata points clients at the server resource URL and repository documentation

Limitations:

- no per-user authorization
- no token rotation API
- no rate limiting
- no TLS termination inside the app

If the service is reachable off-host, TLS and secret management must be handled by the deployment layer.

### Error handling and logging

- user-facing errors avoid exposing absolute local filesystem paths where practical
- logs record safe metadata such as dataset names, row limits, and tool names
- logs intentionally do not include full dataset payloads or preview rows
- optional tracing records operational spans but does not add access control

## Threat Model

### Threats mitigated

- path traversal outside `MCP_DATA_ROOT`
- accidental destructive SQL through MCP tools
- direct SQLite writes through server-managed connections
- accidental over-returning of SQL rows beyond configured bounds
- simple unauthorized HTTP access when `MCP_API_KEY` is configured

### Threats not fully mitigated

- malicious data already present inside `MCP_DATA_ROOT`
- denial-of-service from very large datasets or expensive queries
- network interception when HTTP is exposed without TLS
- secret leakage from poor environment handling outside the app
- multi-tenant isolation requirements

## Operational Recommendations

- keep `MCP_DATA_ROOT` narrow and purpose-specific
- do not mount sensitive home directories or broad project roots as the data root
- prefer `stdio` for single-user local workflows
- if using HTTP, bind to `127.0.0.1` unless a reverse proxy is intentionally exposing the service
- if using HTTP beyond localhost, terminate TLS upstream and set `MCP_API_KEY`
- keep logs at `INFO` or higher in shared environments
- review datasets before placing them under `MCP_DATA_ROOT`

## Known Gaps Before v1.0

- no request rate limiting
- no hard guarantee that DuckDB interruption immediately stops all pathological queries
- no content-based scanning for dangerous or unexpected files inside `MCP_DATA_ROOT`

These gaps are operational hardening items rather than hidden behavior.
