# Security Report

## Summary

This report documents the planned security testing for the V1.0 release candidate and records results as they become available.

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

- Build ID: TBD (capture at scan time)
- Image SHA: TBD (capture at scan time)
- Appliance version: TBD (capture at scan time)
- Source commit: TBD (capture at scan time)
- Configuration: TBD (capture at scan time)

## Methodology

- Nmap HTTPS service and TLS enumeration against the MGMT interface and API.
- OWASP ZAP baseline scan against HTTPS endpoints.
- SQL injection checks using safe, targeted `sqlmap` requests with JWT authentication.
- All scan outputs are timestamped in ISO-8601 UTC format (YYYYMMDDTHHMMSSZ) and stored under `docs/security/`.

## Tools and Versions

- nmap: TBD (capture at scan time)
- OWASP ZAP: TBD (capture at scan time)
- sqlmap: TBD (capture at scan time)

## Results Summary

- Status: Pending scan execution after appliance image packaging.
- Findings: TBD after scans.
- Affected endpoints: TBD after scans.

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

- TBD (only populated if findings require remediation)

## Raw Artifacts

- Placeholder list: `docs/security/README.md`
- Pending summary: `docs/security/scan-results-placeholder.md`
- Expected outputs:
  - `docs/security/nmap-YYYYMMDDTHHMMSSZ.txt`
  - `docs/security/zap-YYYYMMDDTHHMMSSZ.html`
  - `docs/security/sqlmap-YYYYMMDDTHHMMSSZ/`
