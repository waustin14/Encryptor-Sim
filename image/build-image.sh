#!/usr/bin/env bash
#
# build-image.sh - Build qcow2 appliance image for Encryptor Simulator
#
# Produces a compressed qcow2 image < 500MB containing:
# - Alpine Linux 3.23.x base
# - strongSwan, nftables, Python 3.12
# - Encryptor Simulator backend and daemon
# - OpenRC services configured for auto-start
#
# Usage: sudo ./build-image.sh [--no-compress] [--keep-workdir]
#
# Requirements:
# - Root privileges (for chroot, loop mount)
# - qemu-img, qemu-nbd (or losetup), mkfs.ext4, syslinux
# - Internet access for Alpine package downloads

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Alpine version
ALPINE_VERSION="3.23"
ALPINE_RELEASE="3.23.2"
ALPINE_ARCH="x86_64"
ALPINE_MIRROR="https://dl-cdn.alpinelinux.org/alpine"

# Image configuration
IMAGE_NAME="encryptor-sim"
IMAGE_SIZE="2G"
MAX_COMPRESSED_SIZE=$((500 * 1024 * 1024))  # 500MB in bytes

# Directories
WORK_DIR="${SCRIPT_DIR}/work"
OUTPUT_DIR="${SCRIPT_DIR}/output"
ROOTFS_OVERLAY="${SCRIPT_DIR}/rootfs"
OPENRC_DIR="${SCRIPT_DIR}/openrc"
CONFIG_DIR="${SCRIPT_DIR}/config"

# Output files
RAW_IMAGE="${WORK_DIR}/${IMAGE_NAME}.raw"
QCOW2_IMAGE="${OUTPUT_DIR}/${IMAGE_NAME}.qcow2"
COMPRESSED_IMAGE="${OUTPUT_DIR}/${IMAGE_NAME}.qcow2.gz"

# Build options
COMPRESS=true
KEEP_WORKDIR=false

# =============================================================================
# Argument parsing
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-compress)
            COMPRESS=false
            shift
            ;;
        --keep-workdir)
            KEEP_WORKDIR=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--no-compress] [--keep-workdir]"
            echo ""
            echo "Options:"
            echo "  --no-compress    Skip gzip compression of final image"
            echo "  --keep-workdir   Keep work directory after build"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Helper functions
# =============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[ERROR] $*" >&2
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (for chroot and mount operations)"
    fi
}

check_dependencies() {
    local deps=(
        qemu-img
        mkfs.ext4
        parted
        syslinux
        curl
        losetup
        partprobe
        mount
        umount
        mountpoint
        tar
        gzip
        sha256sum
        extlinux
    )
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing[*]}"
    fi
}

cleanup() {
    log "Cleaning up..."

    # Unmount any mounted filesystems
    if mountpoint -q "${WORK_DIR}/mnt" 2>/dev/null; then
        umount -R "${WORK_DIR}/mnt" 2>/dev/null || true
    fi

    # Detach loop device
    if [[ -n "${LOOP_DEV:-}" ]]; then
        losetup -d "$LOOP_DEV" 2>/dev/null || true
    fi

    # Remove work directory unless --keep-workdir
    if [[ "$KEEP_WORKDIR" == "false" && -d "$WORK_DIR" ]]; then
        rm -rf "$WORK_DIR"
    fi
}

trap cleanup EXIT

# =============================================================================
# Build steps
# =============================================================================

create_directories() {
    log "Creating build directories..."
    mkdir -p "$WORK_DIR" "$OUTPUT_DIR" "${WORK_DIR}/mnt" "${WORK_DIR}/alpine"
}

download_alpine() {
    local minirootfs="alpine-minirootfs-${ALPINE_RELEASE}-${ALPINE_ARCH}.tar.gz"
    local url="${ALPINE_MIRROR}/v${ALPINE_VERSION}/releases/${ALPINE_ARCH}/${minirootfs}"
    local tarball="${WORK_DIR}/${minirootfs}"

    if [[ -f "$tarball" ]]; then
        log "Alpine minirootfs already downloaded"
        return
    fi

    log "Downloading Alpine Linux ${ALPINE_RELEASE} minirootfs..."
    curl -fSL -o "$tarball" "$url" || error "Failed to download Alpine minirootfs"

    log "Verifying download..."
    # Download SHA256 checksum
    curl -fsSL -o "${tarball}.sha256" "${url}.sha256" || log "Warning: Could not download checksum"

    if [[ -f "${tarball}.sha256" ]]; then
        (cd "$WORK_DIR" && sha256sum -c "${minirootfs}.sha256") || error "Checksum verification failed"
    fi
}

create_disk_image() {
    log "Creating ${IMAGE_SIZE} disk image..."

    # Create raw disk image
    qemu-img create -f raw "$RAW_IMAGE" "$IMAGE_SIZE"

    # Create partition table and single partition
    log "Creating partition table..."
    parted -s "$RAW_IMAGE" mklabel msdos
    parted -s "$RAW_IMAGE" mkpart primary ext4 1MiB 100%
    parted -s "$RAW_IMAGE" set 1 boot on
}

setup_loop_device() {
    log "Setting up loop device..."

    LOOP_DEV=$(losetup --find --show --partscan "$RAW_IMAGE")
    log "Loop device: $LOOP_DEV"

    # Wait for partition device to appear
    sleep 1

    PART_DEV="${LOOP_DEV}p1"
    if [[ ! -b "$PART_DEV" ]]; then
        # Some systems use different naming
        PART_DEV="${LOOP_DEV}1"
    fi

    if [[ ! -b "$PART_DEV" ]]; then
        partprobe "$LOOP_DEV"
        sleep 1
        PART_DEV="${LOOP_DEV}p1"
    fi

    [[ -b "$PART_DEV" ]] || error "Partition device not found: $PART_DEV"
    log "Partition device: $PART_DEV"
}

format_and_mount() {
    log "Formatting partition as ext4..."
    # Disable ext4 features that syslinux may not support
    mkfs.ext4 -L "encryptor-root" -O ^64bit,^metadata_csum "$PART_DEV"

    log "Mounting filesystem..."
    mount "$PART_DEV" "${WORK_DIR}/mnt"
}

extract_alpine() {
    local minirootfs="alpine-minirootfs-${ALPINE_RELEASE}-${ALPINE_ARCH}.tar.gz"
    local tarball="${WORK_DIR}/${minirootfs}"

    log "Extracting Alpine rootfs..."
    tar -xzf "$tarball" -C "${WORK_DIR}/mnt"
}

configure_alpine() {
    local mnt="${WORK_DIR}/mnt"

    log "Configuring Alpine Linux..."

    # Set up resolv.conf for package installation
    cp /etc/resolv.conf "${mnt}/etc/resolv.conf"

    # Configure Alpine repositories
    cat > "${mnt}/etc/apk/repositories" << EOF
${ALPINE_MIRROR}/v${ALPINE_VERSION}/main
${ALPINE_MIRROR}/v${ALPINE_VERSION}/community
EOF

    # Mount required filesystems for chroot
    mount -t proc proc "${mnt}/proc"
    mount -t sysfs sysfs "${mnt}/sys"
    mount -t devtmpfs devtmpfs "${mnt}/dev"
    mount -t devpts devpts "${mnt}/dev/pts"

    # Update package index
    log "Updating package index..."
    chroot "$mnt" apk update

    # Install required packages
    log "Installing packages..."
    chroot "$mnt" apk add --no-cache \
        alpine-base \
        linux-lts \
        linux-firmware-none \
        syslinux \
        openrc \
        e2fsprogs \
        util-linux \
        python3 \
        py3-pip \
        strongswan \
        strongswan-openrc \
        nftables \
        iproute2 \
        dhcpcd \
        ripgrep \
        openssh-server \
        ca-certificates \
        tzdata \
        openssl

    # Install additional Python packages via pip (musl-compatible)
    log "Installing Python packages..."
    chroot "$mnt" pip3 install --break-system-packages --no-cache-dir \
        alembic \
        aiosqlite \
        python-jose \
        passlib \
        bcrypt

    # Set hostname
    echo "encryptor-sim" > "${mnt}/etc/hostname"

    # Configure hosts file
    cat > "${mnt}/etc/hosts" << EOF
127.0.0.1   localhost encryptor-sim
::1         localhost encryptor-sim
EOF

    # Set timezone
    ln -sf /usr/share/zoneinfo/UTC "${mnt}/etc/localtime"

    # Configure inittab for serial console
    cat > "${mnt}/etc/inittab" << 'EOF'
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default

# Serial console
ttyS0::respawn:/sbin/getty -L ttyS0 115200 vt100

# Standard consoles
tty1::respawn:/sbin/getty 38400 tty1
tty2::respawn:/sbin/getty 38400 tty2

::shutdown:/sbin/openrc shutdown
EOF

    # Enable serial console in securetty
    echo "ttyS0" >> "${mnt}/etc/securetty"

    # Configure fstab
    cat > "${mnt}/etc/fstab" << 'EOF'
# <fs>      <mountpoint>   <type>  <opts>              <dump/pass>
LABEL=encryptor-root  /        ext4    defaults,noatime    0 1
proc        /proc          proc    defaults            0 0
sysfs       /sys           sysfs   defaults            0 0
devpts      /dev/pts       devpts  defaults            0 0
tmpfs       /tmp           tmpfs   defaults,nosuid,nodev 0 0
tmpfs       /run           tmpfs   defaults,nosuid,nodev,mode=755 0 0
EOF

    # Enable essential services
    chroot "$mnt" rc-update add devfs sysinit
    chroot "$mnt" rc-update add dmesg sysinit
    chroot "$mnt" rc-update add mdev sysinit
    chroot "$mnt" rc-update add hwdrivers sysinit

    chroot "$mnt" rc-update add modules boot
    chroot "$mnt" rc-update add sysctl boot
    chroot "$mnt" rc-update add hostname boot
    chroot "$mnt" rc-update add bootmisc boot
    chroot "$mnt" rc-update add networking boot

    # Note: stock strongswan service is NOT added here — our custom
    # encryptor-strongswan service wraps charon to run inside ns_ct.
    chroot "$mnt" rc-update add sshd default

    chroot "$mnt" rc-update add mount-ro shutdown
    chroot "$mnt" rc-update add killprocs shutdown
    chroot "$mnt" rc-update add savecache shutdown

    # Set root password (will be changed on first login)
    echo "root:encryptor" | chroot "$mnt" chpasswd

    log "Alpine configuration complete"
}

generate_tls_certificate() {
    local mnt="${WORK_DIR}/mnt"

    log "Generating self-signed TLS certificate..."

    # Create TLS directory
    mkdir -p "${mnt}/etc/encryptor-sim/tls"

    # Generate self-signed certificate (valid for 10 years)
    chroot "$mnt" openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout /etc/encryptor-sim/tls/server.key \
        -out /etc/encryptor-sim/tls/server.crt \
        -days 3650 \
        -subj "/CN=encryptor-sim/O=Encryptor Simulator/C=US"

    # Set restrictive permissions on private key
    chmod 0600 "${mnt}/etc/encryptor-sim/tls/server.key"
    chmod 0644 "${mnt}/etc/encryptor-sim/tls/server.crt"

    log "TLS certificate generated successfully"
}

generate_psk_encryption_key() {
    local mnt="${WORK_DIR}/mnt"

    log "Generating PSK encryption key..."

    mkdir -p "${mnt}/etc/encryptor-sim"
    chroot "$mnt" openssl rand -base64 32 > "${mnt}/etc/encryptor-sim/psk.key"
    chmod 0600 "${mnt}/etc/encryptor-sim/psk.key"

    log "PSK encryption key generated successfully"
}

generate_jwt_secret_key() {
    local mnt="${WORK_DIR}/mnt"

    log "Generating JWT secret key..."

    mkdir -p "${mnt}/etc/encryptor-sim"
    chroot "$mnt" openssl rand -hex 32 > "${mnt}/etc/encryptor-sim/jwt.key"
    chmod 0600 "${mnt}/etc/encryptor-sim/jwt.key"

    log "JWT secret key generated successfully"
}

build_frontend() {
    if [[ ! -d "${PROJECT_ROOT}/frontend" ]]; then
        log "Warning: frontend directory not found, skipping build"
        return 0
    fi

    if ! command -v npm >/dev/null 2>&1; then
        log "Warning: npm not available, skipping frontend build"
        return 0
    fi

    log "Building frontend production bundle..."
    if [[ -f "${PROJECT_ROOT}/frontend/package-lock.json" ]]; then
        (cd "${PROJECT_ROOT}/frontend" && npm ci) || error "Failed to install frontend dependencies"
    else
        (cd "${PROJECT_ROOT}/frontend" && npm install) || error "Failed to install frontend dependencies"
    fi
    (cd "${PROJECT_ROOT}/frontend" && npm run build) || error "Frontend build failed"
}

install_application() {
    local mnt="${WORK_DIR}/mnt"

    log "Installing Encryptor Simulator application..."

    # Create application directories
    mkdir -p "${mnt}/opt/encryptor-sim"
    mkdir -p "${mnt}/var/lib/encryptor-sim"
    mkdir -p "${mnt}/var/log/encryptor-sim"
    mkdir -p "${mnt}/etc/encryptor-sim"

    # Copy backend application
    if [[ -d "${PROJECT_ROOT}/backend" ]]; then
        log "Copying backend application..."
        cp -r "${PROJECT_ROOT}/backend" "${mnt}/opt/encryptor-sim/"

        # Install backend dependencies
        if [[ -f "${PROJECT_ROOT}/backend/requirements.txt" ]]; then
            log "Installing backend dependencies..."
            chroot "$mnt" pip3 install --break-system-packages --no-cache-dir \
                -r /opt/encryptor-sim/backend/requirements.txt 2>/dev/null || \
                error "Failed to install backend dependencies"
        fi
    else
        log "Warning: backend directory not found, creating placeholder"
        mkdir -p "${mnt}/opt/encryptor-sim/backend"
    fi

    build_frontend

    # Copy frontend build (if exists)
    # Vite outputs directly to backend/static/ (configured in frontend/vite.config.ts)
    mkdir -p "${mnt}/opt/encryptor-sim/backend/static"
    if [[ -d "${PROJECT_ROOT}/backend/static" ]]; then
        log "Copying frontend build..."
        cp -r "${PROJECT_ROOT}/backend/static/." "${mnt}/opt/encryptor-sim/backend/static/"
    else
        log "Warning: frontend build not found, skipping"
    fi
}

install_rootfs_overlay() {
    local mnt="${WORK_DIR}/mnt"

    log "Installing rootfs overlay..."

    if [[ -d "$ROOTFS_OVERLAY" && "$(ls -A "$ROOTFS_OVERLAY" 2>/dev/null)" ]]; then
        cp -a "${ROOTFS_OVERLAY}/." "${mnt}/"
    else
        log "Warning: No rootfs overlay files found"
    fi
}

install_openrc_services() {
    local mnt="${WORK_DIR}/mnt"

    log "Installing OpenRC services..."

    if [[ -d "$OPENRC_DIR" && "$(ls -A "$OPENRC_DIR" 2>/dev/null)" ]]; then
        for service in "${OPENRC_DIR}"/*; do
            if [[ -f "$service" ]]; then
                local svc_name=$(basename "$service")
                log "Installing service: $svc_name"
                install -m 755 "$service" "${mnt}/etc/init.d/${svc_name}"
                chroot "$mnt" rc-update add "$svc_name" default
            fi
        done
    else
        log "Warning: No OpenRC service files found"
    fi
}

install_bootloader() {
    local mnt="${WORK_DIR}/mnt"

    log "Installing syslinux bootloader..."

    # Install syslinux MBR
    dd if="${mnt}/usr/share/syslinux/mbr.bin" of="$LOOP_DEV" bs=440 count=1 conv=notrunc

    # Create syslinux config directory
    mkdir -p "${mnt}/boot/syslinux"

    # Copy syslinux modules (paths vary by distro)
    local syslinux_dirs=(
        "${mnt}/usr/share/syslinux"
        "${mnt}/usr/lib/syslinux/bios"
        "${mnt}/usr/share/syslinux/bios"
    )

    for dir in "${syslinux_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            cp "${dir}/"*.c32 "${mnt}/boot/syslinux/" 2>/dev/null || true
        fi
    done

    # Ensure ldlinux.c32 is present (required by syslinux)
    if [[ ! -f "${mnt}/boot/syslinux/ldlinux.c32" ]]; then
        error "syslinux module ldlinux.c32 not found; bootloader will not start"
    fi

    # Determine kernel version
    local kernel_version=$(ls "${mnt}/lib/modules" | head -1)

    # Create syslinux configuration
    cat > "${mnt}/boot/syslinux/syslinux.cfg" << EOF
DEFAULT encryptor
PROMPT 0
TIMEOUT 30

LABEL encryptor
    LINUX /boot/vmlinuz-lts
    INITRD /boot/initramfs-lts
    APPEND root=LABEL=encryptor-root rootfstype=ext4 console=tty0 console=ttyS0,115200n8 quiet
EOF

    # Install syslinux to partition
    chroot "$mnt" extlinux --install /boot/syslinux

    if [[ ! -f "${mnt}/boot/syslinux/ldlinux.sys" ]]; then
        error "syslinux loader ldlinux.sys not found after extlinux install"
    fi
}

cleanup_chroot() {
    local mnt="${WORK_DIR}/mnt"

    log "Cleaning up chroot environment..."

    # Remove resolv.conf (will be configured by DHCP)
    rm -f "${mnt}/etc/resolv.conf"

    # Clean package cache
    chroot "$mnt" apk cache clean 2>/dev/null || true
    rm -rf "${mnt}/var/cache/apk/"*

    # Remove pip cache
    rm -rf "${mnt}/root/.cache"

    # Unmount special filesystems
    umount "${mnt}/dev/pts" 2>/dev/null || true
    umount "${mnt}/dev" 2>/dev/null || true
    umount "${mnt}/sys" 2>/dev/null || true
    umount "${mnt}/proc" 2>/dev/null || true
}

convert_to_qcow2() {
    log "Unmounting filesystem..."
    umount "${WORK_DIR}/mnt"

    log "Detaching loop device..."
    losetup -d "$LOOP_DEV"
    unset LOOP_DEV

    log "Converting to qcow2 format..."
    qemu-img convert -f raw -O qcow2 -c "$RAW_IMAGE" "$QCOW2_IMAGE"

    # Remove raw image to save space
    rm -f "$RAW_IMAGE"
}

compress_image() {
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing qcow2 image..."
        gzip -9 -c "$QCOW2_IMAGE" > "$COMPRESSED_IMAGE"
    fi
}

validate_image() {
    log "Validating image..."

    local check_file="$QCOW2_IMAGE"
    local size_label="uncompressed"

    local temp_check_file=""

    if [[ "$COMPRESS" == "true" && -f "$COMPRESSED_IMAGE" ]]; then
        check_file="$COMPRESSED_IMAGE"
        size_label="compressed"
    elif [[ "$COMPRESS" == "false" ]]; then
        log "Compression disabled; creating temporary gzip for size validation..."
        temp_check_file="${WORK_DIR}/size-check.qcow2.gz"
        gzip -9 -c "$QCOW2_IMAGE" > "$temp_check_file"
        check_file="$temp_check_file"
        size_label="compressed (temp)"
    fi

    local size=$(stat -f%z "$check_file" 2>/dev/null || stat -c%s "$check_file")
    local size_mb=$((size / 1024 / 1024))

    log "Image size (${size_label}): ${size_mb}MB"

    if [[ $size -gt $MAX_COMPRESSED_SIZE ]]; then
        error "Image size (${size_mb}MB) exceeds maximum (500MB)"
    fi

    log "Image validation passed"

    if [[ -n "$temp_check_file" && -f "$temp_check_file" ]]; then
        rm -f "$temp_check_file"
    fi

    # Display image info
    log "Build complete!"
    echo ""
    echo "Output files:"
    echo "  qcow2: $QCOW2_IMAGE"
    if [[ "$COMPRESS" == "true" ]]; then
        echo "  compressed: $COMPRESSED_IMAGE (${size_mb}MB)"
    fi
    echo ""
    echo "Image info:"
    qemu-img info "$QCOW2_IMAGE"
}

# =============================================================================
# Main
# =============================================================================

main() {
    log "Starting Encryptor Simulator image build"
    log "Alpine Linux: ${ALPINE_RELEASE}"
    log "Target size: < 500MB compressed"

    check_root
    check_dependencies

    create_directories
    download_alpine
    create_disk_image
    setup_loop_device
    format_and_mount
    extract_alpine
    configure_alpine
    install_application
    generate_tls_certificate
    generate_psk_encryption_key
    generate_jwt_secret_key
    install_rootfs_overlay
    install_openrc_services
    install_bootloader
    cleanup_chroot
    convert_to_qcow2
    compress_image
    validate_image

    log "Build completed successfully"
}

main "$@"
