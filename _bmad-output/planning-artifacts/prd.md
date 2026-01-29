---
stepsCompleted: ['step-01-init', 'step-01b-continue', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments:
  - '_bmad-output/analysis/brainstorming-session-2026-01-23.md'
workflowType: 'prd'
date: '2026-01-23'
briefCount: 0
researchCount: 0
brainstormingCount: 1
projectDocsCount: 0
classification:
  projectType: 'Network Virtual Appliance (web-administered)'
  domain: 'GovTech'
  complexity: 'high'
  projectContext: 'greenfield'
---

# Product Requirements Document - Encryptor-Sim-BMAD

**Author:** Will
**Date:** 2026-01-23

## Executive Summary

This PRD defines a virtual network appliance that simulates the role of a TACLANE encryptor in high-security government networks, enabling realistic lab testing without physical hardware.

**Target Users:** Government network engineers, network vendor sales engineers, and solution architects who need to validate designs, demos, and interoperability in controlled lab environments.

**Key Differentiator:** No realistic simulator exists today. Teams must approximate encryptors with routers or firewalls, a process that is tedious, error-prone, and does not faithfully reproduce TACLANE behavior.

The success criteria below define measurable outcomes across user, business, and technical dimensions.

## Success Criteria

### User Success

**Primary Success Moment:** Network engineer drags TACLANE simulator into CML topology, configures first peer, and establishes working tunnel in **< 5 minutes** (excluding boot time). User experiences relief that the simulation is realistic without burdensome configuration.

**User Emotional State:** Relief—they can stop worrying about emulating the encryptor and focus on testing their actual solution (SD-WAN, zero-trust, emerging technologies).

**Key User Outcomes:**
- Speed to realistic simulation without configuration burden
- Tunnel status clearly visible with "UP" confirmation
- User confidently moves on to testing their actual networking solution
- Professional interface they feel proud to demonstrate to customers

**Success Indicators:**
- First tunnel established in < 5 minutes
- User returns to use simulator for additional labs (not one-time usage)
- User recommends tool to colleagues

### Business Success

**12-Month Targets:**
- **Community Adoption:** 20-50 GitHub stars indicating market validation
- **Internal Usage:** 10-15 employees using simulator in their CML instances
- **Lab Integration:** Incorporated into key company demonstration labs
- **Credibility:** Increased mind share with government/military customers as experts in high-security networking

**Strategic Value:**
- Position company as deep experts in TACLANE/KG environments
- Enable employees to confidently discuss and recommend solutions incorporating encryptors
- Differentiate in government/military SD-WAN market
- Open-source community contribution builds goodwill and adoption

**What "Worth It" Means:**
- Company recognized for understanding high-security network requirements
- Engineers cite this tool in customer conversations
- Community maintains and extends beyond initial release

### Technical Success

**Core Requirements:**
- Boots reliably in Cisco Modeling Labs (CML)
- Supports minimum 50 peers, 150 routes
- Isolation validation: PT→CT traffic provably blocked
- Resource efficiency: <2GB RAM usage
- Performance: Minimum 10 Mbps per tunnel throughput
- No critical security vulnerabilities

**Security Validation:**
- Internal security testing completed (nmap scan, OWASP ZAP, isolation tests, SQL injection testing)
- Test results transparently published with security report
- Users feel confident simulator behaves like real TACLANE/KG device
- Not production-classified-data ready, but realistic for lab simulation

**Platform Compatibility:**
- Alpine Linux qcow2 image runs in CML without modification
- Web interface works in modern browsers (Chrome, Firefox, Edge, Safari)
- IPv6 explicitly disabled (V1.0), documented for V2.0

### Measurable Outcomes

| Metric | Target | Timeline |
|--------|--------|----------|
| Time to first tunnel | < 5 minutes | V1.0 launch |
| GitHub stars | 20-50 stars | 12 months |
| Internal adoption | 10-15 users | 12 months |
| Peer capacity | 50+ peers supported | V1.0 launch |
| Route capacity | 150+ routes supported | V1.0 launch |
| RAM usage | < 2GB | V1.0 launch |
| Tunnel throughput | 10+ Mbps per tunnel | V1.0 launch |
| Security vulnerabilities | Zero critical | V1.0 launch |

## Product Scope

The scope below defines V1.0 delivery, near-term enhancements, and long-term vision.

### MVP - Minimum Viable Product (V1.0)

**Essential Features - Required for proving value:**
- **Three-domain isolation:** Network namespaces (CT, PT, MGMT) with nftables enforcement
- **IPsec tunneling:** strongSwan (IKEv2/IKEv1 support, PSK authentication only)
- **Backend:** Python FastAPI + SQLite for configuration storage
- **Frontend:** React + Chakra UI (basic interface, no charts initially)
- **Authentication:** Basic JWT auth (single admin account, RBAC deferred)
- **Core operations:** CRUD for peers, routes, interfaces
- **Real-time monitoring:** WebSocket for live tunnel/interface status
- **Deployment:** Alpine Linux qcow2 image for CML
- **IPv6 handling:** Explicitly disabled via kernel parameter
- **Security transparency:** Published security report with test results
- **Documentation:** Ports/protocols reference, architecture docs

**Success bar for V1.0:** Network engineer can deploy, configure tunnels faster than manual router setup, and confidently demonstrate to customers.

### Growth Features (V1.5/V2.0)

**V1.x Enhancements:**
- Role-based access control (RBAC) - admin/read-only roles
- Health check diagnostics - automated troubleshooting assistance
- Recharts visualizations - bandwidth/utilization graphs
- Configuration snapshots - rollback capability
- Web log viewer - human-readable + raw mode
- Search functionality - global search across peers/routes
- Day-zero provisioning - YAML config via virtual CD-ROM
- Telemetry export - Syslog/gRPC/OpenTelemetry for NOC integration

**Rationale for deferral:** These enhance usability and operational maturity but aren't essential for proving core value (realistic encryptor simulation).

### Vision (V2.0+)

**Advanced Capabilities:**
- **IPv6 full support** - dual-stack CT/PT interfaces
- **Certificate authentication** - X.509 certs, CA trust chains, P12 import
- **Advanced diagnostics** - packet capture, traffic generation, performance metrics
- **Multi-encryptor coordination** - mesh topology automation
- **Community features** - topology sharing, configuration templates
- **Compliance reporting** - audit logs, security posture dashboards

**Strategic Vision:** Become the de facto standard for simulating high-security network devices in virtual lab environments, enabling testing of any emerging technology in contexts where encryptors are part of the infrastructure.

## User Journeys

The journeys below ground requirements in real scenarios and stakeholder goals.

### Ronnie - Network Engineer: "The Optimization Problem"

**Opening Scene:** Ronnie, an Army network engineer, sits at his desk staring at a complex CML topology - multiple DMVPN spokes, hub routers, and a big gap where the TACLANE should be. He's supposed to optimize routing behavior, but without the encryptor in the lab, his tests are meaningless. He's tried faking it with routers configured as IPsec endpoints, but it took him 3 hours last time and still didn't behave like the real thing. He's frustrated.

**Rising Action:** He discovers the TACLANE simulator. Downloads the qcow2 image, imports it into CML. Drags the encryptor into his topology between the CT and PT networks. Opens the web interface, creates peer configurations for his hub and spoke tunnels.

**Climax:** Four minutes later, tunnels show "UP" with green status indicators. His DMVPN traffic is flowing through the encryptor realistically. He can finally test his routing optimizations against actual encryptor behavior.

**Resolution:** Over the next few days, Ronnie tests multiple routing configurations. He identifies the optimal design, validates it behaves correctly with the encryptor in the path, and confidently recommends the change to his commander. The optimization gets deployed to production, and Ronnie knows it'll work because he tested it properly.

**Emotional arc:** Frustration → Relief → Confidence → Success

---

### Mark - Sales Engineer: "The Pre-Flight Check"

**Opening Scene:** Mark, a network vendor sales engineer, has a demo scheduled in two weeks for a government customer evaluating SD-WAN for their classified network. They specifically asked, "How does this work with TACLANEs?" Mark's done demos before where he showed up, started configuring on-site, and hit unexpected issues - tunnel flapping, routing loops, protocol incompatibilities. The customer watched him troubleshoot for 45 minutes. Awkward. He didn't win that one. This time needs to be different.

**Rising Action:** One week before the demo, Mark builds the complete topology in CML at his office - SD-WAN controllers, edge routers, and the TACLANE simulator positioned exactly where the customer's real encryptors sit. He configures the encryptor, establishes tunnels, runs traffic. He discovers a routing issue with the SD-WAN overlay - fixes it now, in private. He validates every failure scenario: tunnel down, interface flap, peer unreachable. Everything works.

**Climax:** Demo day. Mark connects to his pre-built CML environment remotely. Brings up the dashboard. "Here's your network with TACLANEs in place." Tunnels are green, traffic flows, SD-WAN overlay adapts to encryptor behavior perfectly. Customer asks "What happens if a tunnel fails?" Mark triggers a failure, SD-WAN reroutes instantly. Customer sees it work in their context.

**Resolution:** Customer says "This actually addresses our concern. Let's move to pilot phase." Mark leaves with next steps committed. The demo succeeded because he practiced with realistic infrastructure.

**Emotional arc:** Anxiety (past failures) → Control (pre-validation) → Confidence (flawless demo) → Professional success (deal progression)

---

### Jenny - Solution Architect: "Design Validation Before Commitment"

**Opening Scene:** Jenny, a solution architect for a large systems integrator, is three weeks from formal multi-vendor integration testing for a major government network project. The test environment costs $50K+ to stand up and requires coordinating multiple vendors, government stakeholders, and a test facility. If her design has issues during formal testing, she's looking at schedule delays, budget overruns, and very uncomfortable meetings with the program manager. She's done this before - going into formal testing hoping everything works. She needs more confidence this time.

**Rising Action:** Jenny builds three design variations in CML - different routing protocols (BGP vs OSPF), different failover strategies, all with TACLANE simulators positioned where the real encryptors will be in production. She tests vendor interoperability: Cisco routers + Juniper firewalls + Palo Alto security stack, all talking through the encryptor. She runs failure scenarios: What happens when a tunnel goes down? Does the routing protocol reconverge properly through the encryptor? Does the multi-vendor environment handle it gracefully?

**Climax:** During testing, Jenny discovers that one vendor's default IPsec keepalive timer conflicts with the encryptor's dead peer detection settings - tunnels flap unnecessarily under certain conditions. She catches this in her lab, adjusts the design parameters, re-validates. Issue solved before formal testing even starts.

**Resolution:** Jenny enters the formal integration test with a validated design. No surprises. Multi-vendor environment works on first attempt. Formal testing completes on schedule. Program manager is happy, timeline holds, Jenny's design credibility is reinforced. She used the simulator to de-risk expensive formal testing.

**Emotional arc:** Pressure (expensive testing looming) → Methodical exploration → Discovery (caught interop issue early) → Relief (avoided formal test failure) → Professional confidence (design proven sound)

---

### Theresa - Automation Developer: "From Manual Tedium to Topology Automation"

**Opening Scene:** Theresa, a lab engineer focused on automation, has deployed the encryptor simulator manually a dozen times in the past month. Every new lab requires standing up pairs of encryptors - configure peer A, configure peer B, establish tunnel. For a simple hub-and-spoke with 5 spokes, that's 5 tunnels to manually configure through the web UI. For a full mesh with 6 encryptors, that's 15 tunnels (N*(N-1)/2). She's clicking through the same forms over and over. The encryptors work great, but the manual configuration is tedious and error-prone. She knows there has to be a better way.

**Rising Action:** Theresa discovers the REST API documentation. She writes a basic Python script that takes input parameters (CT IPs, PT IPs, subnets) and configures two encryptors as a pair via API calls. She tests it - what took 10 minutes of clicking now takes 30 seconds. This works. She sees the potential.

**Climax:** Theresa enhances the script. New version takes topology type as input: "full-mesh" or "hub-spoke". For full mesh, it calculates all peer relationships automatically and configures every encryptor to talk to every other encryptor. For hub-spoke, it designates one as hub and configures spoke-to-hub tunnels. She feeds it a YAML file with 8 encryptors and topology type "full-mesh" - the script generates 28 tunnel configurations across all devices in under 2 minutes. What would have taken her 2+ hours manually is now automated.

**Resolution:** Theresa publishes her script to the internal team repository. Other lab engineers start using it. Lab deployment time drops dramatically. When business requirements change and they need to re-deploy labs frequently, Theresa's automation makes it painless. The encryptor simulator went from useful tool to critical infrastructure because the API enabled programmatic control at scale.

**Emotional arc:** Tedium (manual repetition) → Discovery (API potential) → Creative satisfaction (solving the problem) → Pride (enabling team efficiency)

---

### Journey Requirements Summary

These four journeys reveal distinct capability requirements:

**From Ronnie (Network Engineer - Testing/Optimization):**
- Quick deployment into CML (qcow2 format, drag-and-drop)
- Simple, intuitive peer configuration interface
- Clear tunnel status visualization (green "UP" indicators)
- Multi-peer support for complex topologies (DMVPN hub + multiple spokes)
- Realistic encryptor behavior matching real TACLANE devices
- Fast time-to-tunnel (< 5 minutes target)

**From Mark (Sales Engineer - Customer Demos):**
- Pre-deployment validation and testing capability
- Failure scenario simulation (trigger tunnel down, interface flap for demo purposes)
- Dashboard suitable for customer-facing demonstrations
- Remote access compatibility with CML environments
- Reliable, repeatable behavior under demo conditions
- Professional interface appropriate for government customer presentations

**From Jenny (Solution Architect - Design Validation):**
- Multi-vendor interoperability (works with Cisco, Juniper, Palo Alto, etc.)
- Configurable IPsec parameters (timers, dead peer detection, keepalives)
- Failure mode testing and validation
- Design iteration capability (test multiple configurations)
- Support for complex routing protocols flowing through encryptor
- Parameter tuning for protocol compatibility

**From Theresa (Automation Developer - API-Driven Scale):**
- Robust REST API for programmatic control
- Peer and tunnel configuration via API calls
- Bulk operations support for multi-encryptor deployments
- Comprehensive API documentation
- Configuration-as-code compatibility (YAML/JSON input)
- Topology pattern support (full mesh, hub-spoke calculations)

**Cross-Journey Requirements:**
- **Reliability:** All users need the simulator to behave predictably and consistently
- **Security isolation:** All users implicitly trust PT/CT/MGMT separation works correctly
- **Performance:** Must handle realistic traffic loads and tunnel counts
- **Documentation:** Different users need different docs (user guides, API reference, architecture)

## Domain-Specific Requirements

This section clarifies GovTech constraints, applicability, and exclusions for the simulator.

### Domain Context

This product operates in the **GovTech (Government Technology)** domain, serving government and military network engineers, sales engineers, and solution architects. While this domain typically carries heavy compliance and regulatory burdens, the specific nature of this simulator significantly reduces those requirements.

### Applicable Domain Constraints

**Core Requirement: TACLANE/KG Behavioral Fidelity**
- Simulator must behave realistically like actual TACLANE/KG encryptor devices
- Users (government/military personnel) must trust the simulation accuracy for lab testing
- Isolation model (CT/PT/MGMT separation) must be provably correct
- IPsec behavior must match real-world TACLANE implementations

**Security Validation & Transparency**
- Internal security testing with published results (nmap, OWASP ZAP, isolation validation)
- Transparent security reporting builds trust with security-conscious government users
- Open-source model allows independent security review
- Published architecture documentation enables validation

### Domain Constraints NOT Applicable (V1.0)

**Export Controls (ITAR/EAR):**
- Standard IPsec cipher suites under 250 Mbps are exempt from export controls
- Simulator does not incorporate controlled cryptographic hardware or classified algorithms
- Open-source distribution is permissible

**Government Procurement Requirements:**
- Open-source project, not entering formal government acquisition processes
- No FAR/DFARS compliance needed
- No FedRAMP authorization required (lab tool, not production cloud service)

**Section 508 Accessibility:**
- Not required for V1.0 lab simulator
- May be considered for future releases if government users specifically request
- Current web UI targets technical users (network engineers)

**Security Clearance Requirements:**
- Simulator handles no classified information
- Not intended for production use with classified data
- Lab/testing use only

### Risk Mitigations

**Credibility Risk:**
- Risk: Government users discover simulator doesn't behave like real TACLANE
- Mitigation: Rigorous validation, published security reports, transparency about limitations

**Security Perception Risk:**
- Risk: Users assume simulator has same security as real TACLANE hardware
- Mitigation: Clear documentation that this is for lab use only, not production classified networks

**Community Trust:**
- Risk: Government/military users skeptical of open-source security tools
- Mitigation: Professional security validation, transparent findings, open architecture

### Future Domain Considerations (V2.0+)

If adoption grows and government agencies request formal compliance:
- Section 508 accessibility compliance for web interface
- Common Criteria evaluation or NIST framework alignment
- Formal security certifications (if agencies require for lab tools)

**Key Principle:** Start with transparency and realistic behavior. Add formal compliance only if community adoption demands it.

## Innovation & Novel Patterns

Innovation analysis captures the differentiators and novel patterns that make this product unique.

### Detected Innovation Areas

**Primary Innovation: First Realistic Virtualized Encryptor Simulator**

This product creates an entirely new product category - **realistic TACLANE/KG encryptor simulation for virtual lab environments**. While generic IPsec implementations exist, no solution currently provides:

1. **Pre-built three-domain isolation architecture** (CT/PT/MGMT) that mirrors real encryptor hardware
2. **TACLANE-specific behavioral fidelity** beyond standard IPsec
3. **Virtualized form factor** for Cisco Modeling Labs deployment
4. **Open-source accessibility** for hardware that's export-controlled and unavailable

**Core Assumption Being Challenged:**

Traditional thinking: *"You need real TACLANE hardware to properly test networks with encryptors."*

This product proves: *"Software-based namespace isolation can realistically simulate hardware security boundaries well enough for meaningful lab testing."*

**Technical Innovation:**

- **Network namespace isolation** (ct-ns, pt-ns, mgmt-ns) provides software-based separation that mimics hardware domain isolation
- **Defense-in-depth enforcement** (namespace boundaries + nftables) ensures PT→CT traffic blocking even under misconfiguration
- **Controlled veth bridging** allows only IKE/ESP protocols between domains, replicating hardware restrictions in software

This is not just "IPsec in a VM" - it's **architectural simulation of security boundaries** that real encryptors enforce through hardware.

### Market Context & Competitive Landscape

**Current State:**

- **TACLANE/KG hardware**: Export-controlled, expensive, unavailable for public use or lab environments
- **Workaround solutions**: Manually configure generic routers/firewalls with IPsec (3+ hours, doesn't behave like real encryptors, error-prone)
- **Existing attempts**: No known successful virtualized encryptor solutions have gained traction

**Why This Innovation Matters:**

The gap between "need to test with encryptors" and "can't access encryptor hardware" has existed for years. Previous solutions failed likely due to:
- **Complexity**: Proper isolation and TACLANE-specific behavior is non-trivial
- **Niche audience**: Small user base (government/military network engineers) doesn't attract commercial investment
- **Domain expertise required**: Understanding real TACLANE behavior requires operational experience

This product succeeds where others haven't because:
- **Builder domain expertise**: Built by someone who has operated real TACLANEs and understands their role, behavior, and admin experience
- **Open source model**: Distributes development/maintenance burden across community
- **Realistic expectations**: Targeting lab simulation fidelity, not production-classified-data equivalence

**Democratizing Access:**

By creating an open-source simulator, this product makes encryptor testing accessible to:
- Network engineers without access to expensive hardware
- Educational institutions teaching IPsec and high-security networking
- Sales engineers demonstrating emerging technologies in secure contexts
- Solution architects validating designs before costly formal testing

### Validation Approach

**How We Know It Works:**

1. **Builder Domain Expertise**
   - Product built by engineer with operational TACLANE experience
   - Firsthand knowledge of device behavior, configuration workflows, and user expectations
   - Deep understanding of three-domain isolation requirements

2. **User Validation**
   - Government/military network engineers confirm realistic behavior
   - Feedback loop: "Does this match your experience with real TACLANEs?"
   - Community validation from users who operate actual encryptors

3. **Technical Validation**
   - Published isolation test results (PT→CT traffic provably blocked)
   - Security testing (nmap, OWASP ZAP, penetration testing)
   - Transparent documentation of architecture and limitations

4. **Iterative Refinement**
   - Continuous improvement based on user feedback
   - Community contributions from TACLANE operators
   - Transparent roadmap for addressing identified gaps

### Risk Mitigation

**Innovation Risk: Simulation Isn't Accurate Enough**

- **Risk**: Users discover simulator doesn't behave like real TACLANE in specific scenarios
- **Mitigation Strategy**:
  - **Transparency**: Clearly document known limitations and V1.0 scope
  - **Iterative improvement**: Address feedback that can be fixed through software
  - **Honest communication**: Acknowledge limitations that can't be addressed (e.g., hardware-specific behaviors)
  - **Community feedback loop**: GitHub issues for users to report behavioral discrepancies

**Adoption Risk: Community Doesn't Use It**

- **Risk**: Government engineers don't adopt simulator, it remains unused
- **Mitigation Strategy**:
  - **Internal value first**: Product delivers value to builder's company labs regardless of external adoption
  - **Realistic success metrics**: 10-15 internal users + 20-50 GitHub stars = success, not mass market
  - **Niche focus**: Deep value for those who need it > shallow value for many
  - **Low barrier to entry**: Free, open source, qcow2 format makes trying it frictionless

**Technical Risk: Isolation Model Has Flaws**

- **Risk**: PT→CT traffic leakage discovered post-launch = credibility disaster
- **Mitigation Strategy**:
  - **Pre-launch security validation**: Rigorous internal testing before public release
  - **Published security reports**: Transparent findings build trust
  - **Defense-in-depth architecture**: Multiple isolation layers (namespaces + nftables + veth restrictions)
  - **Open architecture**: Community can independently audit security model

**Sustainability Risk: Maintenance Burden Too High**

- **Risk**: Solo developer can't sustain long-term maintenance
- **Mitigation Strategy**:
  - **Community-maintained model**: Open source distributes burden after V1.0
  - **Clear V1.0 scope**: Ship focused MVP, defer enhancements to community
  - **Popular tech stack**: Python/React/strongSwan makes contributions accessible
  - **Internal company support**: Company benefits from tool, provides some ongoing support

**Key Innovation Principle:**

This isn't innovation for innovation's sake. It's **solving a real problem (no hardware access) with a novel approach (virtualized isolation) for an underserved niche (government/military network engineers)**. Success is measured by value delivered, not adoption scale.

## Network Virtual Appliance Specific Requirements

### Project-Type Overview

This is a **network virtual appliance** with dual interfaces: web-based administration UI for human operators and REST API for programmatic control. The appliance runs as a qcow2 VM image in Cisco Modeling Labs, simulating TACLANE/KG encryptor behavior with three isolated network domains (CT/PT/MGMT).

**Primary Interfaces:**
- **Web UI**: React single-page application for interactive configuration and monitoring
- **REST API**: Programmatic control for automation and bulk operations
- **Serial Console**: Emergency IP configuration access (restricted shell)

**Core Technical Challenge:** Provide real-time visibility into tunnel/interface state while maintaining security isolation between network domains.

### Technical Architecture Considerations

#### Web Interface Architecture

**Technology Stack:**
- **Frontend Framework**: React 18+ single-page application (SPA)
- **Component Library**: Chakra UI for modern, professional interface
- **State Management**: Zustand (lightweight, hook-based)
- **Build System**: Modern bundler (Vite or Create React App)

**Browser Support:**
- **Target Browsers**: Chrome, Firefox, Edge, Safari (latest stable versions)
- **Policy**: Support most recent stable release, no legacy browser compatibility
- **Rationale**: Network engineers use modern browsers, no enterprise legacy constraints

**Responsive Design:**
- **Target Devices**: Desktop and laptop only (1024px+ screen width)
- **No Mobile Support**: Network appliance administration requires full keyboard/mouse interface
- **Rationale**: CML environments accessed from workstations, not mobile devices

**Performance Requirements:**
- **Initial Page Load**: < 2 seconds from cold start
- **Dashboard Rendering**: Handle 50 peers + 150 routes without lag
- **Real-time Updates**: 1-2 second update interval for interface statistics
- **Tunnel State Changes**: Immediate updates (event-driven via WebSocket)
- **UI Responsiveness**: < 100ms interaction feedback for user actions

**Accessibility:**
- **V1.0 Scope**: No formal accessibility requirements (Section 508 compliance deferred)
- **Basic Usability**: Standard HTML semantics, keyboard navigation not prioritized
- **Future Consideration**: V2.0 may add Section 508 compliance if government agencies request

#### API Architecture

**REST API Design:**
- **Framework**: FastAPI (Python) with auto-generated OpenAPI documentation
- **Versioning**: API versioned from V1.0 (`/api/v1/peers`, `/api/v1/routes`, etc.)
- **Format**: JSON for all requests and responses
- **Documentation**: Auto-generated Swagger UI at `/api/docs`

**API Endpoints (Core V1.0):**
- `GET/POST /api/v1/peers` - Peer configuration management
- `GET/POST /api/v1/routes` - Route configuration management
- `GET/PATCH /api/v1/interfaces` - Interface configuration (CT/PT/MGMT)
- `GET /api/v1/status/tunnels` - Real-time tunnel status
- `GET /api/v1/status/interfaces` - Real-time interface statistics
- `POST /api/v1/auth/login` - JWT token acquisition
- `POST /api/v1/auth/refresh` - JWT token refresh

**Authentication Model:**
- **Method**: JWT (JSON Web Tokens) for both web UI and API
- **Unified Auth**: Same authentication mechanism for web and API (no separate API keys)
- **Token Storage**: Web UI stores JWT in memory (not localStorage for security)
- **Token Lifetime**: 1 hour access token, 7 day refresh token
- **Default Credentials**: admin/changeme with forced password change on first login

**API Security:**
- **HTTPS Only**: API accessible only via HTTPS on MGMT interface
- **CORS Policy**: Restrictive CORS (same-origin only for V1.0)
- **Rate Limiting**: Basic rate limiting to prevent abuse (deferred to V1.x if needed)
- **Input Validation**: Pydantic models for request validation, SQL injection prevention

**API Documentation:**
- **OpenAPI 3.0**: Auto-generated from FastAPI route definitions
- **Interactive Docs**: Swagger UI at `/api/docs` for testing and exploration
- **Schema Export**: OpenAPI schema available for client code generation

#### Real-Time Communication Architecture

**WebSocket Communication:**
- **Single Multiplexed Connection**: One WebSocket per client for all real-time updates
- **Message Format**: JSON with `type` field for routing (`{"type": "tunnel_state", "data": {...}}`)
- **Server→Client Only**: WebSocket used for server-push updates, not bidirectional RPC
- **Update Frequency**:
  - Interface statistics: 1-2 second polling interval
  - Tunnel state changes: Immediate push (event-driven via strongSwan vici callbacks)
  - Peer status changes: Immediate push
- **Reconnection**: Automatic reconnection with exponential backoff on disconnect

**Backend Monitoring Stack:**
- **Interface Monitoring**: pyroute2 netlink for interface stats across namespaces
- **Tunnel Monitoring**: pyvici for strongSwan vici protocol (real-time SA state)
- **Namespace Execution**: `ip netns exec` to query stats from isolated namespaces
- **Event Loop**: Python asyncio for concurrent monitoring tasks

**State Synchronization:**
- **Zustand Store Updates**: WebSocket messages directly update Zustand state
- **Component Re-renders**: Components subscribe to specific state slices for optimized rendering
- **Multi-Client Sync**: Config changes broadcast via WebSocket to keep multiple clients synchronized

#### Security Architecture

**Domain Isolation:**
- **Three Network Namespaces**: ct-ns (Crypto Text), pt-ns (Plain Text), mgmt-ns (Management)
- **Enforcement**: Namespace boundaries + nftables packet filtering (defense-in-depth)
- **CT Namespace**: Isolated with veth pair allowing only IKE (UDP 500/4500) and ESP (protocol 50)
- **MGMT Access**: Web UI and API accessible only via MGMT interface (TCP 443)

**Authentication & Authorization:**
- **V1.0**: Single admin account (no RBAC)
- **Password Policy**: Minimum 8 characters, forced change on first login
- **Session Management**: JWT with secure httpOnly cookies (web) or Authorization header (API)
- **Audit Logging**: Configuration changes logged with timestamp and user (deferred to V1.x)

**Data Security:**
- **Database**: SQLite with file permissions (600, root-only access)
- **Secrets Storage**: PSKs encrypted at rest (implementation TBD - possibly using Python cryptography library)
- **HTTPS Only**: Web interface served over TLS (self-signed cert for V1.0, user-provided cert support V1.x)

#### Platform & Deployment Requirements

**Base Platform:**
- **Operating System**: Alpine Linux 3.19+ (musl libc, apk package manager)
- **Init System**: OpenRC for service management
- **Image Format**: qcow2 disk image for CML compatibility
- **Image Size**: Target < 500MB compressed

**System Requirements:**
- **vCPU**: 2 vCPU minimum, 4 vCPU maximum supported
- **RAM**: 1GB minimum, target < 2GB usage under 50 peer load
- **Disk**: 2GB minimum for OS + database growth
- **Network Interfaces**: 3 virtual interfaces (CT, PT, MGMT)

**CML Integration:**
- **Deployment**: Drag-and-drop qcow2 import into CML
- **Boot Time**: Target < 30 seconds from power-on to web UI accessible
- **Interface Configuration**: MGMT interface defaults to DHCP, CT/PT require manual config via web UI
- **Serial Console Access**: Restricted shell for emergency MGMT IP configuration only

**Service Dependencies:**
- **strongSwan**: IPsec daemon (5.9+) running in pt-ns namespace
- **Python**: Python 3.11+ with FastAPI, SQLAlchemy, pyroute2, pyvici
- **nftables**: Modern netfilter for packet filtering rules
- **Node.js**: Build-time only (not shipped in final image) for React compilation

#### Data Architecture

**Configuration Storage:**
- **Database**: SQLite with SQLAlchemy ORM
- **Schema**: Relational tables for peers, routes, interfaces, users
- **Transactions**: ACID guarantees for configuration changes
- **Backup**: Single .db file for easy backup/restore

**Configuration Generation:**
- **strongSwan Config**: Python generates swanctl.conf from SQLite on changes
- **nftables Rules**: Python generates nftables ruleset from SQLite
- **Atomic Updates**: Configuration reloaded atomically (old config remains until new validates)

**State vs Configuration:**
- **Configuration**: Stored in SQLite (peers, routes, settings)
- **Runtime State**: Queried via vici/netlink (tunnel status, interface stats, traffic counters)
- **No State Persistence**: Runtime state not stored, re-queried on restart

### Implementation Considerations

**Development Workflow:**
- **Backend First**: Prove namespace isolation, strongSwan integration, API functionality
- **Frontend Second**: Build React UI against working backend
- **Integration Testing**: End-to-end tests with real tunnel establishment

**Key Technical Risks:**
- **Alpine Compatibility**: musl libc may cause Python package compatibility issues
  - Mitigation: Test all dependencies on Alpine early in Phase 0
- **Namespace Monitoring**: Accessing stats across namespaces may have permission issues
  - Mitigation: Backend runs as root, proper capability management
- **WebSocket Scale**: Multiple clients with 1-2 second updates may strain resources
  - Mitigation: Limit to 10 concurrent WebSocket connections, load test early

**Performance Optimization Strategy:**
- **V1.0**: Focus on correctness, not optimization
- **Monitoring**: Measure RAM usage under 50 peer load
- **Optimization**: Only optimize if measurements show problems (don't prematurely optimize)

**Documentation Requirements:**
- **User Guide**: Web UI walkthrough with screenshots
- **API Reference**: Auto-generated OpenAPI documentation
- **Architecture Docs**: Three-namespace design, isolation model, security boundaries
- **Ports/Protocols**: Complete network service listing for firewall configuration

## Project Scoping & Phased Development

This section translates scope into phased delivery, risks, and mitigation strategy.

### MVP Strategy & Philosophy

**MVP Approach: Problem-Solving MVP**

V1.0 delivers a **complete solution to the core problem**: realistic TACLANE/KG encryptor simulation for virtual lab environments. The MVP is scoped to prove that software-based namespace isolation can realistically simulate hardware security boundaries for network testing.

**Success Definition:**
If a network engineer (Ronnie's journey) can deploy the simulator, configure tunnels in < 5 minutes, and realistically test network behavior, V1.0 succeeds. All other user journeys (Mark's demos, Jenny's design validation, Theresa's API automation) are supported but not the primary success criteria.

**Strategic Rationale:**
- **Focus over feature creep**: Solve one problem completely rather than many problems partially
- **Validate innovation risk**: Prove the core technical innovation (virtualized isolation) works before adding enhancements
- **Community feedback loop**: Launch focused MVP, iterate based on user feedback
- **Solo developer constraints**: 20-23 week timeline requires disciplined scope

**Resource Requirements:**
- **Team Size**: Solo developer (Will) with company internal validation support
- **Timeline**: ~20-23 weeks to V1.0 launch
- **Skills Required**: Network engineering, Linux systems, Python/FastAPI, React, IPsec/strongSwan, security testing
- **Post-Launch**: Community-maintained model distributes enhancement burden

### MVP Feature Set (Phase 1 - V1.0)

**Core User Journey Supported:**

**Primary: Ronnie (Network Engineer) - Testing & Optimization**
- Deploy qcow2 image into CML topology
- Configure peers via web UI
- Establish tunnels in < 5 minutes
- Monitor tunnel status in real-time
- Test complex routing scenarios (DMVPN, BGP, etc.)

**Secondary Support (enabled but not primary focus):**
- Mark (Sales Engineer): Pre-validated demos work because Ronnie's testing works
- Jenny (Solution Architect): Design validation works because multi-vendor interop works
- Theresa (Automation Developer): API automation works because API is robust

**Must-Have Capabilities (V1.0):**

**Network Isolation & Security:**
- Three network namespaces (CT, PT, MGMT) with enforced separation
- nftables rules preventing PT→CT direct routing
- Defense-in-depth isolation validation (automated tests)
- Published security report with transparent findings

**IPsec Tunneling:**
- strongSwan (IKEv2/IKEv1 support)
- PSK authentication (certificate auth deferred to V2.0)
- Multi-peer support (minimum 50 peers)
- Route management (minimum 150 routes)
- Real-time tunnel status monitoring

**Web Administration Interface:**
- React SPA with Chakra UI
- Peer CRUD operations
- Route CRUD operations
- Interface configuration (IP/netmask/gateway for CT/PT/MGMT)
- Real-time dashboard (tunnel status, interface statistics via WebSocket)
- JWT authentication (single admin account, no RBAC)

**REST API:**
- FastAPI backend with versioned endpoints (/api/v1/*)
- Peer/route/interface management via API
- Auto-generated OpenAPI documentation
- Same JWT authentication as web UI

**Platform & Deployment:**
- Alpine Linux qcow2 image (< 500MB compressed)
- Boots in < 30 seconds
- CML-compatible (drag-and-drop import)
- MGMT interface DHCP by default
- Serial console for emergency IP configuration

**Documentation:**
- User guide (web UI walkthrough)
- API reference (auto-generated Swagger docs)
- Architecture documentation (three-domain design, security model)
- Ports/protocols reference
- Security validation report

**Success Bar for V1.0:**
Network engineer can deploy, configure tunnels faster than manual router setup, and confidently use for realistic testing.

### Post-MVP Features

**Phase 2 (V1.5) - Usability & Operations:**
- **Role-Based Access Control (RBAC)**: Admin and read-only roles
- **Health Check Diagnostics**: Automated troubleshooting assistance
- **Configuration Snapshots**: Rollback capability for experimentation safety
- **Recharts Visualizations**: Bandwidth/utilization graphs
- **Web Log Viewer**: Human-readable + raw mode for troubleshooting
- **Search Functionality**: Global search across peers/routes
- **Day-Zero Provisioning**: YAML config via virtual CD-ROM
- **Telemetry Export**: Syslog/gRPC/OpenTelemetry for NOC integration

**Rationale for Deferral:**
These enhance operational maturity and usability but aren't essential for proving core value. Community feedback will prioritize which V1.5 features matter most.

**Phase 3 (V2.0+) - Advanced Capabilities:**
- **IPv6 Full Support**: Dual-stack CT/PT interfaces
- **Certificate Authentication**: X.509 certs, CA trust chains, P12 import
- **Advanced Diagnostics**: Packet capture, traffic generation, performance metrics (latency/jitter)
- **Multi-Encryptor Coordination**: Mesh topology automation, bulk configuration
- **Community Features**: Topology sharing, configuration templates
- **Compliance Reporting**: Audit logs, security posture dashboards
- **Section 508 Accessibility**: If government agencies request formal compliance

**Strategic Vision:**
Become the de facto standard for simulating high-security network devices in virtual lab environments, enabling testing of any emerging technology in contexts where encryptors are part of the infrastructure.

### Risk Mitigation Strategy

**Technical Risk: Alpine/musl Compatibility (CRITICAL)**

- **Risk**: Python packages (FastAPI, SQLAlchemy, pyroute2, pyvici) may have musl libc compatibility issues
- **Impact**: Would force pivot to Ubuntu/Debian, increasing image size from ~500MB to 2GB+
- **Mitigation**:
  - **Phase 0 validation**: Test all Python dependencies on Alpine Linux before committing to architecture
  - **Early detection**: Validate in first 4 weeks, before significant development
  - **Fallback plan**: If Alpine proves incompatible, pivot to Alpine-based alternatives or accept larger Ubuntu image
  - **Decision point**: End of Phase 0 - commit to Alpine or pivot

**Technical Risk: Performance Under Load**

- **Risk**: 50 peers + 150 routes may exceed 2GB RAM target or cause UI lag
- **Impact**: Product doesn't meet technical success criteria, user experience degrades
- **Mitigation**:
  - **Load testing**: Test with 50 peer configuration during Phase 3 (Security Hardening & Testing)
  - **Memory profiling**: Measure actual RAM usage, optimize if needed
  - **UI optimization**: Virtualized lists for large datasets if rendering lags
  - **Scope adjustment**: If performance issues arise, reduce peer/route targets and document limitations

**Technical Risk: Namespace Isolation Validation**

- **Risk**: PT→CT traffic leakage discovered post-launch = credibility disaster
- **Impact**: Government/military users lose trust, project reputation destroyed
- **Mitigation**:
  - **Automated isolation tests**: Build test suite that validates PT→CT blocking
  - **Multiple validation methods**: tcpdump packet capture, iptables counters, namespace routing tables
  - **Run on every boot**: Isolation tests execute on startup, red banner if failures detected
  - **Published security report**: Transparent documentation of test methodology and results

**Market Risk: Community Adoption Doesn't Happen**

- **Risk**: Government engineers don't adopt simulator, it remains unused
- **Impact**: GitHub stars/community adoption metrics not met
- **Mitigation**:
  - **Internal value first**: Product delivers value to builder's company labs regardless of external adoption
  - **Realistic success metrics**: 10-15 internal users alone equals success, external adoption is bonus
  - **Low barrier to entry**: Free, open source, qcow2 format makes trying it frictionless
  - **Professional quality**: Security validation and documentation build trust with skeptical users

**Resource Risk: Solo Development Timeline Slips**

- **Risk**: 20-23 week timeline proves unrealistic, V1.0 delayed
- **Impact**: Momentum loss, scope creep pressure, burnout risk
- **Mitigation**:
  - **Disciplined scope**: V1.0 feature set is locked, no additions mid-development
  - **Phase 0 validation**: Prove core concepts before committing to full build
  - **Community launch when ready**: Open source doesn't have hard ship dates, launch when stable
  - **Internal company support**: Company benefits from tool, can provide development time

**Key Scoping Principle:**

Ship a **focused, well-validated V1.0** that proves the core innovation (virtualized TACLANE simulation) works. Let community adoption drive V2.0 priorities rather than guessing what enhancements matter most.

## Functional Requirements

The following functional requirements define the capability contract.

### Deployment & Initialization

- **FR1**: Administrators can deploy the encryptor simulator as a qcow2 VM image in Cisco Modeling Labs
- **FR2**: System can boot from power-off to web UI accessible state
- **FR3**: Administrators can access emergency IP configuration via serial console
- **FR4**: System can initialize with DHCP-assigned MGMT interface IP address

### Network Interface Configuration

- **FR5**: Administrators can configure CT interface IP address, netmask, and gateway
- **FR6**: Administrators can configure PT interface IP address, netmask, and gateway
- **FR7**: Administrators can configure MGMT interface IP address, netmask, and gateway
- **FR8**: Administrators can view current interface configuration for all three interfaces (CT/PT/MGMT)
- **FR9**: System can enforce that CT, PT, and MGMT interfaces operate in isolated network namespaces

### Peer Management

- **FR10**: Administrators can create new IPsec peer configurations
- **FR11**: Administrators can specify peer remote IP address (CT interface of remote encryptor)
- **FR12**: Administrators can specify peer authentication method (PSK for V1.0)
- **FR13**: Administrators can configure peer IKE version (IKEv1 or IKEv2)
- **FR14**: Administrators can view list of all configured peers
- **FR15**: Administrators can edit existing peer configurations
- **FR16**: Administrators can delete peer configurations
- **FR17**: Administrators can configure IPsec parameters per peer (DPD timers, keepalive settings, rekeying intervals)

### Route Management

- **FR18**: Administrators can create routes associated with specific peers
- **FR19**: Administrators can specify destination network CIDR for each route
- **FR20**: Administrators can view all configured routes
- **FR21**: Administrators can view routes grouped by peer
- **FR22**: Administrators can edit existing route configurations
- **FR23**: Administrators can delete routes

### Tunnel Establishment & Control

- **FR24**: System can initiate IPsec tunnel establishment with configured peers
- **FR25**: System can negotiate IKEv2 security associations
- **FR26**: System can negotiate IKEv1 security associations
- **FR27**: System can authenticate peers using pre-shared keys (PSK)
- **FR28**: System can maintain multiple concurrent active tunnels (minimum 50)
- **FR29**: System can automatically handle tunnel rekeying
- **FR30**: System can detect dead peers and mark tunnels as down

### Real-Time Status & Monitoring

- **FR31**: Administrators can view real-time tunnel status (up/down/negotiating) for all configured peers
- **FR32**: Administrators can view interface statistics (bytes tx/rx, packets tx/rx, errors) for CT/PT/MGMT interfaces
- **FR33**: System can push tunnel state changes to web UI without manual refresh
- **FR34**: System can push interface statistics updates to web UI at regular intervals
- **FR35**: Administrators can view tunnel establishment time for active tunnels
- **FR36**: Administrators can identify which tunnels are currently passing traffic

### Authentication & Access Control

- **FR37**: Administrators can log in to web UI using username and password
- **FR38**: System can require administrators to change default password on first login
- **FR39**: System can enforce minimum password complexity requirements
- **FR40**: System can issue JWT tokens upon successful authentication
- **FR41**: System can restrict web UI and API access to authenticated users only
- **FR42**: Administrators can log out of web UI

### API Operations

- **FR43**: Automation tools can authenticate to the API using same credentials as web UI
- **FR44**: Automation tools can create peer configurations via REST API
- **FR45**: Automation tools can create route configurations via REST API
- **FR46**: Automation tools can query tunnel status via REST API
- **FR47**: Automation tools can query interface statistics via REST API
- **FR48**: Automation tools can update interface configurations via REST API
- **FR49**: Automation tools can delete peers and routes via REST API
- **FR50**: Developers can access auto-generated OpenAPI documentation

### Security & Isolation

- **FR51**: System can enforce that PT network traffic cannot route directly to CT network
- **FR52**: System can enforce that only IKE (UDP 500/4500) and ESP (protocol 50) traffic passes between PT and CT namespaces
- **FR53**: System can execute automated isolation validation tests on startup
- **FR54**: System can display isolation test results to administrators
- **FR55**: System can encrypt PSKs at rest in configuration database

### Documentation & Help

- **FR56**: Users can access user guide documentation
- **FR57**: Users can access architecture documentation describing three-domain isolation model
- **FR58**: Users can access ports and protocols reference documentation
- **FR59**: Users can access published security validation report

## Non-Functional Requirements

The following non-functional requirements define quality attributes and constraints.

### Performance

**Boot & Initialization:**
- **NFR-P1**: System shall boot from power-off to web UI accessible state in < 30 seconds
- **NFR-P2**: System shall initialize all three network namespaces within boot sequence

**Web UI Responsiveness:**
- **NFR-P3**: Initial page load shall complete in < 2 seconds from cold start
- **NFR-P4**: Dashboard shall render 50 peers and 150 routes without perceptible lag
- **NFR-P5**: User interface interactions shall provide feedback within < 100ms

**Real-Time Updates:**
- **NFR-P6**: Interface statistics shall update via WebSocket at 1-2 second intervals
- **NFR-P7**: Tunnel state changes shall push to web UI immediately (< 1 second from state change)
- **NFR-P8**: System shall support up to 10 concurrent WebSocket connections without degradation

**Tunnel Performance:**
- **NFR-P9**: System shall support minimum 10 Mbps throughput per active tunnel
- **NFR-P10**: System shall establish tunnels from configuration to "UP" state in < 5 minutes (user-facing goal)

### Security

**Isolation & Separation:**
- **NFR-S1**: PT network traffic shall be physically unable to route directly to CT network (namespace boundary enforcement)
- **NFR-S2**: Only IKE (UDP 500/4500) and ESP (protocol 50) traffic shall pass between PT and CT namespaces
- **NFR-S3**: Automated isolation validation tests shall execute on every system boot
- **NFR-S4**: System shall display red banner in web UI if isolation validation fails

**Authentication & Access Control:**
- **NFR-S5**: Web UI and API shall be accessible only via HTTPS on MGMT interface
- **NFR-S6**: System shall enforce minimum 8-character password complexity
- **NFR-S7**: System shall force password change on first login from default credentials
- **NFR-S8**: JWT tokens shall expire after 1 hour (access token) and 7 days (refresh token)

**Data Protection:**
- **NFR-S9**: Pre-shared keys (PSKs) shall be encrypted at rest in SQLite database
- **NFR-S10**: SQLite database file shall have 600 permissions (root-only access)
- **NFR-S11**: Web UI shall store JWT in memory only (not localStorage)

**Security Validation & Transparency:**
- **NFR-S12**: System shall complete internal security testing (nmap, OWASP ZAP, SQL injection testing) before V1.0 release
- **NFR-S13**: Security test results shall be published in public security report
- **NFR-S14**: System shall have zero critical security vulnerabilities at V1.0 launch

### Reliability

**System Stability:**
- **NFR-R1**: System shall boot reliably in CML environment without manual intervention
- **NFR-R2**: System shall maintain active tunnels across configuration changes (no unnecessary tunnel flapping)
- **NFR-R3**: Web UI shall automatically reconnect WebSocket connections on disconnect with exponential backoff

**Capacity & Scale:**
- **NFR-R4**: System shall support minimum 50 concurrent peer configurations
- **NFR-R5**: System shall support minimum 150 route configurations
- **NFR-R6**: System shall consume < 2GB RAM under 50-peer load
- **NFR-R7**: System shall maintain stable operation for 30+ days continuous uptime

**Data Integrity:**
- **NFR-R8**: Configuration changes shall be atomic (old config remains until new validates)
- **NFR-R9**: SQLite database shall provide ACID guarantees for all transactions
- **NFR-R10**: System shall not lose configuration data on unplanned shutdown

### Maintainability

**Code Quality:**
- **NFR-M1**: Backend code shall follow PEP 8 Python style guidelines
- **NFR-M2**: Frontend code shall use ESLint with standard React rules
- **NFR-M3**: All public API endpoints shall have auto-generated OpenAPI documentation

**Documentation:**
- **NFR-M4**: User guide shall include screenshots and step-by-step workflows
- **NFR-M5**: Architecture documentation shall describe three-domain isolation model with diagrams
- **NFR-M6**: Ports/protocols reference shall list all network services with purpose and security implications

**Community Contribution:**
- **NFR-M7**: Codebase shall use popular tech stack (Python/React/strongSwan) to enable community contributions
- **NFR-M8**: GitHub repository shall include contribution guidelines and code of conduct
- **NFR-M9**: Project shall maintain < 48 hour average response time to GitHub issues during active development

### Platform Compatibility

**Deployment Environment:**
- **NFR-C1**: qcow2 image shall be < 500MB compressed
- **NFR-C2**: System shall run on Alpine Linux 3.19+ (musl libc)
- **NFR-C3**: System shall import into CML via drag-and-drop without modification
- **NFR-C4**: System shall operate within 2 vCPU minimum, 4 vCPU maximum allocation
- **NFR-C5**: System shall operate within 1GB RAM minimum allocation

**Browser Support:**
- **NFR-C6**: Web UI shall function in latest stable versions of Chrome, Firefox, Edge, and Safari
- **NFR-C7**: Web UI shall target desktop/laptop displays (1024px+ width)
- **NFR-C8**: Web UI shall not require mobile device support
