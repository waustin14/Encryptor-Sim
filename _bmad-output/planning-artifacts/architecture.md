---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/analysis/brainstorming-session-2026-01-23.md'
workflowType: 'architecture'
project_name: 'Encryptor-Sim-BMAD'
user_name: 'Will'
date: '2026-01-23T17:25:40-0500'
lastStep: 8
status: 'complete'
completedAt: '2026-01-23T18:57:16-0500'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- 59 FRs spanning deployment/boot, CT/PT/MGMT interface configuration, peer/route CRUD, IPsec tunnel lifecycle, real-time monitoring, JWT authentication, REST API automation, security isolation validation, and documentation access.
- Architecturally, this implies a backend that can orchestrate strongSwan, manage configuration state, enforce namespace isolation rules, and stream live status to the UI.

**Non-Functional Requirements:**
- Performance: <30s boot, <2s UI load, 50 peers/150 routes, 10+ Mbps per tunnel, WebSocket updates at 1–2s intervals.
- Security: strict PT/CT isolation, HTTPS-only MGMT, PSKs encrypted at rest, no IPv6 in V1.0, published security testing results.
- Reliability: 30+ days uptime, atomic config changes, resilient WebSocket reconnection.
- Maintainability: PEP8/ESLint, OpenAPI docs, contribution guidelines.
- Platform: Alpine Linux 3.19+, qcow2 for CML, 1–2GB RAM target, browser compatibility.

**Scale & Complexity:**
- Primary domain: full-stack network appliance with embedded security and networking.
- Complexity level: high.
- Estimated architectural components: 7–9 (web UI, API/backend, config store, strongSwan integration, namespace/isolation layer, monitoring/telemetry, packaging/boot services, security validation/testing, docs).

### Technical Constraints & Dependencies

- Deployment constraint: qcow2 image for CML; Alpine Linux base; IPv6 disabled in V1.0.
- Resource constraints: <2GB RAM target, 2–4 vCPU.
- Security constraints: HTTPS-only MGMT, JWT auth, PSKs encrypted at rest, strict PT↔CT filtering.
- Key dependencies: strongSwan/vici, nftables, FastAPI, SQLite, React, WebSocket stack, pyroute2/pyvici.

### Cross-Cutting Concerns Identified

- Isolation correctness and proof (PT→CT must be blocked under all conditions).
- Real-time visibility and operational confidence (live tunnel/interface status).
- Security transparency and hardening (validation reports, scanning).
- Reliability and recovery in locked-down appliance mode.
- Documentation quality (ports/protocols, architecture, security report).

## Starter Template Evaluation

### Primary Technology Domain

Full-stack network appliance: React-based admin UI plus FastAPI backend, with system-level networking components (strongSwan, nftables, namespaces).

### Starter Options Considered

**Option A: Vite React TypeScript + FastAPI minimal backend**
- Vite provides a modern React + TS scaffold and fast dev server.
- FastAPI provides async REST + WebSocket APIs with OpenAPI docs.
- Fits the stated preferences: React, Chakra UI, Zustand, FastAPI, SQLite.

**Option B: Monorepo with separate frontend/backend packages**
- Same tech as Option A but structured as a single repo with `frontend/` and `backend/`.
- Keeps system-level code (nftables, strongSwan config generation) in backend package.

### Selected Starter: Vite React TypeScript + FastAPI minimal backend

**Rationale for Selection:**
- Aligns with the documented preferences (React, FastAPI, SQLite).
- Provides a clean separation between UI and API while remaining lightweight.
- Keeps the system appliance work isolated in the backend where it belongs.

**Initialization Command:**

```bash
# frontend
npm create vite@latest frontend -- --template react-ts

# backend
python -m venv .venv
. .venv/bin/activate
pip install fastapi uvicorn[standard]
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Frontend: TypeScript + React.
- Backend: Python + FastAPI.

**Styling Solution:**
- Chakra UI to be added as the component library after scaffold.

**Build Tooling:**
- Vite for frontend build/dev server.
- Uvicorn for backend dev server.

**Testing Framework:**
- Not included by default; will be selected in later architecture decisions.

**Code Organization:**
- Separate `frontend/` and `backend/` directories to isolate UI, API, and system services.

**Development Experience:**
- Fast hot reload for UI, OpenAPI docs for API, and easy local iteration.

**Note:** Project initialization using these commands should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Data architecture: SQLite + SQLAlchemy + Pydantic + Alembic (no caching initially).
- Security: JWT access/refresh tokens, HTTPS-only MGMT, argon2id for passwords, app-layer PSK encryption.
- System orchestration: backend + privileged local daemon over Unix socket.
- API/Realtime: REST + WebSocket, RFC 7807 errors.
- Frontend: React + Zustand + React Router, layered structure.

**Important Decisions (Shape Architecture):**
- OpenAPI docs via FastAPI defaults.
- No rate limiting initially.
- Proactive frontend optimization.
- Structured logging with rotation.

**Deferred Decisions (Post-MVP):**
- RBAC (admin/read-only).
- Rate limiting.
- Caching strategy.
- Additional observability and telemetry export.

**Version verification:** Deferred (no specific versions provided).

### Data Architecture

- **Database:** SQLite (PRD-aligned).
- **Modeling:** SQLAlchemy ORM.
- **Validation:** Pydantic models.
- **Migrations:** Alembic.
- **Caching:** None initially.

**Rationale:** Small dataset and appliance scope favor simplicity; Alembic enables safe schema evolution across releases.

### Authentication & Security

- **Auth:** JWT access + refresh tokens.
- **Authorization:** Admin-only for V1.0; RBAC deferred.
- **Middleware:** Standard auth dependency + baseline CORS/security headers.
- **Passwords:** argon2id hashing.
- **PSKs at rest:** Application-layer encryption (plus OS file permissions).
- **API security:** HTTPS-only on MGMT; no IP allowlist.

**Rationale:** Aligns with security expectations while keeping implementation focused for V1.0.

### API & Communication Patterns

- **API pattern:** REST + WebSocket for realtime status.
- **Docs:** OpenAPI/Swagger (FastAPI defaults).
- **Errors:** RFC 7807 problem details.
- **Rate limiting:** None initially.
- **Service communication:** FastAPI in MGMT namespace with a privileged local daemon via Unix socket for strongSwan/nftables/namespace ops.

**Rationale:** Clear separation of concerns with controlled privilege boundary; realtime updates are first-class.

### Frontend Architecture

- **State:** Zustand.
- **Structure:** Layered (components/pages/hooks).
- **Routing:** React Router.
- **Performance:** Proactive optimizations where appropriate.
- **Bundling:** Vite defaults.

**Rationale:** Lightweight state management and conventional routing enable maintainable UI with good responsiveness.

### Infrastructure & Deployment

- **Hosting strategy:** Local builds for now.
- **CI/CD:** Full qcow2 image build and publish on release.
- **Environment config:** `.env` for dev; appliance system config file for runtime.
- **Logging:** Structured logs with rotation.
- **Scaling:** Single appliance focus for now.

### Decision Impact Analysis

**Implementation Sequence:**
1) SQLite schema + SQLAlchemy models + Alembic setup
2) Auth/security layer (JWT, argon2id, PSK encryption)
3) Local daemon + Unix socket IPC boundary
4) REST API + WebSocket events + RFC 7807 errors
5) Frontend routing/state + realtime UI
6) Packaging, logging, and release image pipeline

**Cross-Component Dependencies:**
- Daemon IPC shapes API endpoints and security boundaries.
- Auth choices affect both API and UI flows.
- Alembic and Pydantic models drive API contracts and validation logic.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 6 areas (naming, structure, format, communication, process, data modeling)

### Naming Patterns

**Database Naming Conventions:**
- Tables: plural (`peers`, `routes`, `interfaces`)
- Columns: `camelCase` (e.g., `peerId`, `createdAt`)
- Primary key: `<table>Id` (e.g., `peerId`)
- Foreign keys: `fk_<table>` (e.g., `fk_peer`)
- Indexes: `idx_<table>_<column>` (e.g., `idx_peers_remoteIp`)

**API Naming Conventions:**
- REST paths: plural (`/peers`, `/routes`)
- Route params: `{id}`
- Query params: `camelCase`
- Versioning: `/api/v1/...`

**Code Naming Conventions:**
- React component files: `PascalCase.tsx`
- Frontend folders: `kebab-case`
- Backend Python modules: `snake_case`

### Structure Patterns

**Project Organization:**
- Frontend and backend remain in separate top-level folders: `frontend/`, `backend/`
- Frontend is layered: `components/`, `pages/`, `hooks/`, `services/`, `state/`
- Backend uses a clear separation: `api/`, `models/`, `schemas/`, `services/`, `repositories/`, `daemon/`

**File Structure Patterns:**
- Tests are co-located with implementation where feasible (`*.test.ts`, `test_*.py`)
- Env files only in dev (`.env`), appliance config is separate (`/etc/<app>/config.yaml` or similar)

### Format Patterns

**API Response Formats:**
- Success responses use a consistent envelope: `{ data, meta }`
- Error responses follow RFC 7807 (problem details) without additional wrapping

**Data Exchange Formats:**
- JSON fields: `camelCase`
- Date/time: ISO-8601 UTC strings (e.g., `2026-01-23T14:36:23Z`)
- Booleans: JSON `true/false`

### Communication Patterns

**Event System Patterns:**
- Event names use dot notation: `tunnel.status_changed`, `peer.created`
- WebSocket payloads are `{ type, data }` only (no mixed shapes)
- Event payloads should be versioned implicitly by API version

**State Management Patterns:**
- Zustand store per domain (`peers`, `routes`, `interfaces`, `tunnels`)
- Actions are verbs (`fetchPeers`, `updateRoute`, `setTunnelStatus`)

### Process Patterns

**Error Handling Patterns:**
- RFC 7807 for all error responses
- User-facing errors are derived from `title` and `detail`

**Loading State Patterns:**
- Local per-view loading state plus a global `app.loadingCount` for app-wide spinners
- No single global boolean to avoid contention

### Enforcement Guidelines

**All AI Agents MUST:**
- Use the naming conventions above for DB/API/code identifiers
- Follow the response format rules (success envelope + RFC 7807 errors)
- Emit WebSocket events using `{ type, data }` with dot-notation event names

**Pattern Enforcement:**
- Add lint/format checks where possible
- Reject PRs that violate naming/format rules
- Document exceptions explicitly in architecture.md

### Pattern Examples

**Good Examples:**
- `GET /api/v1/peers` → `{ data: [...], meta: { count: 2 } }`
- Error: `{\"type\":\"about:blank\",\"title\":\"Validation Error\",\"status\":422,\"detail\":\"peerId is required\"}`
- WebSocket: `{ \"type\": \"tunnel.status_changed\", \"data\": { \"peerId\": \"p1\", \"status\": \"up\" } }`

**Anti-Patterns:**
- `GET /peer` (singular)
- `snake_case` JSON fields
- WebSocket payloads that omit `type`

## Project Structure & Boundaries

### Complete Project Directory Structure
```
encryptor-sim-bmad/
├── README.md
├── .gitignore
├── .editorconfig
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── ports-protocols.md
│   ├── security-report.md
│   └── api-reference.md
├── .github/
│   └── workflows/
│       └── release.yml
├── image/
│   ├── build-image.sh
│   ├── rootfs/
│   ├── openrc/
│   └── config/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env.example
│   ├── public/
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       ├── state/
│       ├── routes/
│       └── styles/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
└── backend/
    ├── requirements.txt
    ├── alembic.ini
    ├── main.py
    ├── config/
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    ├── app/
    │   ├── api/
    │   ├── models/
    │   ├── schemas/
    │   ├── services/
    │   ├── repositories/
    │   ├── db/
    │   ├── auth/
    │   └── ws/
    ├── daemon/
    │   ├── daemon_main.py
    │   ├── ops/
    │   └── ipc/
    └── tests/
        ├── unit/
        ├── integration/
        └── e2e/
```

### Architectural Boundaries

**API Boundaries:**
- External REST + WebSocket endpoints live under `backend/app/api/` and `backend/app/ws/`.
- Auth boundary enforced in `backend/app/auth/` (JWT access/refresh).
- RFC 7807 error shaping centralized in `backend/app/api/` utilities.

**Component Boundaries:**
- Frontend feature implementation stays within `frontend/src/pages/` + `components/` + `state/`.
- Backend orchestration stays in `backend/app/services/`.
- Privileged operations isolated in `backend/daemon/` with Unix socket IPC.

**Service Boundaries:**
- FastAPI app in `backend/app/` handles API, auth, and validation.
- Daemon in `backend/daemon/` owns strongSwan, nftables, namespaces, and system-level ops.
- IPC contract defined in `backend/daemon/ipc/`.

**Data Boundaries:**
- ORM models in `backend/app/models/`.
- Pydantic schemas in `backend/app/schemas/`.
- DB session management in `backend/app/db/`.
- Repository layer in `backend/app/repositories/`.

### Requirements to Structure Mapping

**Feature/Epic Mapping (FR Categories):**
- Deployment/Initialization (FR1–FR4) → `image/`, `backend/config/`, `backend/daemon/ops/`
- Interface Configuration (FR5–FR9) → `backend/app/api/`, `backend/app/services/`, `frontend/src/pages/`
- Peer Management (FR10–FR17) → `backend/app/api/`, `backend/app/models/`, `frontend/src/pages/peers`
- Route Management (FR18–FR23) → `backend/app/api/`, `backend/app/models/`, `frontend/src/pages/routes`
- Tunnel Control (FR24–FR30) → `backend/daemon/ops/`, `backend/app/services/`, `frontend/src/state/`
- Real-Time Monitoring (FR31–FR36) → `backend/app/ws/`, `frontend/src/state/`, `frontend/src/components/`
- Auth & Access Control (FR37–FR42) → `backend/app/auth/`, `frontend/src/services/`
- API Operations (FR43–FR50) → `backend/app/api/`, `backend/app/schemas/`
- Security & Isolation (FR51–FR55) → `backend/daemon/ops/`, `backend/app/services/`, `docs/security-report.md`
- Documentation (FR56–FR59) → `docs/`

**Cross-Cutting Concerns:**
- Logging → `backend/app/services/`, `backend/daemon/`, `image/` log config
- WebSocket event contracts → `backend/app/ws/`, `frontend/src/state/`

### Integration Points

**Internal Communication:**
- FastAPI ⇄ Daemon via Unix socket IPC (command + status channel).
- FastAPI ⇄ DB via SQLAlchemy repositories.
- Frontend ⇄ API via REST; Frontend ⇄ WS via WebSocket.

**External Integrations:**
- strongSwan/vici and nftables via daemon ops.
- CML deployment through `image/` build output (qcow2).

**Data Flow:**
- UI actions → REST API → services → daemon IPC → system ops.
- System status → daemon → API/WebSocket → Zustand store → UI.

### File Organization Patterns

**Configuration Files:**
- Dev config: `.env` files.
- Appliance config: generated at runtime to `/etc/<app>/config.yaml`, sourced from `backend/config/`.

**Source Organization:**
- Backend separation between API, domain models, and privileged ops.
- Frontend layered separation by UI responsibility.

**Test Organization:**
- `frontend/tests/unit|integration|e2e`
- `backend/tests/unit|integration|e2e`

**Asset Organization:**
- Frontend static assets in `frontend/public/`.
- Documentation assets in `docs/`.

### Development Workflow Integration

**Development Server Structure:**
- Frontend Vite dev server in `frontend/`.
- Backend FastAPI dev server in `backend/`.

**Build Process Structure:**
- Frontend build outputs bundled into image build step.
- Backend packaged into image rootfs.

**Deployment Structure:**
- `image/` orchestrates qcow2 build, boot configuration, and OpenRC services.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
The selected stack (Python 3.12 + FastAPI 0.128.0 + SQLAlchemy 2.0.46 + Alembic 1.18.1; React 19.2.3 + Vite 7.3.1 + Chakra UI 3.31.0 + Zustand 5.0.10; strongSwan 6.0.4 + nftables 1.1.6 + OpenRC 0.63 + Alpine 3.23.2) is compatible and aligns with the appliance constraints.

**Pattern Consistency:**
Naming, API envelopes, RFC 7807 errors, and WebSocket event patterns are consistent. DB PK naming is aligned to camelCase (`peerId`).

**Structure Alignment:**
Project structure supports boundaries and integration points (frontend/backend/daemon/image separation).

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
All FR categories map to modules and boundaries (deployment, interface config, peer/route CRUD, tunnels, monitoring, auth, API, security, docs).

**Non-Functional Requirements Coverage:**
Performance, security, reliability, and platform constraints are addressed through isolation model, daemon boundary, and packaging approach.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical decisions documented with explicit versions.

**Structure Completeness:**
Complete directory structure and integration boundaries defined.

**Pattern Completeness:**
Naming, formatting, communication, and process patterns are specified with examples.

### Gap Analysis Results

**Critical Gaps:** None

**Important Gaps:** None

**Nice-to-Have Gaps:**
- Consider adding example IPC payloads for daemon commands in future.

### Validation Issues Addressed

- DB naming conflict resolved: PKs are camelCase (`peerId`).
- Version verification completed using provided versions list.

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clear privileged daemon boundary for system ops
- Consistent API/UI/WS conventions
- Complete structure and requirement mapping

**Areas for Future Enhancement:**
- IPC command schema examples
- Version pinning in lockfiles

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
- Initialize frontend and backend scaffolds per starter commands

## Architecture Completion Summary

### Workflow Completion

**Architecture Decision Workflow:** COMPLETED ✅
**Total Steps Completed:** 8
**Date Completed:** 2026-01-23T18:57:16-0500
**Document Location:** _bmad-output/planning-artifacts/architecture.md

### Final Architecture Deliverables

**Complete Architecture Document**

- All architectural decisions documented with specific versions
- Implementation patterns ensuring AI agent consistency
- Complete project structure with all files and directories
- Requirements to architecture mapping
- Validation confirming coherence and completeness

**Implementation Ready Foundation**

- 5 architectural decision areas finalized
- 6 implementation pattern categories defined
- 3 main components specified (frontend, backend, image/packaging)
- 59 functional requirements fully supported

**AI Agent Implementation Guide**

- Technology stack with verified versions
- Consistency rules that prevent implementation conflicts
- Project structure with clear boundaries
- Integration patterns and communication standards

### Implementation Handoff

**For AI Agents:**
This architecture document is your complete guide for implementing Encryptor-Sim-BMAD. Follow all decisions, patterns, and structures exactly as documented.

**First Implementation Priority:**
Initialize frontend and backend scaffolds per starter commands.

**Development Sequence:**

1. Initialize project using documented starter template
2. Set up development environment per architecture
3. Implement core architectural foundations
4. Build features following established patterns
5. Maintain consistency with documented rules

### Quality Assurance Checklist

**✅ Architecture Coherence**

- [x] All decisions work together without conflicts
- [x] Technology choices are compatible
- [x] Patterns support the architectural decisions
- [x] Structure aligns with all choices

**✅ Requirements Coverage**

- [x] All functional requirements are supported
- [x] All non-functional requirements are addressed
- [x] Cross-cutting concerns are handled
- [x] Integration points are defined

**✅ Implementation Readiness**

- [x] Decisions are specific and actionable
- [x] Patterns prevent agent conflicts
- [x] Structure is complete and unambiguous
- [x] Examples are provided for clarity

### Project Success Factors

**Clear Decision Framework**
Every technology choice was made collaboratively with clear rationale, ensuring all stakeholders understand the architectural direction.

**Consistency Guarantee**
Implementation patterns and rules ensure that multiple AI agents will produce compatible, consistent code that works together seamlessly.

**Complete Coverage**
All project requirements are architecturally supported, with clear mapping from business needs to technical implementation.

**Solid Foundation**
The chosen starter template and architectural patterns provide a production-ready foundation following current best practices.

---

**Architecture Status:** READY FOR IMPLEMENTATION ✅

**Next Phase:** Begin implementation using the architectural decisions and patterns documented herein.

**Document Maintenance:** Update this architecture when major technical decisions are made during implementation.
