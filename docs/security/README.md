# Security Scan Artifacts

Raw scan outputs for the V1.0 security gate are stored in this directory.
As of 2026-02-06, these artifacts are not yet present because image packaging and
lab scan execution are still pending.

Expected files (timestamped, UTC in ISO-8601 format):

- `docs/security/nmap-YYYYMMDDTHHMMSSZ.txt`
- `docs/security/zap-YYYYMMDDTHHMMSSZ.html`
- `docs/security/sqlmap-YYYYMMDDTHHMMSSZ/`

Add scan outputs using the naming convention above once the security run completes.
