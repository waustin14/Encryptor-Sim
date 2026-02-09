#!/usr/bin/env bash
#
# deploy-test-topology.sh - Deploy a two-site encryptor test topology
#
# Launches four QEMU VMs with virtual L2 segments connecting them:
#
#         Host LAN (via port forwarding on 0.0.0.0)
#           |                        |
#         [MGMT]                   [MGMT]
#       :8443->443               :9443->443
#       :2201->22                :2202->22
#      +-----------+            +-----------+
#      | Encryptor |            | Encryptor |
#      |  Site A   |            |  Site B   |
#      +-----------+            +-----------+
#        [CT]                       [CT]
#         |______ CT Network ________|
#                172.16.0.0/24
#        [PT]                       [PT]
#         |                          |
#      PT-A Network             PT-B Network
#      10.0.1.0/24              10.0.2.0/24
#         |                          |
#      +----------+            +----------+
#      | Alpine A |            | Alpine B |
#      +----------+            +----------+
#
# Usage:
#   ./deploy-test-topology.sh start               Launch all VMs
#   ./deploy-test-topology.sh stop                 Gracefully stop all VMs
#   ./deploy-test-topology.sh kill                 Force-kill all VMs
#   ./deploy-test-topology.sh status               Show VM status
#   ./deploy-test-topology.sh console <vm-name>    Attach to serial console
#   ./deploy-test-topology.sh clean                Remove overlay images and work dir
#
#   VM names: encryptor-a, encryptor-b, alpine-a, alpine-b
#
# Requirements:
#   - qemu-system-x86_64 (with virtio support)
#   - qemu-img
#   - socat (for console access)
#   - curl (for Alpine ISO download)
#   - Built encryptor image at image/output/encryptor-sim.qcow2
#
# MGMT Access (from any host on the LAN):
#   Encryptor A Web UI:  https://<host-ip>:8443
#   Encryptor A SSH:     ssh -p 2201 root@<host-ip>
#   Encryptor B Web UI:  https://<host-ip>:9443
#   Encryptor B SSH:     ssh -p 2202 root@<host-ip>
#
# Console Access (from the machine running the VMs):
#   ./deploy-test-topology.sh console encryptor-a
#   ./deploy-test-topology.sh console alpine-a
#   (Detach with Ctrl-O then 'q' -- this is socat's escape)
#
# Suggested IP Configuration (applied via each VM's UI or shell):
#   CT Network (172.16.0.0/24):
#     Encryptor A CT (eth1): 172.16.0.1/24
#     Encryptor B CT (eth1): 172.16.0.2/24
#   PT-A Network (10.0.1.0/24):
#     Encryptor A PT (eth2): 10.0.1.1/24
#     Alpine A (eth0):       10.0.1.10/24  gw 10.0.1.1
#   PT-B Network (10.0.2.0/24):
#     Encryptor B PT (eth2): 10.0.2.1/24
#     Alpine B (eth0):       10.0.2.10/24  gw 10.0.2.1

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Encryptor image (must be built first via image/build-image.sh)
ENCRYPTOR_IMAGE="${PROJECT_ROOT}/image/output/encryptor-sim.qcow2"

# Alpine virt ISO for vanilla test hosts
ALPINE_VERSION="3.23"
ALPINE_RELEASE="3.23.2"
ALPINE_ISO="alpine-virt-${ALPINE_RELEASE}-x86_64.iso"
ALPINE_ISO_URL="https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION}/releases/x86_64/${ALPINE_ISO}"

# Work directory (overlay images, ISOs, runtime state)
WORK_DIR="${PROJECT_ROOT}/test-topology"
PID_DIR="${WORK_DIR}/run"
CONSOLE_DIR="${WORK_DIR}/consoles"
MONITOR_DIR="${WORK_DIR}/monitors"

# VM resources
ENCRYPTOR_MEM="1024"
ENCRYPTOR_CPUS="2"
HOST_MEM="512"
HOST_CPUS="1"

# Host port mappings for MGMT access (bound to 0.0.0.0 for LAN visibility)
ENCR_A_HTTPS_PORT=8443
ENCR_A_SSH_PORT=2201
ENCR_B_HTTPS_PORT=9443
ENCR_B_SSH_PORT=2202

# Virtual L2 segments via QEMU UDP multicast sockets
# VMs sharing the same mcast address:port are on the same L2 segment
CT_MCAST="230.0.0.1:10001"
PT_A_MCAST="230.0.0.1:10002"
PT_B_MCAST="230.0.0.1:10003"

# MAC addresses (locally administered, unique per NIC)
ENCR_A_MAC_MGMT="52:54:00:01:00:0a"
ENCR_A_MAC_CT="52:54:00:01:01:0a"
ENCR_A_MAC_PT="52:54:00:01:02:0a"
ENCR_B_MAC_MGMT="52:54:00:02:00:0b"
ENCR_B_MAC_CT="52:54:00:02:01:0b"
ENCR_B_MAC_PT="52:54:00:02:02:0b"
ALPINE_A_MAC="52:54:00:03:00:0a"
ALPINE_B_MAC="52:54:00:04:00:0b"

# All VM names
VMS=(encryptor-a encryptor-b alpine-a alpine-b)

# =============================================================================
# Helper functions
# =============================================================================

log()   { echo "[$(date '+%H:%M:%S')] $*"; }
warn()  { echo "[$(date '+%H:%M:%S')] WARNING: $*" >&2; }
error() { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; exit 1; }

pid_file()     { echo "${PID_DIR}/$1.pid"; }
console_sock() { echo "${CONSOLE_DIR}/$1.sock"; }
monitor_sock() { echo "${MONITOR_DIR}/$1.sock"; }

check_deps() {
    local missing=()
    for cmd in qemu-system-x86_64 qemu-img socat curl; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing[*]}"
    fi
}

detect_accel() {
    case "$(uname -s)" in
        Darwin)
            if qemu-system-x86_64 -accel help 2>&1 | grep -q hvf; then
                echo "hvf"
            else
                echo "tcg"
            fi
            ;;
        Linux)
            if [[ -r /dev/kvm ]]; then
                echo "kvm"
            else
                echo "tcg"
            fi
            ;;
        *)
            echo "tcg"
            ;;
    esac
}

is_running() {
    local pf
    pf=$(pid_file "$1")
    if [[ -f "$pf" ]]; then
        local pid
        pid=$(cat "$pf")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        # Stale PID file
        rm -f "$pf"
    fi
    return 1
}

any_running() {
    for vm in "${VMS[@]}"; do
        if is_running "$vm"; then
            return 0
        fi
    done
    return 1
}

ensure_dirs() {
    mkdir -p "$WORK_DIR" "$PID_DIR" "$CONSOLE_DIR" "$MONITOR_DIR"
}

# =============================================================================
# Setup
# =============================================================================

download_alpine_iso() {
    local iso_path="${WORK_DIR}/${ALPINE_ISO}"
    if [[ -f "$iso_path" ]]; then
        log "Alpine ISO already present"
        return
    fi
    log "Downloading Alpine Linux ${ALPINE_RELEASE} virt ISO..."
    curl -fSL -o "${iso_path}.tmp" "$ALPINE_ISO_URL"
    mv "${iso_path}.tmp" "$iso_path"
    log "Download complete ($(du -h "$iso_path" | cut -f1))"
}

create_vm_images() {
    # Encryptor overlay images (copy-on-write, preserving the base image)
    for site in a b; do
        local overlay="${WORK_DIR}/encryptor-${site}.qcow2"
        if [[ ! -f "$overlay" ]]; then
            log "Creating overlay image for encryptor-${site}..."
            qemu-img create -f qcow2 -b "$ENCRYPTOR_IMAGE" -F qcow2 "$overlay"
        fi
    done

    # Empty disks for Alpine hosts (boot from ISO; optionally install to disk)
    for site in a b; do
        local disk="${WORK_DIR}/alpine-${site}.qcow2"
        if [[ ! -f "$disk" ]]; then
            log "Creating disk for alpine-${site}..."
            qemu-img create -f qcow2 "$disk" 2G
        fi
    done
}

# =============================================================================
# VM launch
# =============================================================================

launch_encryptor() {
    local name="$1"
    local https_port="$2"
    local ssh_port="$3"
    local pt_mcast="$4"
    local mac_mgmt="$5"
    local mac_ct="$6"
    local mac_pt="$7"

    if is_running "$name"; then
        warn "${name} is already running"
        return
    fi

    local overlay="${WORK_DIR}/${name}.qcow2"
    local accel
    accel=$(detect_accel)

    log "Launching ${name} (accel=${accel})..."

    # Clean up stale sockets
    rm -f "$(console_sock "$name")" "$(monitor_sock "$name")"

    qemu-system-x86_64 \
        -name "$name" \
        -accel "$accel" \
        -m "$ENCRYPTOR_MEM" \
        -smp "$ENCRYPTOR_CPUS" \
        -drive "file=${overlay},format=qcow2,if=virtio" \
        -netdev "user,id=mgmt,hostfwd=tcp:0.0.0.0:${https_port}-:443,hostfwd=tcp:0.0.0.0:${ssh_port}-:22" \
        -device "virtio-net-pci,netdev=mgmt,mac=${mac_mgmt}" \
        -netdev "socket,id=ct,mcast=${CT_MCAST}" \
        -device "virtio-net-pci,netdev=ct,mac=${mac_ct}" \
        -netdev "socket,id=pt,mcast=${pt_mcast}" \
        -device "virtio-net-pci,netdev=pt,mac=${mac_pt}" \
        -serial "unix:$(console_sock "$name"),server,nowait" \
        -monitor "unix:$(monitor_sock "$name"),server,nowait" \
        -nographic \
        -pidfile "$(pid_file "$name")" \
        -daemonize

    log "${name} started (PID $(cat "$(pid_file "$name")"))"
}

launch_alpine() {
    local name="$1"
    local pt_mcast="$2"
    local mac="$3"

    if is_running "$name"; then
        warn "${name} is already running"
        return
    fi

    local disk="${WORK_DIR}/${name}.qcow2"
    local iso="${WORK_DIR}/${ALPINE_ISO}"
    local accel
    accel=$(detect_accel)

    log "Launching ${name} (accel=${accel})..."

    # Clean up stale sockets
    rm -f "$(console_sock "$name")" "$(monitor_sock "$name")"

    qemu-system-x86_64 \
        -name "$name" \
        -accel "$accel" \
        -m "$HOST_MEM" \
        -smp "$HOST_CPUS" \
        -drive "file=${disk},format=qcow2,if=virtio" \
        -cdrom "$iso" \
        -boot d \
        -netdev "socket,id=pt,mcast=${pt_mcast}" \
        -device "virtio-net-pci,netdev=pt,mac=${mac}" \
        -serial "unix:$(console_sock "$name"),server,nowait" \
        -monitor "unix:$(monitor_sock "$name"),server,nowait" \
        -nographic \
        -pidfile "$(pid_file "$name")" \
        -daemonize

    log "${name} started (PID $(cat "$(pid_file "$name")"))"
}

# =============================================================================
# Commands
# =============================================================================

cmd_start() {
    check_deps

    if [[ ! -f "$ENCRYPTOR_IMAGE" ]]; then
        error "Encryptor image not found: ${ENCRYPTOR_IMAGE}\nBuild it first: sudo ./image/build-image.sh"
    fi

    if any_running; then
        error "Some VMs are already running. Run 'stop' first."
    fi

    ensure_dirs
    download_alpine_iso
    create_vm_images

    local accel
    accel=$(detect_accel)

    log "Starting test topology..."
    echo ""

    # Launch encryptors
    launch_encryptor "encryptor-a" \
        "$ENCR_A_HTTPS_PORT" "$ENCR_A_SSH_PORT" "$PT_A_MCAST" \
        "$ENCR_A_MAC_MGMT" "$ENCR_A_MAC_CT" "$ENCR_A_MAC_PT"

    launch_encryptor "encryptor-b" \
        "$ENCR_B_HTTPS_PORT" "$ENCR_B_SSH_PORT" "$PT_B_MCAST" \
        "$ENCR_B_MAC_MGMT" "$ENCR_B_MAC_CT" "$ENCR_B_MAC_PT"

    # Launch Alpine test hosts
    launch_alpine "alpine-a" "$PT_A_MCAST" "$ALPINE_A_MAC"
    launch_alpine "alpine-b" "$PT_B_MCAST" "$ALPINE_B_MAC"

    echo ""
    log "All VMs launched."
    echo ""
    echo "=== Access Information ==="
    echo ""
    echo "  MGMT (from LAN):"
    echo "    Encryptor A Web UI:  https://localhost:${ENCR_A_HTTPS_PORT}"
    echo "    Encryptor A SSH:     ssh -p ${ENCR_A_SSH_PORT} root@localhost"
    echo "    Encryptor B Web UI:  https://localhost:${ENCR_B_HTTPS_PORT}"
    echo "    Encryptor B SSH:     ssh -p ${ENCR_B_SSH_PORT} root@localhost"
    echo ""
    echo "  Serial Console:"
    echo "    $0 console encryptor-a"
    echo "    $0 console encryptor-b"
    echo "    $0 console alpine-a"
    echo "    $0 console alpine-b"
    echo "    (Detach: Ctrl-O then q)"
    echo ""
    echo "  Suggested IP Setup:"
    echo "    CT:   Encryptor-A 172.16.0.1/24  Encryptor-B 172.16.0.2/24"
    echo "    PT-A: Encryptor-A 10.0.1.1/24    Alpine-A 10.0.1.10/24 gw 10.0.1.1"
    echo "    PT-B: Encryptor-B 10.0.2.1/24    Alpine-B 10.0.2.10/24 gw 10.0.2.1"
    echo ""
    echo "  Alpine hosts boot from live ISO. Log in as root (no password)."
    echo "  Configure networking from the console, e.g.:"
    echo "    ip addr add 10.0.1.10/24 dev eth0"
    echo "    ip route add default via 10.0.1.1"
    echo ""
}

cmd_stop() {
    log "Stopping test topology..."

    for vm in "${VMS[@]}"; do
        if is_running "$vm"; then
            local mon
            mon=$(monitor_sock "$vm")
            if [[ -S "$mon" ]]; then
                log "Sending ACPI powerdown to ${vm}..."
                echo "system_powerdown" | socat - "UNIX-CONNECT:${mon}" 2>/dev/null || true
            fi
        fi
    done

    # Wait up to 15 seconds for graceful shutdown
    log "Waiting for VMs to shut down (up to 15s)..."
    local waited=0
    while any_running && [[ $waited -lt 15 ]]; do
        sleep 1
        waited=$((waited + 1))
    done

    # Force-kill any remaining VMs
    for vm in "${VMS[@]}"; do
        if is_running "$vm"; then
            local pid
            pid=$(cat "$(pid_file "$vm")")
            warn "${vm} (PID ${pid}) did not shut down gracefully, sending SIGTERM..."
            kill "$pid" 2>/dev/null || true
        fi
    done

    sleep 1

    # Clean up PID files for any that stopped
    for vm in "${VMS[@]}"; do
        local pf
        pf=$(pid_file "$vm")
        if [[ -f "$pf" ]]; then
            local pid
            pid=$(cat "$pf")
            if ! kill -0 "$pid" 2>/dev/null; then
                rm -f "$pf"
            fi
        fi
    done

    # Clean up sockets
    rm -f "${CONSOLE_DIR}"/*.sock "${MONITOR_DIR}"/*.sock 2>/dev/null || true

    log "Topology stopped."
}

cmd_kill() {
    log "Force-killing all VMs..."

    for vm in "${VMS[@]}"; do
        local pf
        pf=$(pid_file "$vm")
        if [[ -f "$pf" ]]; then
            local pid
            pid=$(cat "$pf")
            if kill -0 "$pid" 2>/dev/null; then
                log "Killing ${vm} (PID ${pid})..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pf"
        fi
    done

    rm -f "${CONSOLE_DIR}"/*.sock "${MONITOR_DIR}"/*.sock 2>/dev/null || true
    log "Done."
}

cmd_status() {
    local running=0

    printf "%-16s %-8s %s\n" "VM" "STATUS" "PID"
    printf "%-16s %-8s %s\n" "---" "------" "---"

    for vm in "${VMS[@]}"; do
        if is_running "$vm"; then
            local pid
            pid=$(cat "$(pid_file "$vm")")
            printf "%-16s %-8s %s\n" "$vm" "running" "$pid"
            running=$((running + 1))
        else
            printf "%-16s %-8s %s\n" "$vm" "stopped" "-"
        fi
    done

    echo ""

    if [[ $running -gt 0 ]]; then
        echo "MGMT access:"
        if is_running "encryptor-a"; then
            echo "  Encryptor A: https://localhost:${ENCR_A_HTTPS_PORT}  ssh -p ${ENCR_A_SSH_PORT} root@localhost"
        fi
        if is_running "encryptor-b"; then
            echo "  Encryptor B: https://localhost:${ENCR_B_HTTPS_PORT}  ssh -p ${ENCR_B_SSH_PORT} root@localhost"
        fi
    fi
}

cmd_console() {
    local vm="$1"
    local sock
    sock=$(console_sock "$vm")

    if ! is_running "$vm"; then
        error "${vm} is not running"
    fi

    if [[ ! -S "$sock" ]]; then
        error "Console socket not found: ${sock}"
    fi

    if ! command -v socat &>/dev/null; then
        error "socat is required for console access. Install it first."
    fi

    echo "Connecting to ${vm} serial console..."
    echo "  Detach: press Ctrl-O then type 'q' and Enter"
    echo ""

    socat -,rawer,escape=0x0f "UNIX-CONNECT:${sock}"
}

cmd_clean() {
    if any_running; then
        error "VMs are still running. Stop them first."
    fi

    log "Cleaning up test topology work directory..."
    rm -rf "$WORK_DIR"
    log "Done. Run 'start' to recreate from scratch."
}

# =============================================================================
# Main
# =============================================================================

usage() {
    echo "Usage: $0 {start|stop|kill|status|console <vm-name>|clean}"
    echo ""
    echo "Commands:"
    echo "  start               Launch all four VMs"
    echo "  stop                Gracefully shut down all VMs"
    echo "  kill                Force-kill all VMs"
    echo "  status              Show VM status and access info"
    echo "  console <vm-name>   Attach to a VM's serial console"
    echo "  clean               Remove work directory (VMs must be stopped)"
    echo ""
    echo "VM names: encryptor-a, encryptor-b, alpine-a, alpine-b"
}

main() {
    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        kill)
            cmd_kill
            ;;
        status)
            cmd_status
            ;;
        console)
            local vm="${1:-}"
            if [[ -z "$vm" ]]; then
                error "Usage: $0 console <vm-name>"
            fi
            # Validate VM name
            local valid=false
            for v in "${VMS[@]}"; do
                if [[ "$v" == "$vm" ]]; then
                    valid=true
                    break
                fi
            done
            if [[ "$valid" != "true" ]]; then
                error "Unknown VM: ${vm}. Valid names: ${VMS[*]}"
            fi
            cmd_console "$vm"
            ;;
        clean)
            cmd_clean
            ;;
        -h|--help|help)
            usage
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
