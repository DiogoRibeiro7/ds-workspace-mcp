# Roadmap

## v0.1 — Minimal useful MCP server

- [x] Safe CSV discovery.
- [x] CSV preview tool.
- [x] CSV profiling tool.
- [x] Data-quality issue detection.
- [x] Dataset analysis prompt.
- [x] Tests for core safety logic.
- [x] Dockerfile.

## v0.2 — Better analytical workspace

- [x] Add DuckDB support.
- [x] Add SQLite support.
- [x] Add a safe SQL query tool with mandatory row limits.
- [x] Add dataset-level metadata cache.
- [x] Add column summaries for numeric, categorical, and datetime variables.
- [x] Add correlation summaries for numeric columns.

## v0.3 — ML-oriented tools

- [x] Add target leakage checks.
- [x] Add baseline model evaluation tools.
- [x] Add time-series frequency detection.
- [x] Add forecasting dataset validation.
- [x] Add notebook-based walkthroughs.

## v0.4 — Production polish

- [x] Add GitHub Actions CI.
- [x] Add structured logging.
- [x] Add configuration validation.
- [x] Add OpenTelemetry hooks.
- [x] Add authentication support for HTTP deployment.
- [x] Add deployment example with Docker Compose.

## v0.5 — Project polish

- [x] Add synthetic healthcare dataset generation.
- [x] Add local workflow CLI.
- [x] Add MCP client examples.
- [x] Add release artifact and GitHub-tag workflow.

## v1.0 — Stable release

- [x] Document the public API contract.
- [x] Add end-to-end transport coverage for stdio, HTTP, and HTTP auth.
- [x] Add security, deployment, and architecture docs.
- [x] Add dataset, SQL length, and SQL timeout guardrails.
- [x] Prepare `1.0.0` release metadata and notes.

## v1.1 — Hardening and reliability

- [x] Enforce query timeouts and cancellation for DuckDB and SQLite execution.
- [x] Replace the regex SQL blocklist with DuckDB read-only/sandbox configuration as the primary control, keeping pattern checks as defense in depth.
- [x] Add explicit baseline validation split strategies for random, stratified, chronological, and grouped holdouts.
- [x] Reject classification baseline splits that cannot represent every class in train and test data.
- [x] Replace modal-delta time-series frequency inference with structured regular, approximate, irregular, and heterogeneous outcomes.
- [x] Separate leakage evidence from feature exclusion decisions for high correlation and target-name overlap.
- [x] Make Docker builds lockfile-driven and persist report storage through Compose.
- [x] Make report save, copy, and rename operations transactional with explicit overwrite semantics.
- [x] Create isolated FastMCP server instances through a public application factory.
- [x] Split MCP resource, tool, and prompt registrations into domain modules.
- [ ] Cache DuckDB query results by file fingerprint and normalized SQL, mirroring the profile cache.
- [ ] Add explicit handling and tests for malformed, empty, and mixed-encoding CSV edge cases.
- [ ] Surface per-tool resource limits (rows, columns, bytes) in error messages consistently.

## v1.2 — Broader data access

- [x] Support Parquet datasets through the existing safe data-root checks.
- [x] Support Excel (`.xlsx`) and JSON datasets for preview and profiling.
- [x] Add a safe `group_by` aggregation tool so assistants avoid hand-writing SQL.
- [ ] Add a bounded query-result export tool that writes a new CSV back into the data directory.
- [x] Add a dataset comparison / schema-diff tool for column and dtype drift.

## v1.3 — Richer analytics

- [ ] Add numeric histograms and binning to profiling output.
- [ ] Add outlier detection (IQR and z-score) and constant/near-constant column flags.
- [ ] Add duplicate-row detection and key-candidate suggestions.
- [ ] Add time-series resampling and missing-interval fill suggestions.
- [ ] Add a seasonal-naive forecast baseline alongside the existing validator.

## v2.0 — Workspace and extensibility

- [ ] Support multiple configured data roots with per-root access policies.
- [ ] Add optional write-mode workflows behind explicit, audited opt-in.
- [ ] Add a pluggable tool-registration system for third-party analytical tools.
- [ ] Add per-client/session rate limiting for HTTP deployments.
- [ ] Evaluate richer auth (scoped tokens or OAuth) beyond the shared bearer secret.
