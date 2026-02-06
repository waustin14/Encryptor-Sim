#!/usr/bin/env bash
# Encryptor Simulator API - curl examples
#
# Requirements: bash, curl, python3
#
# Usage:
#   export MGMT_IP=192.168.1.100
#   export ADMIN_PASSWORD=YourPassword123
#   bash curl_examples.sh
#
# Note: --insecure is required for the self-signed TLS certificate.

set -euo pipefail

MGMT_IP="${MGMT_IP:?Set MGMT_IP to the management interface address}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?Set ADMIN_PASSWORD}"
BASE_URL="https://${MGMT_IP}:443"

echo "=== 1. Login ==="
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"${ADMIN_PASSWORD}\"}" \
  --insecure)

echo "${LOGIN_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${LOGIN_RESPONSE}"

# Extract tokens (requires python3)
ACCESS_TOKEN=$(echo "${LOGIN_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")
REFRESH_TOKEN=$(echo "${LOGIN_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['refreshToken'])")

echo ""
echo "=== 2. Access protected endpoint (GET /auth/me) ==="
curl -s -X GET "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  --insecure | python3 -m json.tool

echo ""
echo "=== 3. Access system health ==="
curl -s -X GET "${BASE_URL}/api/v1/system/health" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  --insecure | python3 -m json.tool

echo ""
echo "=== 4. Refresh access token ==="
REFRESH_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\":\"${REFRESH_TOKEN}\"}" \
  --insecure)

echo "${REFRESH_RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${REFRESH_RESPONSE}"

NEW_ACCESS_TOKEN=$(echo "${REFRESH_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['accessToken'])")

echo ""
echo "=== 5. Use refreshed token ==="
curl -s -X GET "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer ${NEW_ACCESS_TOKEN}" \
  --insecure | python3 -m json.tool

echo ""
echo "=== 6. Error handling: invalid token ==="
echo "Expected: 401 Unauthorized"
curl -s -X GET "${BASE_URL}/api/v1/auth/me" \
  -H "Authorization: Bearer invalid.token.here" \
  --insecure | python3 -m json.tool

echo ""
echo "=== Done ==="
