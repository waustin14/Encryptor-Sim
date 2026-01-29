#!/usr/bin/env bash
#
# validate-image.sh - Validate qcow2 image artifacts and perform optional boot check
#
# Usage: ./validate-image.sh [--no-boot]
#
# Notes:
# - This script is intended for Linux build hosts with QEMU installed.
# - Boot validation is best-effort and still requires manual verification in CML.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"
IMAGE_NAME="encryptor-sim"
QCOW2_IMAGE="${OUTPUT_DIR}/${IMAGE_NAME}.qcow2"
COMPRESSED_IMAGE="${OUTPUT_DIR}/${IMAGE_NAME}.qcow2.gz"
MAX_COMPRESSED_SIZE=$((500 * 1024 * 1024))

NO_BOOT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-boot)
            NO_BOOT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--no-boot]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required tool: $1" >&2
        exit 1
    }
}

require qemu-img
require gzip

[[ -f "$QCOW2_IMAGE" ]] || { echo "Missing qcow2: $QCOW2_IMAGE" >&2; exit 1; }

log "Validating qcow2 format..."
qemu-img info "$QCOW2_IMAGE" >/dev/null

log "Validating compressed size < 500MB..."
check_file="$COMPRESSED_IMAGE"
temp_check=""

if [[ ! -f "$check_file" ]]; then
    temp_check="$(mktemp "${OUTPUT_DIR}/size-check.XXXXXX.qcow2.gz")"
    gzip -9 -c "$QCOW2_IMAGE" > "$temp_check"
    check_file="$temp_check"
fi

size=$(stat -f%z "$check_file" 2>/dev/null || stat -c%s "$check_file")
size_mb=$((size / 1024 / 1024))
log "Compressed size: ${size_mb}MB"

if [[ $size -gt $MAX_COMPRESSED_SIZE ]]; then
    echo "Compressed size exceeds 500MB" >&2
    exit 1
fi

if [[ -n "$temp_check" ]]; then
    rm -f "$temp_check"
fi

if [[ "$NO_BOOT" == "true" ]]; then
    log "Skipping boot validation (--no-boot)"
    exit 0
fi

require qemu-system-x86_64
require timeout

log "Boot validation (best-effort, 60s)..."
timeout 60s qemu-system-x86_64 \
    -m 1024 \
    -smp 2 \
    -drive "file=${QCOW2_IMAGE},format=qcow2,if=virtio" \
    -netdev user,id=net0 \
    -device virtio-net-pci,netdev=net0 \
    -nographic >/dev/null 2>&1 || true

log "Boot check complete. Manual CML import/boot validation still required."
