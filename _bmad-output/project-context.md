---
project_name: 'Encryptor-Sim-BMAD'
user_name: 'Will'
date: '2026-01-23T18:58:46-0500'
sections_completed: ['technology_stack', 'language_specific', 'framework_specific', 'testing', 'code_quality']
existing_patterns_found: 6
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Python 3.12
- FastAPI 0.128.0
- SQLAlchemy 2.0.46
- Alembic 1.18.1
- React 19.2.3
- Vite 7.3.1
- Chakra UI 3.31.0
- Zustand 5.0.10
- strongSwan 6.0.4
- nftables 1.1.6
- OpenRC 0.63
- Alpine Linux 3.23.2
- SQLite (default embedded DB)

## Critical Implementation Rules

_Documented after discovery phase_

### Language-Specific Rules

- Python: Use Pydantic models for request/response validation.
- Python: Use SQLAlchemy ORM for DB access and Alembic for migrations (no manual DB edits).
- Python: Use centralized RFC 7807 error shaping utilities; raise HTTPException consistently.
- TypeScript: Use camelCase for JSON fields and API DTOs.
- TypeScript: React components use `PascalCase.tsx`; avoid default exports.
- TypeScript: Prefer async/await over promise chains.

### Framework-Specific Rules

- React: State via Zustand stores per domain (`peers`, `routes`, `interfaces`, `tunnels`).
- React: Routing via React Router; pages live under `pages/`.
- React: WebSocket payloads are `{ type, data }` and update Zustand via action verbs.
- FastAPI: REST + WebSocket; RFC 7807 for errors; OpenAPI via defaults.
- FastAPI: Auth enforced via dependencies; JWT access + refresh tokens.

### Testing Rules

- Tests live under `frontend/tests/{unit,integration,e2e}` and `backend/tests/{unit,integration,e2e}`.
- Frontend test files: `*.test.ts`; backend test files: `test_*.py`.
- Integration tests must cover API + daemon IPC happy path and failure path.
- Tests should not edit the DB directly; use ORM/session helpers.
- Run backend tests using the repo virtual environment: `./.venv/bin/python -m pytest` (not system Python).

### Code Quality & Style Rules

- Naming: DB columns camelCase; PKs `<table>Id`; REST paths plural; `/api/v1` prefix.
- JSON fields camelCase; errors follow RFC 7807.
- TypeScript: no default exports; React component files in PascalCase.
- API responses use `{ data, meta }` envelope for success.
- WebSocket events use dot-notation names (e.g., `tunnel.status_changed`).
