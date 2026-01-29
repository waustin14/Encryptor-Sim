# Encryptor Simulator Image Build

This directory contains the tooling to build a qcow2 appliance image for the Encryptor Simulator, designed for deployment in Cisco Modeling Labs (CML).

## Overview

The build process produces a compressed qcow2 image (< 500MB) containing:

- **Base OS**: Alpine Linux 3.23.2 with musl libc
- **IPsec**: strongSwan 6.0.4
- **Firewall**: nftables 1.1.6
- **Backend**: Python 3.12, FastAPI, SQLAlchemy
- **Init**: OpenRC 0.63

## Quick Start

### Prerequisites

Build host requirements (Linux):

- Root access (for chroot, loop mount)
- `qemu-img` - QEMU disk image utility
- `parted` - Partition manipulation
- `mkfs.ext4` - Filesystem creation
- `syslinux` - Bootloader
- `curl` - For downloading Alpine

Install on Debian/Ubuntu:
```bash
sudo apt-get install qemu-utils parted e2fsprogs syslinux curl
```

Install on Fedora/RHEL:
```bash
sudo dnf install qemu-img parted e2fsprogs syslinux curl
```

### Build the Image

```bash
cd image/
sudo ./build-image.sh
```

Output files are created in `image/output/`:
- `encryptor-sim.qcow2` - Uncompressed qcow2 image
- `encryptor-sim.qcow2.gz` - Compressed image (< 500MB)

### Build Options

```bash
# Skip compression (faster build, larger output)
sudo ./build-image.sh --no-compress

# Keep work directory for debugging
sudo ./build-image.sh --keep-workdir
```
Note: `--no-compress` still performs a temporary gzip size check to enforce the <500MB compressed requirement.

## Importing into CML

### Step 1: Upload the Image

1. Log into CML as administrator
2. Navigate to **Tools > Image Management**
3. Click **Upload Image**
4. Select `encryptor-sim.qcow2` (uncompressed version)
5. Wait for upload to complete

### Step 2: Import Node Definition

1. Navigate to **Tools > Node Definitions**
2. Click **Import**
3. Select `config/cml-node.yaml`
4. Verify the node appears in the list

Alternative (advanced): If your CML workflow expects a root-level `*.node.yaml` definition,
use `encryptor-sim.node.yaml` from the project root. Keep both files aligned on resources
and interface ordering (MGMT, CT, PT).

### Step 3: Use in Topology

1. Create or open a topology
2. Find **Encryptor Simulator** in the device palette under **Security > Encryption**
3. Drag the node into your topology
4. Connect interfaces:
   - **MGMT (eth0)**: Connect to management network (DHCP)
   - **CT (eth1)**: Connect to encrypted network segment
   - **PT (eth2)**: Connect to plaintext network segment

## Network Interfaces

| Interface | Label | Purpose | Default |
|-----------|-------|---------|---------|
| eth0 | MGMT | Management, Web UI, API | DHCP |
| eth1 | CT | Crypto Text (encrypted) | Manual |
| eth2 | PT | Plain Text (unencrypted) | Manual |

## Resource Requirements

| Resource | Minimum | Maximum | Default |
|----------|---------|---------|---------|
| vCPU | 2 | 4 | 2 |
| RAM | 1 GB | 2 GB | 1 GB |
| Disk | 2 GB | 2 GB | 2 GB |

## Directory Structure

```
image/
├── build-image.sh        # Main build script
├── README.md             # This file
├── config/
│   └── cml-node.yaml     # CML node definition
├── openrc/
│   ├── encryptor-api         # FastAPI service
│   ├── encryptor-daemon      # Privileged daemon service
│   └── encryptor-namespaces  # Namespace initialization
├── rootfs/
│   ├── etc/
│   │   ├── hostname
│   │   └── network/
│   │       └── interfaces    # Network configuration
│   └── usr/
│       └── local/
│           └── bin/          # Helper scripts
├── output/               # Built images (created by build)
│   ├── encryptor-sim.qcow2
│   └── encryptor-sim.qcow2.gz
└── work/                 # Build workspace (temporary)
```

## Services

The appliance runs three OpenRC services:

1. **encryptor-namespaces** - Creates network namespaces for traffic isolation
2. **encryptor-daemon** - Privileged daemon for strongSwan/nftables ops
3. **encryptor-api** - FastAPI backend (depends on daemon)

Boot order is enforced via OpenRC dependencies.

## First Boot

1. The appliance boots and obtains DHCP on eth0
2. Access the web UI at `http://<mgmt-ip>:8000`
3. Default credentials are defined in the admin-access epic; if not configured, use the serial console to reset.
4. Configure CT and PT interfaces via the UI
5. Add IPsec peers and begin configuration

## Serial Console

Serial console is available for troubleshooting:
- Baud rate: 115200
- Data bits: 8
- Parity: None
- Stop bits: 1

In CML, right-click the node and select **Console** to access.

## Validation

The build script automatically validates:
- Image size < 500MB compressed
- qcow2 format integrity

Additional validation helper:
```bash
./validate-image.sh         # size + best-effort QEMU boot check
./validate-image.sh --no-boot
```

### Validation Notes (2026-01-27)

- Built on Ubuntu dev VM using `image/build-image.sh`
- Image and node definition copied into CML
- After importing updated image + node definition, node was drag-and-drop added to an existing lab
- Appliance booted successfully without intervention

Manual validation steps:
1. Boot image in QEMU: `qemu-system-x86_64 -m 1G -hda output/encryptor-sim.qcow2 -nographic`
2. Verify services start: `rc-status default`
3. Check interface configuration: `ip addr`
4. Verify API responds: `curl http://localhost:8000/api/v1/system/health`

## Troubleshooting

### Build Fails: Missing dependencies
Ensure all prerequisites are installed. The script checks for required tools at startup.

### Build Fails: Permission denied
The build script must run as root (`sudo ./build-image.sh`).

### Image too large
- Check for unneeded packages in the build script
- Ensure pip cache is cleaned
- Verify `--no-cache` flags are used with `apk add` and `pip install`

### Boot fails in CML
- Verify the qcow2 format: `qemu-img info output/encryptor-sim.qcow2`
- Check CML image upload completed successfully
- Ensure sufficient resources are allocated

## Development

To modify the image:

1. Edit files in `rootfs/` for filesystem overlay changes
2. Edit files in `openrc/` for service changes
3. Modify `build-image.sh` for package or configuration changes
4. Rebuild: `sudo ./build-image.sh --keep-workdir`
5. Test locally before CML import
