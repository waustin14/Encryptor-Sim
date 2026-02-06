# User Guide

This guide covers the core V1.0 workflows for operating the Encryptor Simulator from the management plane.

## Audience and Scope

Use this guide if you are configuring interfaces, IPsec peers, routes, and monitoring through the web UI or API. The appliance is intended to be managed only through the MGMT domain and HTTPS endpoint.

## Prerequisites

- Appliance deployed and reachable on the management network
- HTTPS access to `https://<mgmt-ip>:443`
- Administrator credentials
- Browser trust decision for the self-signed certificate

## Workflow Map

- Login at `/login` and complete first-use password change at `/change-password` when required
- Navigate operational views at `/dashboard`, `/interfaces`, `/peers`, and `/routes`
- Configure interfaces before peer/route operations
- Add IPsec peers, then add/update/delete routes tied to those peers
- Confirm tunnel and interface monitoring from dashboard and monitoring cards
- Logout when complete

## Step-by-Step Operations

### 1. Login (`/login`)

1. Open `https://<mgmt-ip>:443`.
2. Accept the self-signed certificate warning for trusted lab systems.
3. Sign in with an administrative account.
4. If prompted for first-use rotation, continue to `/change-password`.

Screenshot: `image/user-guide-login.png`

### 2. First Password Change (`/change-password`)

1. Enter current password.
2. Enter a new password with at least 8 characters.
3. Submit the change and confirm success.
4. Continue to `/dashboard`.

Screenshot: `image/user-guide-change-password.png`

### 3. Dashboard and Monitoring (`/dashboard`)

1. Review system and tunnel summary cards.
2. Validate tunnel states (`up`, `down`, `negotiating`) and recent telemetry.
3. Check interface statistics for expected traffic direction and counters.
4. Investigate warnings before making additional changes.

Screenshot: `image/user-guide-dashboard.png`

### 4. Configure Interfaces (`/interfaces`)

1. Open `/interfaces`.
2. Select CT, PT, or MGMT entry.
3. Set `ipAddress`, `netmask`, and `gateway`.
4. Save configuration and confirm applied/daemon status feedback.

Screenshot: `image/user-guide-interfaces.png`

### 5. Manage Peers (`/peers`)

1. Open `/peers`.
2. Add peer parameters: `name`, `remoteIp`, `psk`, `ikeVersion`, DPD/rekey fields, and `enabled`.
3. Save and confirm peer status (`ready`/`incomplete`).
4. Initiate tunnel from peer actions when operationally ready.
5. Update, disable, or delete peers as needed.

Screenshot: `image/user-guide-peers.png`

### 6. Manage Routes (`/routes`)

1. Open `/routes`.
2. Create route with `peerId` and `destinationCidr`.
3. Validate route list and optional peer-based filtering.
4. Update or delete routes during topology changes.

Screenshot: `image/user-guide-routes.png`

### 7. Logout

1. Use the UI logout control.
2. Confirm redirect to `/login`.
3. Close browser session on shared systems.

Screenshot: `image/user-guide-logout.png`

## Troubleshooting Basics

- Login fails: confirm username/password and TLS target host.
- API/UI auth failures: refresh session and re-login to obtain fresh JWT tokens.
- Tunnel not establishing: verify peer fields, routing, and IKE/ESP reachability.
- Stats not updating: check daemon availability and MGMT connectivity.

## Security Notes

- API and UI sessions are authenticated with JWT tokens.
- Treat access and refresh tokens as secrets and do not store them in shared logs.
- The HTTPS certificate is self-signed by default; verify the target host before accepting certificate warnings.
- Do not expose MGMT plane access outside approved administrative networks.

## Screenshot Maintenance

Store screenshots under `image/` with clear names by workflow step. When UI changes, update screenshots in the same pull request as related UX changes.

Recommended screenshot file set:

- `image/user-guide-login.png`
- `image/user-guide-change-password.png`
- `image/user-guide-dashboard.png`
- `image/user-guide-interfaces.png`
- `image/user-guide-peers.png`
- `image/user-guide-routes.png`
- `image/user-guide-logout.png`
