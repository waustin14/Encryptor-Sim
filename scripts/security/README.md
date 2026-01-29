# Security Scan Scripts

This folder contains repeatable, non-destructive security scan commands for the lab appliance.

## Prerequisites

- Run against a lab-only target (never production).
- HTTPS only.
- Tools installed locally: `nmap`, `zap.sh` (OWASP ZAP), `sqlmap`, `curl`, `jq`.
- Scripts must be executable: `chmod +x *.sh`

## Environment Variables

- `TARGET_HOST`: Host or IP of the MGMT interface (example: 192.0.2.10)
- `TARGET_PORT`: HTTPS port (default: 443)
- `API_BASE`: Base API URL (example: https://192.0.2.10/api)
- `AUTH_USER`: Username for JWT token acquisition
- `AUTH_PASS`: Password for JWT token acquisition
- `JWT_TOKEN`: Optional pre-acquired token (if set, auth step is skipped)

## JWT Token Acquisition

If `JWT_TOKEN` is not set, the scripts use this command:

```
curl -k -s -X POST "$API_BASE/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$AUTH_USER\",\"password\":\"$AUTH_PASS\"}" \
  | jq -r ".access_token"
```

Note: API follows /api/v1 versioning pattern per architecture.

## Commands

- Nmap HTTPS scan: `./run-nmap.sh`
- OWASP ZAP baseline scan: `./run-zap.sh`
- SQL injection checks (safe flags): `./run-sqlmap.sh`

Each script writes artifacts to `docs/security/` with timestamps in ISO-8601 UTC format (YYYYMMDDTHHMMSSZ).
