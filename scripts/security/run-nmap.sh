#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:?TARGET_HOST is required}"
TARGET_PORT="${TARGET_PORT:-443}"
OUT_DIR="docs/security"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# Validate nmap is installed
if ! command -v nmap &> /dev/null; then
  echo "ERROR: nmap is not installed. Install it before running this script."
  exit 1
fi

mkdir -p "$OUT_DIR"

# Non-destructive HTTPS scan for exposed services and TLS details.
nmap -sV -p "$TARGET_PORT" --script "ssl-enum-ciphers,ssl-cert,http-security-headers" \
  "$TARGET_HOST" \
  -oN "${OUT_DIR}/nmap-${STAMP}.txt"

echo "Nmap output saved to ${OUT_DIR}/nmap-${STAMP}.txt"
