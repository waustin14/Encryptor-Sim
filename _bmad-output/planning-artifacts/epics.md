---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# Encryptor-Sim-BMAD - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Encryptor-Sim-BMAD, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Administrators can deploy the encryptor simulator as a qcow2 VM image in Cisco Modeling Labs
FR2: System can boot from power-off to web UI accessible state
FR3: Administrators can access emergency IP configuration via serial console
FR4: System can initialize with DHCP-assigned MGMT interface IP address
FR5: Administrators can configure CT interface IP address, netmask, and gateway
FR6: Administrators can configure PT interface IP address, netmask, and gateway
FR7: Administrators can configure MGMT interface IP address, netmask, and gateway
FR8: Administrators can view current interface configuration for all three interfaces (CT/PT/MGMT)
FR9: System can enforce that CT, PT, and MGMT interfaces operate in isolated network namespaces
FR10: Administrators can create new IPsec peer configurations
FR11: Administrators can specify peer remote IP address (CT interface of remote encryptor)
FR12: Administrators can specify peer authentication method (PSK for V1.0)
FR13: Administrators can configure peer IKE version (IKEv1 or IKEv2)
FR14: Administrators can view list of all configured peers
FR15: Administrators can edit existing peer configurations
FR16: Administrators can delete peer configurations
FR17: Administrators can configure IPsec parameters per peer (DPD timers, keepalive settings, rekeying intervals)
FR18: Administrators can create routes associated with specific peers
FR19: Administrators can specify destination network CIDR for each route
FR20: Administrators can view all configured routes
FR21: Administrators can view routes grouped by peer
FR22: Administrators can edit existing route configurations
FR23: Administrators can delete routes
FR24: System can initiate IPsec tunnel establishment with configured peers
FR25: System can negotiate IKEv2 security associations
FR26: System can negotiate IKEv1 security associations
FR27: System can authenticate peers using pre-shared keys (PSK)
FR28: System can maintain multiple concurrent active tunnels (minimum 50)
FR29: System can automatically handle tunnel rekeying
FR30: System can detect dead peers and mark tunnels as down
FR31: Administrators can view real-time tunnel status (up/down/negotiating) for all configured peers
FR32: Administrators can view interface statistics (bytes tx/rx, packets tx/rx, errors) for CT/PT/MGMT interfaces
FR33: System can push tunnel state changes to web UI without manual refresh
FR34: System can push interface statistics updates to web UI at regular intervals
FR35: Administrators can view tunnel establishment time for active tunnels
FR36: Administrators can identify which tunnels are currently passing traffic
FR37: Administrators can log in to web UI using username and password
FR38: System can require administrators to change default password on first login
FR39: System can enforce minimum password complexity requirements
FR40: System can issue JWT tokens upon successful authentication
FR41: System can restrict web UI and API access to authenticated users only
FR42: Administrators can log out of web UI
FR43: Automation tools can authenticate to the API using same credentials as web UI
FR44: Automation tools can create peer configurations via REST API
FR45: Automation tools can create route configurations via REST API
FR46: Automation tools can query tunnel status via REST API
FR47: Automation tools can query interface statistics via REST API
FR48: Automation tools can update interface configurations via REST API
FR49: Automation tools can delete peers and routes via REST API
FR50: Developers can access auto-generated OpenAPI documentation
FR51: System can enforce that PT network traffic cannot route directly to CT network
FR52: System can enforce that only IKE (UDP 500/4500) and ESP (protocol 50) traffic passes between PT and CT namespaces
FR53: System can execute automated isolation validation tests on startup
FR54: System can display isolation test results to administrators
FR55: System can encrypt PSKs at rest in configuration database
FR56: Users can access user guide documentation
FR57: Users can access architecture documentation describing three-domain isolation model
FR58: Users can access ports and protocols reference documentation
FR59: Users can access published security validation report

### NonFunctional Requirements

NFR1: (Performance) System shall boot from power-off to web UI accessible state in < 30 seconds
NFR2: (Performance) System shall initialize all three network namespaces within boot sequence
NFR3: (Performance) Initial page load shall complete in < 2 seconds from cold start
NFR4: (Performance) Dashboard shall render 50 peers and 150 routes without perceptible lag
NFR5: (Performance) User interface interactions shall provide feedback within < 100ms
NFR6: (Performance) Interface statistics shall update via WebSocket at 1-2 second intervals
NFR7: (Performance) Tunnel state changes shall push to web UI immediately (< 1 second from state change)
NFR8: (Performance) System shall support up to 10 concurrent WebSocket connections without degradation
NFR9: (Performance) System shall support minimum 10 Mbps throughput per active tunnel
NFR10: (Performance) System shall establish tunnels from configuration to "UP" state in < 5 minutes (user-facing goal)
NFR11: (Security) PT network traffic shall be physically unable to route directly to CT network (namespace boundary enforcement)
NFR12: (Security) Only IKE (UDP 500/4500) and ESP (protocol 50) traffic shall pass between PT and CT namespaces
NFR13: (Security) Automated isolation validation tests shall execute on every system boot
NFR14: (Security) System shall display red banner in web UI if isolation validation fails
NFR15: (Security) Web UI and API shall be accessible only via HTTPS on MGMT interface
NFR16: (Security) System shall enforce minimum 8-character password complexity
NFR17: (Security) System shall force password change on first login from default credentials
NFR18: (Security) JWT tokens shall expire after 1 hour (access token) and 7 days (refresh token)
NFR19: (Security) Pre-shared keys (PSKs) shall be encrypted at rest in SQLite database
NFR20: (Security) SQLite database file shall have 600 permissions (root-only access)
NFR21: (Security) Web UI shall store JWT in memory only (not localStorage)
NFR22: (Security) System shall complete internal security testing (nmap, OWASP ZAP, SQL injection testing) before V1.0 release
NFR23: (Security) Security test results shall be published in public security report
NFR24: (Security) System shall have zero critical security vulnerabilities at V1.0 launch
NFR25: (Reliability) System shall boot reliably in CML environment without manual intervention
NFR26: (Reliability) System shall maintain active tunnels across configuration changes (no unnecessary tunnel flapping)
NFR27: (Reliability) Web UI shall automatically reconnect WebSocket connections on disconnect with exponential backoff
NFR28: (Reliability) System shall support minimum 50 concurrent peer configurations
NFR29: (Reliability) System shall support minimum 150 route configurations
NFR30: (Reliability) System shall consume < 2GB RAM under 50-peer load
NFR31: (Reliability) System shall maintain stable operation for 30+ days continuous uptime
NFR32: (Reliability) Configuration changes shall be atomic (old config remains until new validates)
NFR33: (Reliability) SQLite database shall provide ACID guarantees for all transactions
NFR34: (Reliability) System shall not lose configuration data on unplanned shutdown
NFR35: (Maintainability) Backend code shall follow PEP 8 Python style guidelines
NFR36: (Maintainability) Frontend code shall use ESLint with standard React rules
NFR37: (Maintainability) All public API endpoints shall have auto-generated OpenAPI documentation
NFR38: (Maintainability) User guide shall include screenshots and step-by-step workflows
NFR39: (Maintainability) Architecture documentation shall describe three-domain isolation model with diagrams
NFR40: (Maintainability) Ports/protocols reference shall list all network services with purpose and security implications
NFR41: (Maintainability) Codebase shall use popular tech stack (Python/React/strongSwan) to enable community contributions
NFR42: (Maintainability) GitHub repository shall include contribution guidelines and code of conduct
NFR43: (Maintainability) Project shall maintain < 48 hour average response time to GitHub issues during active development
NFR44: (Platform) qcow2 image shall be < 500MB compressed
NFR45: (Platform) System shall run on Alpine Linux 3.19+ (musl libc)
NFR46: (Platform) System shall import into CML via drag-and-drop without modification
NFR47: (Platform) System shall operate within 2 vCPU minimum, 4 vCPU maximum allocation
NFR48: (Platform) System shall operate within 1GB RAM minimum allocation
NFR49: (Platform) Web UI shall function in latest stable versions of Chrome, Firefox, Edge, and Safari
NFR50: (Platform) Web UI shall target desktop/laptop displays (1024px+ width)
NFR51: (Platform) Web UI shall not require mobile device support

### Additional Requirements

- Starter template: Vite React TypeScript frontend + FastAPI backend; initialize with `npm create vite@latest frontend -- --template react-ts` and `python -m venv .venv` plus FastAPI install; project initialization is the first implementation story.
- Project layout: separate `frontend/` and `backend/` top-level directories with layered frontend structure shown in architecture.
- Data architecture: SQLite + SQLAlchemy ORM + Pydantic + Alembic; no caching initially.
- Privileged operations: backend app communicates with a local daemon over Unix socket for strongSwan, nftables, and namespace operations.
- API/Realtime: REST + WebSocket; success envelope `{ data, meta }`; RFC 7807 error format; event payloads `{ type, data }` with dot-notation event names.
- Auth/security: JWT access and refresh tokens, admin-only for V1.0, argon2id password hashing, PSKs encrypted at app layer, HTTPS-only on MGMT.
- Frontend: Zustand state management and React Router; proactive performance optimization.
- Logging: structured logs with rotation.
- Configuration: `.env` for dev; appliance config at `/etc/<app>/config.yaml` for runtime.

### FR Coverage Map

### FR Coverage Map

FR1: Epic 2 - Deployment & Boot Readiness
FR2: Epic 2 - Deployment & Boot Readiness
FR3: Epic 2 - Deployment & Boot Readiness
FR4: Epic 2 - Deployment & Boot Readiness
FR5: Epic 4 - Configure Interfaces, Peers, and Routes
FR6: Epic 4 - Configure Interfaces, Peers, and Routes
FR7: Epic 4 - Configure Interfaces, Peers, and Routes
FR8: Epic 4 - Configure Interfaces, Peers, and Routes
FR9: Epic 4 - Configure Interfaces, Peers, and Routes
FR10: Epic 4 - Configure Interfaces, Peers, and Routes
FR11: Epic 4 - Configure Interfaces, Peers, and Routes
FR12: Epic 4 - Configure Interfaces, Peers, and Routes
FR13: Epic 4 - Configure Interfaces, Peers, and Routes
FR14: Epic 4 - Configure Interfaces, Peers, and Routes
FR15: Epic 4 - Configure Interfaces, Peers, and Routes
FR16: Epic 4 - Configure Interfaces, Peers, and Routes
FR17: Epic 4 - Configure Interfaces, Peers, and Routes
FR18: Epic 4 - Configure Interfaces, Peers, and Routes
FR19: Epic 4 - Configure Interfaces, Peers, and Routes
FR20: Epic 4 - Configure Interfaces, Peers, and Routes
FR21: Epic 4 - Configure Interfaces, Peers, and Routes
FR22: Epic 4 - Configure Interfaces, Peers, and Routes
FR23: Epic 4 - Configure Interfaces, Peers, and Routes
FR24: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR25: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR26: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR27: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR28: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR29: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR30: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR31: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR32: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR33: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR34: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR35: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR36: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR37: Epic 3 - Secure Admin Access
FR38: Epic 3 - Secure Admin Access
FR39: Epic 3 - Secure Admin Access
FR40: Epic 3 - Secure Admin Access
FR41: Epic 3 - Secure Admin Access
FR42: Epic 3 - Secure Admin Access
FR43: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR44: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR45: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR46: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR47: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR48: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR49: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR50: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR51: Epic 1 - Isolation & Security Assurance
FR52: Epic 1 - Isolation & Security Assurance
FR53: Epic 1 - Isolation & Security Assurance
FR54: Epic 1 - Isolation & Security Assurance
FR55: Epic 1 - Isolation & Security Assurance
FR56: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR57: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR58: Epic 5 - Tunnel Operations, Monitoring, Automation, and Docs
FR59: Epic 1 - Isolation & Security Assurance

## Epic List

### Epic 1: Isolation & Security Assurance
Users can trust the appliance enforces strict PT/CT separation and publishes security validation results.
**FRs covered:** FR51, FR52, FR53, FR54, FR55, FR59

### Epic 2: Deployment & Boot Readiness
Users can deploy the qcow2 in CML, boot successfully, and reach the system for initial setup.
**FRs covered:** FR1, FR2, FR3, FR4

### Epic 3: Secure Admin Access
Admins can securely access the UI/API and manage credentials for first-time use.
**FRs covered:** FR37, FR38, FR39, FR40, FR41, FR42

### Epic 4: Configure Interfaces, Peers, and Routes
Admins can configure interfaces and create/manage peers and routes to define connectivity.
**FRs covered:** FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23

### Epic 5: Tunnel Operations, Monitoring, Automation, and Docs
Users can bring tunnels up, monitor status, automate via API, and access documentation to validate connectivity.
**FRs covered:** FR24, FR25, FR26, FR27, FR28, FR29, FR30, FR31, FR32, FR33, FR34, FR35, FR36, FR43, FR44, FR45, FR46, FR47, FR48, FR49, FR50, FR56, FR57, FR58

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: Isolation & Security Assurance

Users can trust the appliance enforces strict PT/CT separation and publishes security validation results.

### Story 1.1: Initialize Project from Starter Template

As a developer,
I want to initialize the project using the approved starter templates,
So that the codebase follows the architectural foundation from the start.

**Acceptance Criteria:**

**Given** the project repository is ready for initialization
**When** I scaffold the frontend with the Vite React TypeScript template and create the FastAPI backend environment
**Then** the `frontend/` and `backend/` directories exist with their baseline scaffolds (FR1)
**And** the project structure aligns with the architecture starter template decision (FR1)

### Story 1.2: Enforce Isolation Rules and Secure PSKs

As an administrator,
I want strict PT/CT traffic isolation with PSKs encrypted at rest,
So that the simulator prevents cross-domain leakage and protects secrets.

**Acceptance Criteria:**

**Given** the appliance is running with CT/PT/MGMT namespaces
**When** PT traffic attempts to route directly to CT
**Then** the traffic is blocked and does not reach CT (FR51)
**And** only IKE (UDP 500/4500) and ESP (protocol 50) are permitted between PT and CT (FR52)
**And** PSKs are stored encrypted at rest in the configuration database (FR55)

### Story 1.3: Isolation Validation on Startup with UI Status

As an administrator,
I want automated isolation validation tests on startup with visible results,
So that I can confirm isolation is working before use.

**Acceptance Criteria:**

**Given** the system boots
**When** isolation validation tests execute
**Then** test results are recorded and visible to administrators (FR54)
**And** a red banner is displayed in the UI when isolation validation fails (FR54)
**And** isolation validation tests execute on startup (FR53)

### Story 1.4: Security Testing and Published Report

As a security reviewer,
I want security testing performed with a published report,
So that the simulator is transparently validated and free of critical vulnerabilities.

**Acceptance Criteria:**

**Given** pre-release security testing is completed (nmap, OWASP ZAP, SQL injection)
**When** results are compiled
**Then** a public security report is published (FR59)
**And** the report indicates zero critical vulnerabilities at V1.0 launch (FR59)

## Epic 2: Deployment & Boot Readiness

Users can deploy the qcow2 in CML, boot successfully, and reach the system for initial setup.

### Story 2.1: Deploy qcow2 Appliance in CML

As an administrator,
I want to deploy the qcow2 image in Cisco Modeling Labs,
So that I can add the simulator to my topology.

**Acceptance Criteria:**

**Given** I have the qcow2 image
**When** I import it into CML and instantiate a node
**Then** the node boots successfully and exposes the MGMT interface (FR1)
**And** the appliance is compatible with drag-and-drop import (FR1)

### Story 2.2: Boot With Required Services Running

As an administrator,
I want the appliance to boot with all required services running,
So that the system is ready for configuration immediately.

**Acceptance Criteria:**

**Given** the appliance powers on
**When** the boot sequence completes
**Then** required services (API, Web UI, isolation checks, daemon) are running (FR2)
**And** the system reaches an HTTP(S)-reachable state for the management interface (FR2)

### Story 2.3: MGMT Interface DHCP Initialization

As an administrator,
I want the MGMT interface to pull an IP address using DHCP,
So that I can access the UI without manual network setup.

**Acceptance Criteria:**

**Given** a DHCP server is reachable on the MGMT network
**When** the appliance boots
**Then** the MGMT interface obtains an IP address via DHCP (FR4)
**And** the assigned IP is available for use by the Web UI and API (FR4)

### Story 2.4: Serial Console MGMT Configuration

As an administrator,
I want to configure the MGMT interface via serial console,
So that I can recover access when DHCP is unavailable.

**Acceptance Criteria:**

**Given** the appliance is running with serial console access
**When** I set a static IP, netmask, and gateway for MGMT
**Then** the configuration is applied and persists across reboots (FR3)

### Story 2.5: Boot Health Indicator via API

As an administrator,
I want a boot-time health indicator available via the API,
So that I can confirm system readiness and boot timing.

**Acceptance Criteria:**

**Given** the appliance has completed boot
**When** I query the health/status endpoint
**Then** I receive service readiness status and boot duration (FR2)
**And** boot duration indicates whether the <30s target was met (FR2)

## Epic 3: Secure Admin Access

Admins can securely access the UI/API and manage credentials for first-time use.

### Story 3.1: Default Admin Login

As an administrator,
I want to access the management interface with default credentials,
So that I can sign in on first use.

**Acceptance Criteria:**

**Given** the appliance is running and reachable on MGMT
**When** I log in with the default username and password
**Then** I am authenticated and can access the UI (FR37)
**And** access is restricted to authenticated users only (FR41)
**And** I can log out to end my session (FR42)

### Story 3.2: Forced Password Change on First Login

As an administrator,
I want to be required to change the default password on first login,
So that default credentials are not retained.

**Acceptance Criteria:**

**Given** I authenticate with default credentials
**When** I attempt to proceed past initial login
**Then** I am prompted to change the password (FR38)
**And** the new password must meet minimum complexity requirements (FR39)

### Story 3.3: HTTPS with TLS 1.2+ Self-Signed Cert

As an administrator,
I want the management interface to use HTTPS with TLS 1.2+ and a self-signed certificate,
So that management traffic is encrypted.

**Acceptance Criteria:**

**Given** I access the UI or API over MGMT
**When** a TLS session is established
**Then** the connection uses TLS 1.2 or higher (FR41)
**And** the certificate is self-signed and presented by the appliance (FR41)

### Story 3.4: API Authentication with JWT

As an automation user,
I want to authenticate to the API and receive a JWT,
So that I can make authenticated API calls.

**Acceptance Criteria:**

**Given** valid admin credentials
**When** I authenticate via the API
**Then** I receive a JWT access token (FR40)
**And** the API accepts the same credentials as the web UI (FR43)
**And** the token can be used to access protected API endpoints (FR41)

## Epic 4: Configure Interfaces, Peers, and Routes

Admins can configure interfaces and create/manage peers and routes to define connectivity.

### Story 4.1: Configure and View Interface Settings

As an administrator,
I want to configure and view CT/PT/MGMT interface settings,
So that the simulator's network interfaces are correctly defined.

**Acceptance Criteria:**

**Given** I am authenticated
**When** I set IP address, netmask, and gateway for CT, PT, and MGMT
**Then** the settings are saved and applied (FR5, FR6, FR7)
**And** I can view the current configuration for all three interfaces (FR8)
**And** CT, PT, and MGMT interfaces operate in isolated network namespaces (FR9)

### Story 4.2: Add IPsec Peer

As an administrator,
I want to create an IPsec peer with required parameters,
So that the simulator can establish a tunnel.

**Acceptance Criteria:**

**Given** I am authenticated
**When** I create a peer with remote IP, PSK, and IKE version
**Then** the peer is saved and appears in the peer list (FR10, FR11, FR12, FR13, FR14)
**And** I can configure per-peer IPsec parameters (DPD, keepalive, rekey) (FR17)
**And** I can edit existing peer configurations (FR15)

### Story 4.3: Delete IPsec Peer

As an administrator,
I want to delete an IPsec peer,
So that obsolete peers are removed from configuration.

**Acceptance Criteria:**

**Given** an existing peer configuration
**When** I delete the peer
**Then** the peer is removed from the peer list (FR16)
**And** associated configuration is removed (FR16)

### Story 4.4: Add Route for a Peer

As an administrator,
I want to create routes associated with a peer,
So that traffic is directed through the correct tunnel.

**Acceptance Criteria:**

**Given** an existing peer
**When** I add a route with a destination CIDR tied to that peer
**Then** the route is saved (FR18, FR19)
**And** I can view all configured routes and routes grouped by peer (FR20, FR21)
**And** I can edit existing route configurations (FR22)

### Story 4.5: Delete Route

As an administrator,
I want to delete a configured route,
So that stale routes are removed.

**Acceptance Criteria:**

**Given** an existing route
**When** I delete the route
**Then** the route is removed from the route list (FR23)

### Story 4.6: Confirm Peer Operational State

As an administrator,
I want to see whether a configured peer is operational,
So that I can verify configuration correctness before tunnel testing.

**Acceptance Criteria:**

**Given** a configured peer
**When** I view the peer list
**Then** I can see the peer's operational status (configured/ready) (FR14)
**And** peers with missing required fields are flagged as incomplete (FR14)

## Epic 5: Tunnel Operations, Monitoring, Automation, and Docs

Users can bring tunnels up, monitor status, automate via API, and access documentation to validate connectivity.

### Story 5.1: Tunnel Status and Interface Statistics

As an administrator,
I want real-time tunnel status and interface statistics,
So that I can monitor operational health.

**Acceptance Criteria:**

**Given** tunnels and interfaces are configured
**When** I view the dashboard
**Then** I see tunnel status (up/down/negotiating) for all peers (FR31)
**And** I see CT/PT/MGMT interface statistics (bytes/packets/errors) (FR32)
**And** status/statistics update without manual refresh (FR33, FR34)

### Story 5.2: Dynamically Add Tunnels

As an administrator,
I want to bring up tunnels for newly configured peers,
So that I can add connectivity without rebooting.

**Acceptance Criteria:**

**Given** a new peer is configured
**When** I initiate tunnel establishment
**Then** the system negotiates IKEv1/IKEv2 and authenticates via PSK (FR25, FR26, FR27)
**And** the tunnel becomes active without requiring a reboot (FR24)
**And** the system supports multiple concurrent active tunnels (FR28)
**And** tunnel rekeying is handled automatically (FR29)

### Story 5.3: Dynamically Remove Tunnels

As an administrator,
I want to tear down tunnels for removed peers,
So that obsolete connectivity is removed cleanly.

**Acceptance Criteria:**

**Given** an active tunnel
**When** the associated peer is deleted or disabled
**Then** the tunnel is torn down (FR30)
**And** the system releases related resources (FR30)

### Story 5.4: Validate Tunnel Traffic Flow

As an administrator,
I want to confirm tunnels are passing traffic,
So that I can validate CT-CT and PT-host connectivity.

**Acceptance Criteria:**

**Given** a tunnel is active
**When** I check tunnel traffic indicators
**Then** I can see which tunnels are passing traffic (FR36)
**And** tunnel establishment time is visible for active tunnels (FR35)

### Story 5.5: Operational REST API for Automation

As an automation user,
I want a working REST API to manage peers, routes, interfaces, and status,
So that I can automate configuration at scale.

**Acceptance Criteria:**

**Given** I am authenticated
**When** I call the API to create/update/delete peers and routes
**Then** the operations succeed and reflect in the UI (FR44, FR45, FR48, FR49)
**And** I can query tunnel status and interface statistics via the API (FR46, FR47)

### Story 5.6: Complete API and User Documentation

As a user,
I want complete API and user documentation available,
So that I can understand configuration, ports/protocols, and usage.

**Acceptance Criteria:**

**Given** I access the documentation area
**When** I open the docs
**Then** I can access the user guide, API reference, and ports/protocols documentation (FR56, FR57, FR58)
**And** the API documentation is auto-generated and current (FR50)
