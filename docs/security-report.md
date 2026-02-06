# Security Report

## Summary

This report captures the V1.0 security test gate and current execution status.
As of 2026-02-06, lab security scans have not been executed from this repository
workspace because a packaged appliance image has not yet been provided for scan execution.

## Scope

### Target Surfaces

- MGMT interface (HTTPS)
- REST API (JWT-authenticated)
- Web UI
- WebSocket endpoint

### Exclusions

- non-destructive scans only
- lab-only environment (no production targets)
- No denial-of-service or load testing

## Environment

### Build and Configuration

- Build ID: not assigned yet (image packaging pending)
- Image SHA: not available yet (image packaging pending)
- Appliance version: V1.0 candidate
- Source commit: `034592c`
- Configuration: lab defaults, MGMT HTTPS access only

## Methodology

- Nmap HTTPS service and TLS enumeration against the MGMT interface and API.
- OWASP ZAP baseline scan against HTTPS endpoints.
- SQL injection checks using safe, targeted `sqlmap` requests with JWT authentication.
- All scan outputs are timestamped in ISO-8601 UTC format (YYYYMMDDTHHMMSSZ) and stored under `docs/security/`.

## Tools and Versions

- nmap: to be captured at scan run time
- OWASP ZAP: to be captured at scan run time
- sqlmap: to be captured at scan run time

## Results Summary

- Status: not executed yet (blocked on packaged appliance image)
- Findings: none recorded yet
- Affected endpoints: not evaluated yet

## Critical Vulnerabilities

- V1.0 launch target: 0 critical vulnerabilities (pending scan confirmation).
- Current status: scans pending; release is blocked until scans confirm zero critical issues.
- If any critical findings occur, remediation actions and re-test results will be documented here.

## Isolation Validation Reference

Startup isolation validation runs on boot and reports status in the UI banner; it enforces PT/CT separation as part of the security posture. See `backend/tests/unit/test_isolation_validation.py` and the Isolation Status banner behavior for the validation mechanism.

## Risks and Limitations

- Results are pending until the virtual image is available for lab testing.
- Scans are limited to non-destructive checks and do not include load or fuzz testing.

## Remediation Log

- No remediations recorded yet (no scan findings collected).

## Raw Artifacts

- Placeholder list: `docs/security/README.md`
- Pending summary: `docs/security/scan-results-placeholder.md`
- Expected outputs:
  - `docs/security/nmap-YYYYMMDDTHHMMSSZ.txt`
  - `docs/security/zap-YYYYMMDDTHHMMSSZ.html`
  - `docs/security/sqlmap-YYYYMMDDTHHMMSSZ/`
