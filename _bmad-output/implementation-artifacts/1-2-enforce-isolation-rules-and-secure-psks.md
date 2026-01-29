# Story 1.2: Enforce Isolation Rules and Secure PSKs

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an administrator,
I want strict PT/CT traffic isolation with PSKs encrypted at rest,
so that the simulator prevents cross-domain leakage and protects secrets.

## Acceptance Criteria

1. Given the appliance is running with CT/PT/MGMT namespaces, when PT traffic attempts to route directly to CT, then the traffic is blocked and does not reach CT. (FR51)
2. Only IKE (UDP 500/4500) and ESP (protocol 50) traffic is permitted between PT and CT namespaces. (FR52)
3. Pre-shared keys (PSKs) are stored encrypted at rest in the configuration database. (FR55, NFR-S9)

## Tasks / Subtasks

- [x] Implement namespace isolation enforcement (AC: 1, 2)
  - [x] Define nftables rules that deny PT->CT routing by default and allow only IKE/ESP between PT and CT.
  - [x] Place privileged rule application in `backend/daemon/ops` and expose a daemon IPC command for enforcement.
  - [x] Ensure rules are applied for CT/PT namespaces without affecting MGMT traffic.
  - [x] Add startup hook in backend/daemon to apply rules during boot sequence.
- [x] Encrypt PSKs at rest (AC: 3)
  - [x] Add encrypted PSK storage fields to the peer model/schema and database (SQLAlchemy + Alembic migration).
  - [x] Implement application-layer encryption/decryption in `backend/app/services` using a config-provided key.
  - [x] Ensure API never returns raw PSKs; mask or omit as appropriate in responses.
- [x] Testing (AC: 1, 2, 3)
  - [x] Unit tests for PSK encryption/decryption utilities.
  - [x] Integration test validating: PT->CT packets blocked; IKE/ESP allowed (mock or namespace-level test harness).
  - [x] Integration test verifying encrypted PSKs stored in SQLite (no plaintext in DB).

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Replace isolation “integration” test with a real namespace/packet-level test to validate PT->CT blocking and IKE/ESP allow. `backend/tests/integration/test_isolation_rules_integration.py:7`
- [x] [AI-Review][HIGH] Fix PSK key parsing to handle hex keys that are also valid base64; ensure hex fallback is used when appropriate. `backend/app/services/psk_crypto.py:15`
- [x] [AI-Review][MEDIUM] Restrict daemon IPC Unix socket permissions/ownership after bind to prevent untrusted local access. `backend/daemon/ipc/server.py:49`

## Dev Notes

- Isolation enforcement must use nftables; rules live in the privileged daemon (`backend/daemon/ops`) and are invoked via Unix socket IPC from the FastAPI service layer. [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points]
- Namespace model: CT/PT/MGMT are distinct network namespaces; ensure PT->CT direct routing is blocked and only UDP 500/4500 + ESP (proto 50) are allowed between CT and PT. [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Enforce Isolation Rules and Secure PSKs]
- PSK encryption is required at the application layer; SQLite file must be 600 permissions (root-only) and PSKs must not be stored plaintext. [Source: _bmad-output/planning-artifacts/prd.md#Security]
- API response format must use `{ data, meta }`; errors must be RFC 7807. [Source: _bmad-output/project-context.md#Critical Implementation Rules]

### Project Structure Notes

- Privileged ops: `backend/daemon/ops` and IPC boundary in `backend/daemon/ipc`.
- API/service logic: `backend/app/services` and `backend/app/api`.
- DB models/migrations: `backend/app/models`, `backend/app/schemas`, `backend/app/db`, `backend/alembic/versions`.
- Frontend is not expected to be modified for this story unless status display requires it.

## Developer Context

Goal: enforce PT/CT isolation rules via nftables and ensure PSKs are encrypted at rest in SQLite. This story focuses on backend and daemon operations, data modeling, and security enforcement. No UI redesign is required.

In scope:
- nftables isolation rules for CT/PT namespaces
- PSK encryption at rest with application-layer crypto
- DB migration to store encrypted PSKs
- Minimal API/service adjustments to avoid plaintext exposure
- Backend/daemon tests for isolation and encryption

Out of scope:
- Isolation validation UX (Story 1.3)
- Security testing report (Story 1.4)
- New UI workflows for peer management beyond existing CRUD

## Technical Requirements

- Use SQLAlchemy ORM + Alembic for any schema changes; no manual DB edits.
- PSK encryption must be reversible for strongSwan configuration generation; do not hash PSKs.
- Store encryption key in appliance config (`/etc/<app>/config.yaml`) or environment as defined in backend config layer.
- Ensure SQLite file permissions are enforced at 600 (root-only) at runtime.
- Respect API success envelope `{ data, meta }` and RFC 7807 errors.

## Architecture Compliance

- Privileged system changes must go through the daemon boundary (Unix socket IPC).
- API lives under `/api/v1` and uses camelCase JSON fields.
- WebSocket events (if added) must be `{ type, data }` with dot-notation event names.
- Backend folder structure: `api`, `models`, `schemas`, `services`, `repositories`, `db`, `auth`, `ws`, `daemon`.

## Library & Framework Requirements

- Python 3.12 + FastAPI 0.128.0
- SQLAlchemy 2.0.46 + Alembic 1.18.1
- strongSwan 6.0.4 + nftables 1.1.6
- SQLite (default embedded DB)

## File Structure Requirements

- nftables rule logic: `backend/daemon/ops/*`
- IPC command definition: `backend/daemon/ipc/*`
- PSK encryption utilities: `backend/app/services/*`
- DB schema changes: `backend/app/models/*` and `backend/alembic/versions/*`
- Tests: `backend/tests/unit/test_*.py`, `backend/tests/integration/test_*.py`

## Testing Requirements

- Unit tests for encryption utilities (round-trip encrypt/decrypt).
- Integration test: verify PT->CT traffic blocked while IKE/ESP allowed (namespace or mocked nftables).
- Integration test: verify encrypted PSK storage in SQLite (no plaintext).

## Previous Story Intelligence

- Story 1.1 created the repo structure, versions, and base FastAPI app; use the existing directory layout and version pins. [Source: _bmad-output/implementation-artifacts/1-1-initialize-project-from-starter-template.md]

## Latest Tech Information

- Web research not performed (offline). Use the exact versions listed in architecture and project context.

## Project Context Reference

- Use Pydantic models for request/response validation.
- Use SQLAlchemy ORM + Alembic for migrations.
- JSON fields are camelCase; REST paths are plural under `/api/v1`.
- Errors follow RFC 7807.
- React components are `PascalCase.tsx` and avoid default exports.
- WebSocket payloads are `{ type, data }` with dot-notation event names.

## Completion Status

Status: done

Completion note: Code review complete with all HIGH and MEDIUM issues resolved.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2: Enforce Isolation Rules and Secure PSKs]
- [Source: _bmad-output/planning-artifacts/prd.md#Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Debug Log References

create-story workflow (YOLO)

### Completion Notes List

- Story derived from epic 1.2 requirements and architecture constraints.
- Isolation rules and PSK encryption requirements captured with daemon boundary enforcement.
- Tests defined for isolation enforcement and encrypted PSK storage.
- Web research skipped due to offline environment; versions pinned to architecture.
- Implemented nftables isolation rules with daemon IPC command and startup hook.
- Added encrypted PSK storage (SQLAlchemy + Alembic), AES-GCM utilities, and peer service serialization without plaintext.
- Added unit/integration tests for isolation rules and encrypted PSK storage; ensured SQLite permissions set to 600.
- Scoped isolation rules to explicit interface allowlist for PT/CT forwarding and updated tests to assert enforcement.
- Wired PSK encryption key lookup through settings helper and added unit coverage for config-driven key parsing.
- Extended daemon IPC to accept optional interface allowlist for isolation enforcement.
- Ensured isolation rules apply cleanly by creating the nftables table before flushing and reloading rules.
- Added daemon Unix-socket IPC server and app-side client for enforce_isolation commands.
- Strengthened isolation tests to validate table creation flow and exact allow-rule set.
- Implemented namespace-level packet test for PT/CT isolation (UDP 500/4500 allow, UDP 9999 block, ESP allow).
- Prefer hex PSK key decoding when hex/base64 ambiguous; added unit test coverage.
- Restricted daemon IPC socket permissions to 600 and root ownership when available; added unit test.
- Tests run: `APP_PSK_ENCRYPTION_KEY=... .venv/bin/python -m pytest` (12 passed, 2 skipped: netns test requires root; unix socket bind restricted in environment).
- ✅ Resolved review finding [HIGH]: Replace isolation integration test with namespace/packet-level validation.
- ✅ Resolved review finding [HIGH]: Prefer hex PSK key decoding when ambiguous.
- ✅ Resolved review finding [MEDIUM]: Restrict daemon IPC Unix socket permissions/ownership after bind.
- ✅ Code review (2026-01-25): Fixed 1 HIGH + 6 MEDIUM issues:
  - [HIGH] Staged untracked IPC implementation files (daemon_ipc.py, server.py, tests)
  - [MEDIUM] Added connection timeout (5s) to IPC server to prevent DoS
  - [MEDIUM] Added graceful shutdown via SIGTERM/SIGINT signal handlers
  - [MEDIUM] Added exception logging to daemon IPC request handler
  - [MEDIUM] Fixed IPC client to read full response with loop (not just 4096 bytes)
  - [MEDIUM] Cached parsed PSK key with lru_cache to avoid re-parsing
  - [MEDIUM] Added pre-flight check for required commands (ip, nft)

### File List

- .claude/commands/bmad/bmm/agents/analyst.md
- .claude/commands/bmad/bmm/agents/architect.md
- .claude/commands/bmad/bmm/agents/dev.md
- .claude/commands/bmad/bmm/agents/pm.md
- .claude/commands/bmad/bmm/agents/quick-flow-solo-dev.md
- .claude/commands/bmad/bmm/agents/sm.md
- .claude/commands/bmad/bmm/agents/tea.md
- .claude/commands/bmad/bmm/agents/tech-writer.md
- .claude/commands/bmad/bmm/agents/ux-designer.md
- .claude/commands/bmad/bmm/workflows/check-implementation-readiness.md
- .claude/commands/bmad/bmm/workflows/code-review.md
- .claude/commands/bmad/bmm/workflows/correct-course.md
- .claude/commands/bmad/bmm/workflows/create-architecture.md
- .claude/commands/bmad/bmm/workflows/create-epics-and-stories.md
- .claude/commands/bmad/bmm/workflows/create-excalidraw-dataflow.md
- .claude/commands/bmad/bmm/workflows/create-excalidraw-diagram.md
- .claude/commands/bmad/bmm/workflows/create-excalidraw-flowchart.md
- .claude/commands/bmad/bmm/workflows/create-excalidraw-wireframe.md
- .claude/commands/bmad/bmm/workflows/create-product-brief.md
- .claude/commands/bmad/bmm/workflows/create-story.md
- .claude/commands/bmad/bmm/workflows/create-ux-design.md
- .claude/commands/bmad/bmm/workflows/dev-story.md
- .claude/commands/bmad/bmm/workflows/document-project.md
- .claude/commands/bmad/bmm/workflows/generate-project-context.md
- .claude/commands/bmad/bmm/workflows/prd.md
- .claude/commands/bmad/bmm/workflows/quick-dev.md
- .claude/commands/bmad/bmm/workflows/quick-spec.md
- .claude/commands/bmad/bmm/workflows/research.md
- .claude/commands/bmad/bmm/workflows/retrospective.md
- .claude/commands/bmad/bmm/workflows/sprint-planning.md
- .claude/commands/bmad/bmm/workflows/sprint-status.md
- .claude/commands/bmad/bmm/workflows/testarch-atdd.md
- .claude/commands/bmad/bmm/workflows/testarch-automate.md
- .claude/commands/bmad/bmm/workflows/testarch-ci.md
- .claude/commands/bmad/bmm/workflows/testarch-framework.md
- .claude/commands/bmad/bmm/workflows/testarch-nfr.md
- .claude/commands/bmad/bmm/workflows/testarch-test-design.md
- .claude/commands/bmad/bmm/workflows/testarch-test-review.md
- .claude/commands/bmad/bmm/workflows/testarch-trace.md
- .claude/commands/bmad/bmm/workflows/workflow-init.md
- .claude/commands/bmad/bmm/workflows/workflow-status.md
- .claude/commands/bmad/core/agents/bmad-master.md
- .claude/commands/bmad/core/tasks/index-docs.md
- .claude/commands/bmad/core/tasks/shard-doc.md
- .claude/commands/bmad/core/workflows/brainstorming.md
- .claude/commands/bmad/core/workflows/party-mode.md
- .codex/prompts/bmad-bmm-agents-analyst.md
- .codex/prompts/bmad-bmm-agents-architect.md
- .codex/prompts/bmad-bmm-agents-dev.md
- .codex/prompts/bmad-bmm-agents-pm.md
- .codex/prompts/bmad-bmm-agents-quick-flow-solo-dev.md
- .codex/prompts/bmad-bmm-agents-sm.md
- .codex/prompts/bmad-bmm-agents-tea.md
- .codex/prompts/bmad-bmm-agents-tech-writer.md
- .codex/prompts/bmad-bmm-agents-ux-designer.md
- .codex/prompts/bmad-bmm-workflows-README.md
- .codex/prompts/bmad-bmm-workflows-check-implementation-readiness.md
- .codex/prompts/bmad-bmm-workflows-code-review.md
- .codex/prompts/bmad-bmm-workflows-correct-course.md
- .codex/prompts/bmad-bmm-workflows-create-architecture.md
- .codex/prompts/bmad-bmm-workflows-create-epics-and-stories.md
- .codex/prompts/bmad-bmm-workflows-create-excalidraw-dataflow.md
- .codex/prompts/bmad-bmm-workflows-create-excalidraw-diagram.md
- .codex/prompts/bmad-bmm-workflows-create-excalidraw-flowchart.md
- .codex/prompts/bmad-bmm-workflows-create-excalidraw-wireframe.md
- .codex/prompts/bmad-bmm-workflows-create-product-brief.md
- .codex/prompts/bmad-bmm-workflows-create-story.md
- .codex/prompts/bmad-bmm-workflows-create-ux-design.md
- .codex/prompts/bmad-bmm-workflows-dev-story.md
- .codex/prompts/bmad-bmm-workflows-document-project.md
- .codex/prompts/bmad-bmm-workflows-generate-project-context.md
- .codex/prompts/bmad-bmm-workflows-prd.md
- .codex/prompts/bmad-bmm-workflows-quick-dev.md
- .codex/prompts/bmad-bmm-workflows-quick-spec.md
- .codex/prompts/bmad-bmm-workflows-research.md
- .codex/prompts/bmad-bmm-workflows-retrospective.md
- .codex/prompts/bmad-bmm-workflows-sprint-planning.md
- .codex/prompts/bmad-bmm-workflows-sprint-status.md
- .codex/prompts/bmad-bmm-workflows-testarch-atdd.md
- .codex/prompts/bmad-bmm-workflows-testarch-automate.md
- .codex/prompts/bmad-bmm-workflows-testarch-ci.md
- .codex/prompts/bmad-bmm-workflows-testarch-framework.md
- .codex/prompts/bmad-bmm-workflows-testarch-nfr.md
- .codex/prompts/bmad-bmm-workflows-testarch-test-design.md
- .codex/prompts/bmad-bmm-workflows-testarch-test-review.md
- .codex/prompts/bmad-bmm-workflows-testarch-trace.md
- .codex/prompts/bmad-bmm-workflows-workflow-init.md
- .codex/prompts/bmad-bmm-workflows-workflow-status.md
- .codex/prompts/bmad-core-agents-bmad-master.md
- .codex/prompts/bmad-core-workflows-README.md
- .codex/prompts/bmad-core-workflows-brainstorming.md
- .codex/prompts/bmad-core-workflows-party-mode.md
- .editorconfig
- .env.example
- .github/workflows/README.md
- .github/workflows/release.yml
- .gitignore
- README.md
- _bmad-output/analysis/brainstorming-session-2026-01-23.md
- _bmad-output/implementation-artifacts/1-1-initialize-project-from-starter-template.md
- _bmad-output/implementation-artifacts/1-2-enforce-isolation-rules-and-secure-psks.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- _bmad-output/planning-artifacts/architecture.md
- _bmad-output/planning-artifacts/epics.md
- _bmad-output/planning-artifacts/implementation-readiness-report-2026-01-23.md
- _bmad-output/planning-artifacts/prd-validation-report.md
- _bmad-output/planning-artifacts/prd.md
- _bmad-output/planning-artifacts/ux-color-themes.html
- _bmad-output/planning-artifacts/ux-design-directions.html
- _bmad-output/planning-artifacts/ux-design-specification.md
- _bmad-output/project-context.md
- _bmad/_config/agent-manifest.csv
- _bmad/_config/agents/bmm-analyst.customize.yaml
- _bmad/_config/agents/bmm-architect.customize.yaml
- _bmad/_config/agents/bmm-dev.customize.yaml
- _bmad/_config/agents/bmm-pm.customize.yaml
- _bmad/_config/agents/bmm-quick-flow-solo-dev.customize.yaml
- _bmad/_config/agents/bmm-sm.customize.yaml
- _bmad/_config/agents/bmm-tea.customize.yaml
- _bmad/_config/agents/bmm-tech-writer.customize.yaml
- _bmad/_config/agents/bmm-ux-designer.customize.yaml
- _bmad/_config/agents/core-bmad-master.customize.yaml
- _bmad/_config/files-manifest.csv
- _bmad/_config/ides/claude-code.yaml
- _bmad/_config/ides/codex.yaml
- _bmad/_config/manifest.yaml
- _bmad/_config/task-manifest.csv
- _bmad/_config/tool-manifest.csv
- _bmad/_config/workflow-manifest.csv
- _bmad/bmm/agents/analyst.md
- _bmad/bmm/agents/architect.md
- _bmad/bmm/agents/dev.md
- _bmad/bmm/agents/pm.md
- _bmad/bmm/agents/quick-flow-solo-dev.md
- _bmad/bmm/agents/sm.md
- _bmad/bmm/agents/tea.md
- _bmad/bmm/agents/tech-writer.md
- _bmad/bmm/agents/ux-designer.md
- _bmad/bmm/config.yaml
- _bmad/bmm/data/README.md
- _bmad/bmm/data/documentation-standards.md
- _bmad/bmm/data/project-context-template.md
- _bmad/bmm/teams/default-party.csv
- _bmad/bmm/teams/team-fullstack.yaml
- _bmad/bmm/testarch/knowledge/api-request.md
- _bmad/bmm/testarch/knowledge/api-testing-patterns.md
- _bmad/bmm/testarch/knowledge/auth-session.md
- _bmad/bmm/testarch/knowledge/burn-in.md
- _bmad/bmm/testarch/knowledge/ci-burn-in.md
- _bmad/bmm/testarch/knowledge/component-tdd.md
- _bmad/bmm/testarch/knowledge/contract-testing.md
- _bmad/bmm/testarch/knowledge/data-factories.md
- _bmad/bmm/testarch/knowledge/email-auth.md
- _bmad/bmm/testarch/knowledge/error-handling.md
- _bmad/bmm/testarch/knowledge/feature-flags.md
- _bmad/bmm/testarch/knowledge/file-utils.md
- _bmad/bmm/testarch/knowledge/fixture-architecture.md
- _bmad/bmm/testarch/knowledge/fixtures-composition.md
- _bmad/bmm/testarch/knowledge/intercept-network-call.md
- _bmad/bmm/testarch/knowledge/log.md
- _bmad/bmm/testarch/knowledge/network-error-monitor.md
- _bmad/bmm/testarch/knowledge/network-first.md
- _bmad/bmm/testarch/knowledge/network-recorder.md
- _bmad/bmm/testarch/knowledge/nfr-criteria.md
- _bmad/bmm/testarch/knowledge/overview.md
- _bmad/bmm/testarch/knowledge/playwright-config.md
- _bmad/bmm/testarch/knowledge/probability-impact.md
- _bmad/bmm/testarch/knowledge/recurse.md
- _bmad/bmm/testarch/knowledge/risk-governance.md
- _bmad/bmm/testarch/knowledge/selective-testing.md
- _bmad/bmm/testarch/knowledge/selector-resilience.md
- _bmad/bmm/testarch/knowledge/test-healing-patterns.md
- _bmad/bmm/testarch/knowledge/test-levels-framework.md
- _bmad/bmm/testarch/knowledge/test-priorities-matrix.md
- _bmad/bmm/testarch/knowledge/test-quality.md
- _bmad/bmm/testarch/knowledge/timing-debugging.md
- _bmad/bmm/testarch/knowledge/visual-debugging.md
- _bmad/bmm/testarch/tea-index.csv
- _bmad/bmm/workflows/1-analysis/create-product-brief/product-brief.template.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-01-init.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-01b-continue.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-02-vision.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-03-users.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-04-metrics.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-05-scope.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/steps/step-06-complete.md
- _bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-01-init.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-02-domain-analysis.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-03-competitive-landscape.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-04-regulatory-focus.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-05-technical-trends.md
- _bmad/bmm/workflows/1-analysis/research/domain-steps/step-06-research-synthesis.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-01-init.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-02-customer-behavior.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-02-customer-insights.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-03-customer-pain-points.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-04-customer-decisions.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-05-competitive-analysis.md
- _bmad/bmm/workflows/1-analysis/research/market-steps/step-06-research-completion.md
- _bmad/bmm/workflows/1-analysis/research/research.template.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-01-init.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-02-technical-overview.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-03-integration-patterns.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-04-architectural-patterns.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-05-implementation-research.md
- _bmad/bmm/workflows/1-analysis/research/technical-steps/step-06-research-synthesis.md
- _bmad/bmm/workflows/1-analysis/research/workflow.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-01-init.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-01b-continue.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-02-discovery.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-03-core-experience.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-04-emotional-response.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-05-inspiration.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-06-design-system.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-07-defining-experience.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-08-visual-foundation.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-09-design-directions.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-10-user-journeys.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-11-component-strategy.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-12-ux-patterns.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-13-responsive-accessibility.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/steps/step-14-complete.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/ux-design-template.md
- _bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md
- _bmad/bmm/workflows/2-plan-workflows/prd/data/domain-complexity.csv
- _bmad/bmm/workflows/2-plan-workflows/prd/data/prd-purpose.md
- _bmad/bmm/workflows/2-plan-workflows/prd/data/project-types.csv
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-01-init.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-01b-continue.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-02-discovery.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-03-success.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-04-journeys.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-05-domain.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-06-innovation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-07-project-type.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-08-scoping.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-09-functional.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-10-nonfunctional.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-11-polish.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-c/step-12-complete.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-e/step-e-01-discovery.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-e/step-e-01b-legacy-conversion.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-e/step-e-02-review.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-e/step-e-03-edit.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-e/step-e-04-complete.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-01-discovery.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-02-format-detection.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-02b-parity-check.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-03-density-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-04-brief-coverage-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-05-measurability-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-06-traceability-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-07-implementation-leakage-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-08-domain-compliance-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-09-project-type-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-10-smart-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-11-holistic-quality-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-12-completeness-validation.md
- _bmad/bmm/workflows/2-plan-workflows/prd/steps-v/step-v-13-report-complete.md
- _bmad/bmm/workflows/2-plan-workflows/prd/templates/prd-template.md
- _bmad/bmm/workflows/2-plan-workflows/prd/validation-report-prd-workflow.md
- _bmad/bmm/workflows/2-plan-workflows/prd/workflow.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-01-document-discovery.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-02-prd-analysis.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-03-epic-coverage-validation.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-04-ux-alignment.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-05-epic-quality-review.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/steps/step-06-final-assessment.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/templates/readiness-report-template.md
- _bmad/bmm/workflows/3-solutioning/check-implementation-readiness/workflow.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/architecture-decision-template.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/data/domain-complexity.csv
- _bmad/bmm/workflows/3-solutioning/create-architecture/data/project-types.csv
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-01-init.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-01b-continue.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-02-context.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-03-starter.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-04-decisions.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-05-patterns.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-06-structure.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-07-validation.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/steps/step-08-complete.md
- _bmad/bmm/workflows/3-solutioning/create-architecture/workflow.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/steps/step-01-validate-prerequisites.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/steps/step-02-design-epics.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/steps/step-03-create-stories.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/steps/step-04-final-validation.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/templates/epics-template.md
- _bmad/bmm/workflows/3-solutioning/create-epics-and-stories/workflow.md
- _bmad/bmm/workflows/4-implementation/code-review/checklist.md
- _bmad/bmm/workflows/4-implementation/code-review/instructions.xml
- _bmad/bmm/workflows/4-implementation/code-review/workflow.yaml
- _bmad/bmm/workflows/4-implementation/correct-course/checklist.md
- _bmad/bmm/workflows/4-implementation/correct-course/instructions.md
- _bmad/bmm/workflows/4-implementation/correct-course/workflow.yaml
- _bmad/bmm/workflows/4-implementation/create-story/checklist.md
- _bmad/bmm/workflows/4-implementation/create-story/instructions.xml
- _bmad/bmm/workflows/4-implementation/create-story/template.md
- _bmad/bmm/workflows/4-implementation/create-story/workflow.yaml
- _bmad/bmm/workflows/4-implementation/dev-story/checklist.md
- _bmad/bmm/workflows/4-implementation/dev-story/instructions.xml
- _bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml
- _bmad/bmm/workflows/4-implementation/retrospective/instructions.md
- _bmad/bmm/workflows/4-implementation/retrospective/workflow.yaml
- _bmad/bmm/workflows/4-implementation/sprint-planning/checklist.md
- _bmad/bmm/workflows/4-implementation/sprint-planning/instructions.md
- _bmad/bmm/workflows/4-implementation/sprint-planning/sprint-status-template.yaml
- _bmad/bmm/workflows/4-implementation/sprint-planning/workflow.yaml
- _bmad/bmm/workflows/4-implementation/sprint-status/instructions.md
- _bmad/bmm/workflows/4-implementation/sprint-status/workflow.yaml
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-01-mode-detection.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-02-context-gathering.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-03-execute.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-04-self-check.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-05-adversarial-review.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/steps/step-06-resolve-findings.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-dev/workflow.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/steps/step-01-understand.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/steps/step-02-investigate.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/steps/step-03-generate.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/steps/step-04-review.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/tech-spec-template.md
- _bmad/bmm/workflows/bmad-quick-flow/quick-spec/workflow.md
- _bmad/bmm/workflows/document-project/checklist.md
- _bmad/bmm/workflows/document-project/documentation-requirements.csv
- _bmad/bmm/workflows/document-project/instructions.md
- _bmad/bmm/workflows/document-project/templates/deep-dive-template.md
- _bmad/bmm/workflows/document-project/templates/index-template.md
- _bmad/bmm/workflows/document-project/templates/project-overview-template.md
- _bmad/bmm/workflows/document-project/templates/project-scan-report-schema.json
- _bmad/bmm/workflows/document-project/templates/source-tree-template.md
- _bmad/bmm/workflows/document-project/workflow.yaml
- _bmad/bmm/workflows/document-project/workflows/deep-dive-instructions.md
- _bmad/bmm/workflows/document-project/workflows/deep-dive.yaml
- _bmad/bmm/workflows/document-project/workflows/full-scan-instructions.md
- _bmad/bmm/workflows/document-project/workflows/full-scan.yaml
- _bmad/bmm/workflows/excalidraw-diagrams/_shared/excalidraw-library.json
- _bmad/bmm/workflows/excalidraw-diagrams/_shared/excalidraw-templates.yaml
- _bmad/bmm/workflows/excalidraw-diagrams/create-dataflow/checklist.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-dataflow/instructions.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-dataflow/workflow.yaml
- _bmad/bmm/workflows/excalidraw-diagrams/create-diagram/checklist.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-diagram/instructions.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-diagram/workflow.yaml
- _bmad/bmm/workflows/excalidraw-diagrams/create-flowchart/checklist.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-flowchart/instructions.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-flowchart/workflow.yaml
- _bmad/bmm/workflows/excalidraw-diagrams/create-wireframe/checklist.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-wireframe/instructions.md
- _bmad/bmm/workflows/excalidraw-diagrams/create-wireframe/workflow.yaml
- _bmad/bmm/workflows/generate-project-context/project-context-template.md
- _bmad/bmm/workflows/generate-project-context/steps/step-01-discover.md
- _bmad/bmm/workflows/generate-project-context/steps/step-02-generate.md
- _bmad/bmm/workflows/generate-project-context/steps/step-03-complete.md
- _bmad/bmm/workflows/generate-project-context/workflow.md
- _bmad/bmm/workflows/testarch/atdd/atdd-checklist-template.md
- _bmad/bmm/workflows/testarch/atdd/checklist.md
- _bmad/bmm/workflows/testarch/atdd/instructions.md
- _bmad/bmm/workflows/testarch/atdd/workflow.yaml
- _bmad/bmm/workflows/testarch/automate/checklist.md
- _bmad/bmm/workflows/testarch/automate/instructions.md
- _bmad/bmm/workflows/testarch/automate/workflow.yaml
- _bmad/bmm/workflows/testarch/ci/checklist.md
- _bmad/bmm/workflows/testarch/ci/github-actions-template.yaml
- _bmad/bmm/workflows/testarch/ci/gitlab-ci-template.yaml
- _bmad/bmm/workflows/testarch/ci/instructions.md
- _bmad/bmm/workflows/testarch/ci/workflow.yaml
- _bmad/bmm/workflows/testarch/framework/checklist.md
- _bmad/bmm/workflows/testarch/framework/instructions.md
- _bmad/bmm/workflows/testarch/framework/workflow.yaml
- _bmad/bmm/workflows/testarch/nfr-assess/checklist.md
- _bmad/bmm/workflows/testarch/nfr-assess/instructions.md
- _bmad/bmm/workflows/testarch/nfr-assess/nfr-report-template.md
- _bmad/bmm/workflows/testarch/nfr-assess/workflow.yaml
- _bmad/bmm/workflows/testarch/test-design/checklist.md
- _bmad/bmm/workflows/testarch/test-design/instructions.md
- _bmad/bmm/workflows/testarch/test-design/test-design-template.md
- _bmad/bmm/workflows/testarch/test-design/workflow.yaml
- _bmad/bmm/workflows/testarch/test-review/checklist.md
- _bmad/bmm/workflows/testarch/test-review/instructions.md
- _bmad/bmm/workflows/testarch/test-review/test-review-template.md
- _bmad/bmm/workflows/testarch/test-review/workflow.yaml
- _bmad/bmm/workflows/testarch/trace/checklist.md
- _bmad/bmm/workflows/testarch/trace/instructions.md
- _bmad/bmm/workflows/testarch/trace/trace-template.md
- _bmad/bmm/workflows/testarch/trace/workflow.yaml
- _bmad/bmm/workflows/workflow-status/init/instructions.md
- _bmad/bmm/workflows/workflow-status/init/workflow.yaml
- _bmad/bmm/workflows/workflow-status/instructions.md
- _bmad/bmm/workflows/workflow-status/paths/enterprise-brownfield.yaml
- _bmad/bmm/workflows/workflow-status/paths/enterprise-greenfield.yaml
- _bmad/bmm/workflows/workflow-status/paths/method-brownfield.yaml
- _bmad/bmm/workflows/workflow-status/paths/method-greenfield.yaml
- _bmad/bmm/workflows/workflow-status/project-levels.yaml
- _bmad/bmm/workflows/workflow-status/workflow-status-template.yaml
- _bmad/bmm/workflows/workflow-status/workflow.yaml
- _bmad/core/agents/bmad-master.md
- _bmad/core/config.yaml
- _bmad/core/resources/excalidraw/README.md
- _bmad/core/resources/excalidraw/excalidraw-helpers.md
- _bmad/core/resources/excalidraw/library-loader.md
- _bmad/core/resources/excalidraw/validate-json-instructions.md
- _bmad/core/tasks/index-docs.xml
- _bmad/core/tasks/review-adversarial-general.xml
- _bmad/core/tasks/shard-doc.xml
- _bmad/core/tasks/workflow.xml
- _bmad/core/workflows/advanced-elicitation/methods.csv
- _bmad/core/workflows/advanced-elicitation/workflow.xml
- _bmad/core/workflows/brainstorming/brain-methods.csv
- _bmad/core/workflows/brainstorming/steps/step-01-session-setup.md
- _bmad/core/workflows/brainstorming/steps/step-01b-continue.md
- _bmad/core/workflows/brainstorming/steps/step-02a-user-selected.md
- _bmad/core/workflows/brainstorming/steps/step-02b-ai-recommended.md
- _bmad/core/workflows/brainstorming/steps/step-02c-random-selection.md
- _bmad/core/workflows/brainstorming/steps/step-02d-progressive-flow.md
- _bmad/core/workflows/brainstorming/steps/step-03-technique-execution.md
- _bmad/core/workflows/brainstorming/steps/step-04-idea-organization.md
- _bmad/core/workflows/brainstorming/template.md
- _bmad/core/workflows/brainstorming/workflow.md
- _bmad/core/workflows/party-mode/steps/step-01-agent-loading.md
- _bmad/core/workflows/party-mode/steps/step-02-discussion-orchestration.md
- _bmad/core/workflows/party-mode/steps/step-03-graceful-exit.md
- _bmad/core/workflows/party-mode/workflow.md
- backend/alembic.ini
- backend/alembic/env.py
- backend/alembic/versions/20260125_0001_create_peers.py
- backend/app/__init__.py
- backend/app/config.py
- backend/app/db/__init__.py
- backend/app/db/base.py
- backend/app/db/session.py
- backend/app/models/__init__.py
- backend/app/models/peer.py
- backend/app/schemas/__init__.py
- backend/app/schemas/peer.py
- backend/app/services/__init__.py
- backend/app/services/peer_service.py
- backend/app/services/psk_crypto.py
- backend/daemon/__init__.py
- backend/daemon/ipc/__init__.py
- backend/daemon/ipc/commands.py
- backend/daemon/main.py
- backend/daemon/ops/__init__.py
- backend/daemon/ops/nftables.py
- backend/daemon/startup.py
- backend/main.py
- backend/requirements.txt
- backend/tests/integration/test_isolation_rules_integration.py
- backend/tests/integration/test_peer_storage_encrypted.py
- backend/tests/unit/test_app.py
- backend/tests/unit/test_daemon_ipc.py
- backend/tests/unit/test_isolation_rules.py
- backend/tests/unit/test_peer_schema.py
- backend/tests/unit/test_psk_crypto.py
- backend/tests/unit/test_daemon_ipc_server.py
- docs/README.md
- docs/api-reference.md
- docs/architecture.md
- docs/ports-protocols.md
- docs/security-report.md
- frontend/.gitignore
- frontend/README.md
- frontend/eslint.config.js
- frontend/index.html
- frontend/package-lock.json
- frontend/package.json
- frontend/public/vite.svg
- frontend/src/App.css
- frontend/src/App.tsx
- frontend/src/assets/react.svg
- frontend/src/index.css
- frontend/src/main.tsx
- frontend/tests/unit/App.test.ts
- frontend/tsconfig.app.json
- frontend/tsconfig.json
- frontend/tsconfig.node.json
- frontend/vite.config.ts
- image/README.md
- image/build-image.sh
- backend/app/services/daemon_ipc.py
- backend/daemon/ipc/server.py
- backend/tests/unit/test_daemon_ipc_client.py
## Change Log

- 2026-01-25: Implemented isolation enforcement and PSK encryption with tests and migrations.
- 2026-01-25: Scoped isolation rules to PT/CT interface allowlist and wired PSK key from settings with updated tests.
- 2026-01-25: Added IPC support for interface allowlist in isolation enforcement.
- 2026-01-25: Addressed code review findings - 3 items resolved.
