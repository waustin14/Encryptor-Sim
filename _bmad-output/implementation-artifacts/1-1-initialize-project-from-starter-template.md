# Story 1.1: Initialize Project from Starter Template

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to initialize the project using the approved starter templates,
so that the codebase follows the architectural foundation from the start.

## Acceptance Criteria

1. Frontend is scaffolded with the Vite React TypeScript template under `frontend/`.
2. Backend Python virtual environment is created and a FastAPI baseline exists under `backend/`.
3. The repository contains `frontend/` and `backend/` directories and aligns with the agreed architecture starter structure.

## Tasks / Subtasks

- [x] Scaffold frontend (AC: 1, 3)
  - [x] Run `npm create vite@latest frontend -- --template react-ts` from repo root
  - [x] Create expected frontend subfolders (`src/pages`, `src/components`, `src/hooks`, `src/services`, `src/state`, `src/routes`, `src/styles`)
  - [x] Ensure package versions align with architecture (React 19.2.3, Vite 7.3.1) and update `frontend/package.json` if template versions differ
- [x] Scaffold backend (AC: 2, 3)
  - [x] Create `.venv` at repo root with Python 3.12
  - [x] Initialize `backend/` with a minimal FastAPI app (`backend/main.py`) and `requirements.txt`
  - [x] Create backend directory skeleton per architecture (`backend/app/api`, `backend/app/models`, `backend/app/schemas`, `backend/app/services`, `backend/app/repositories`, `backend/app/db`, `backend/app/auth`, `backend/app/ws`, `backend/daemon/ops`, `backend/daemon/ipc`, `backend/tests/{unit,integration,e2e}`)
  - [x] Pin FastAPI version to 0.128.0 in `backend/requirements.txt` and document any additional baseline packages
- [x] Sanity checks (AC: 1, 2)
  - [x] `npm install` in `frontend/` completes successfully
  - [x] `python -m uvicorn backend.main:app --reload` starts without import errors

## Developer Context

Goal: establish the approved frontend and backend scaffolds only. No feature implementation or app logic beyond a minimal FastAPI app instance and the default Vite React template.

In scope:
- Repo scaffolding
- Directory skeletons aligned to architecture
- Version alignment for core dependencies

Out of scope:
- Any domain features (interfaces, peers, routes)
- Database schema or migrations
- Authentication or API endpoints beyond the minimal app instance

## Technical Requirements

- Frontend scaffold: Vite React TypeScript template under `frontend/`.
- Backend scaffold: Python 3.12 virtual environment at repo root and a minimal FastAPI app under `backend/`.
- Keep the separation between frontend and backend top-level directories.
- Use the stack versions listed in project context and architecture for baseline dependencies.

## Architecture Compliance

- Follow the layered frontend structure (`pages`, `components`, `hooks`, `services`, `state`, `routes`, `styles`).
- Follow the backend structure (`api`, `models`, `schemas`, `services`, `repositories`, `db`, `auth`, `ws`) and daemon boundary (`backend/daemon`).
- Do not introduce deviations from naming and response format conventions even in early scaffolding.

## Library & Framework Requirements

- React 19.2.3
- Vite 7.3.1
- FastAPI 0.128.0
- Python 3.12

## File Structure Requirements

Create or ensure the following exist:

- `frontend/` (Vite React TS scaffold)
- `frontend/src/pages`
- `frontend/src/components`
- `frontend/src/hooks`
- `frontend/src/services`
- `frontend/src/state`
- `frontend/src/routes`
- `frontend/src/styles`
- `frontend/tests/unit`
- `frontend/tests/integration`
- `frontend/tests/e2e`
- `backend/`
- `backend/main.py`
- `backend/app/api`
- `backend/app/models`
- `backend/app/schemas`
- `backend/app/services`
- `backend/app/repositories`
- `backend/app/db`
- `backend/app/auth`
- `backend/app/ws`
- `backend/daemon/ops`
- `backend/daemon/ipc`
- `backend/tests/unit`
- `backend/tests/integration`
- `backend/tests/e2e`

## Testing Requirements

- `npm install` succeeds in `frontend/`.
- `python -m uvicorn backend.main:app --reload` starts without errors.

## Project Context Reference

- Use `{ data, meta }` success envelopes and RFC 7807 errors for future API work.
- JSON field names are camelCase; REST paths are plural and under `/api/v1`.
- React components use `PascalCase.tsx` and avoid default exports.
- WebSocket events use `{ type, data }` with dot-notation event names.

## Completion Status

Status: done

Completion note: Frontend and backend scaffolds created with minimal tests and sanity checks completed.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1: Initialize Project from Starter Template]
- [Source: _bmad-output/project-context.md#Technology Stack & Versions]
- [Source: _bmad-output/project-context.md#Critical Implementation Rules]

## Dev Agent Record

### Agent Model Used

GPT-5 (Codex)

### Debug Log References

create-story workflow; dev-story scaffold and test harness run

### Implementation Plan

- Scaffold frontend via Vite template and align React/Vite versions.
- Scaffold backend with minimal FastAPI app and required directory layout.
- Add minimal test harness (vitest/pytest) and complete sanity checks.

### Completion Notes List

- Story scaffolded from epics + architecture + project context.
- Frontend scaffolded via Vite React TS; React 19.2.3 and Vite 7.3.1 pinned.
- Backend scaffolded with `.venv`, minimal FastAPI app, and required directory skeleton.
- Added minimal test harness (vitest/pytest) and verified sanity checks.
- Code review fixes: named export for App, safer external links, jsdom test env, and expanded repo structure placeholders.
- Web research step skipped (offline); no external version changes introduced.

### File List

- .editorconfig
- .env.example
- .github/workflows/README.md
- .github/workflows/release.yml
- .gitignore
- README.md
- .venv/
- backend/main.py
- backend/requirements.txt
- backend/tests/unit/test_app.py
- frontend/.gitignore
- frontend/README.md
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
- frontend/eslint.config.js
- frontend/tsconfig.app.json
- frontend/tsconfig.json
- frontend/tsconfig.node.json
- frontend/vite.config.ts
- docs/api-reference.md
- docs/architecture.md
- docs/ports-protocols.md
- docs/security-report.md
- image/build-image.sh
- docs/README.md
- image/README.md
- _bmad-output/implementation-artifacts/1-1-initialize-project-from-starter-template.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-01-25: Scaffolded frontend/backend, added minimal test harness, and completed sanity checks.
