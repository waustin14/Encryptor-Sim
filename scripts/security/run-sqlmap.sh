#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:?TARGET_HOST is required}"
API_BASE="${API_BASE:?API_BASE is required}"
AUTH_USER="${AUTH_USER:?AUTH_USER is required}"
AUTH_PASS="${AUTH_PASS:?AUTH_PASS is required}"
JWT_TOKEN="${JWT_TOKEN:-}"
OUT_DIR="docs/security"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Validate required tools are installed
if ! command -v sqlmap &> /dev/null; then
  echo "ERROR: sqlmap is not installed. Install it before running this script."
  exit 1
fi

if ! command -v curl &> /dev/null; then
  echo "ERROR: curl is not installed. Install it before running this script."
  exit 1
fi

if ! command -v jq &> /dev/null; then
  echo "ERROR: jq is not installed. Install it before running this script."
  exit 1
fi

mkdir -p "$OUT_DIR"

if [[ -z "$JWT_TOKEN" ]]; then
  JWT_TOKEN="$(curl -k -s -X POST "${API_BASE}/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${AUTH_USER}\",\"password\":\"${AUTH_PASS}\"}" \
    | jq -r ".access_token")"
fi

if [[ -z "$JWT_TOKEN" || "$JWT_TOKEN" == "null" ]]; then
  echo "Failed to obtain JWT token. Set JWT_TOKEN or update auth endpoint."
  exit 1
fi

# Safe, targeted SQLi checks against authenticated API endpoints.
sqlmap -u "${API_BASE}/v1/peers?filter=test" \
  --headers="Authorization: Bearer ${JWT_TOKEN}" \
  --batch --risk=1 --level=1 --timeout=10 --threads=1 \
  --output-dir="${OUT_DIR}/sqlmap-${STAMP}"

echo "sqlmap output saved to ${OUT_DIR}/sqlmap-${STAMP}"
