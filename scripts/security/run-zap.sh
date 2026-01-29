#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:?TARGET_HOST is required}"
TARGET_PORT="${TARGET_PORT:-443}"
OUT_DIR="docs/security"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Validate zap.sh is installed
if ! command -v zap.sh &> /dev/null; then
  echo "ERROR: zap.sh is not installed. Install OWASP ZAP before running this script."
  exit 1
fi

mkdir -p "$OUT_DIR"

# OWASP ZAP baseline scan against HTTPS target.
# Requires zap.sh in PATH (ZAP installed locally).
zap.sh -cmd -quickurl "https://${TARGET_HOST}:${TARGET_PORT}" \
  -quickout "${OUT_DIR}/zap-${STAMP}.html" \
  -quickprogress

echo "ZAP output saved to ${OUT_DIR}/zap-${STAMP}.html"
