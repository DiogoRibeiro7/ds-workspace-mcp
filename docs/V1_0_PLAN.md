# v1.0 Plan

## Goal

Ship `v1.0.0` as a stable MCP server for local analytical workflows with explicit compatibility guarantees, deployment guidance, and end-to-end transport coverage.

## Definition of Done

- MCP tool, resource, prompt, CLI, and environment-variable names are treated as a documented public contract.
- The repo has end-to-end tests for `stdio`, Streamable HTTP, and HTTP auth.
- Release packaging, example clients, and Docker Compose have at least one integration-level smoke path.
- Security, deployment, and architecture documentation are complete enough for third-party use.
- `v1.0.0` release notes and checklist are ready to execute without ad hoc steps.

## Milestone 1: Public Contract

- [x] Create `docs/API_CONTRACT.md`.
- [x] Enumerate all public MCP resources, tools, prompts, CLI commands, and environment variables.
- [x] Document stable result-shape expectations and known heuristic outputs.
- [x] Define backward-compatibility rules for patch, minor, and major releases.

Acceptance criteria:
- A new contributor can tell which names and schemas are versioned.
- Breaking API changes require an explicit compatibility note.

## Milestone 2: Integration Reliability

- [x] Scaffold `tests/integration/`.
- [x] Add a `stdio` integration flow test.
- [x] Add a Streamable HTTP integration flow test.
- [x] Add a Streamable HTTP integration test with API-key auth enabled.
- [x] Run the integration suite in CI, or add a dedicated gated workflow for it.
- [x] Add smoke coverage for the example clients.

Acceptance criteria:
- The suite proves that real MCP clients can initialize sessions and call core tools over supported transports.
- Auth-on and auth-off HTTP behavior is covered by transport-level tests.

## Milestone 3: Operational Hardening

- [x] Document the security model in `docs/SECURITY_MODEL.md`.
- [x] Add a deployment guide in `docs/DEPLOYMENT.md`.
- [x] Add an architecture overview in `docs/ARCHITECTURE.md`.
- [x] Define and test behavior for malformed CSVs, large files, and encoding edge cases.
- [x] Evaluate SQL timeout or cancellation behavior for long-running queries.
- [x] Add request and dataset size guardrails where missing.

Acceptance criteria:
- Supported deployment and safety boundaries are explicit.
- Common failure modes are documented and reproducible.

## Milestone 4: Release Execution

- [ ] Update `pyproject.toml` and `src/ds_workspace_mcp/__init__.py` to `1.0.0`.
- [ ] Add `docs/V1_0_0_RELEASE_NOTES.md`.
- [ ] Run full validation: unit tests, integration tests, linting, typing, and build.
- [ ] Tag and publish the `v1.0.0` release.

Acceptance criteria:
- The release can be cut from a documented checklist with no hidden manual steps.
- `v1.0.0` artifacts and notes match the tested repository state.

## Immediate Next Steps

1. Land the initial integration suite.
2. Write `docs/API_CONTRACT.md`.
3. Add CI execution for `tests/integration/`.
4. Add deployment and security model docs.
