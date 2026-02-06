# Ports and Protocols

This reference lists externally relevant protocols for V1.0 operation and integration planning.

## Management Access

- **HTTPS (TCP 443)**  
  Purpose: UI and REST API access on the MGMT domain.  
  Security implication: self-signed TLS by default; clients must validate host identity before trusting certificate warnings.

## VPN Control/Data Plane

- **IKEv2 (UDP 500)**  
  Purpose: IPsec key exchange negotiation for site-to-site peers.
- **NAT-T (UDP 4500)**  
  Purpose: IPsec negotiation and encapsulated ESP across NAT boundaries.
- **ESP (IP protocol 50)**  
  Purpose: encrypted payload transport for established tunnels.

Security implication: these protocols should be restricted to approved peer addresses and required transport domains only. Do not expose them on management-only networks unless explicitly required by deployment design.

## Real-Time Monitoring

- **WebSocket over TLS (wss on TCP 443)**  
  Endpoint: `/api/v1/ws` on MGMT HTTPS listener.  
  Purpose: authenticated push updates for tunnel and interface telemetry.

## Directionality and Domain Applicability

- Inbound MGMT: HTTPS and WebSocket client connections from administrators/automation.
- CT/PT relevant traffic: IKE/ESP paths between configured peer endpoints.
- Administrative actions originate from MGMT but affect CT/PT runtime behavior through controlled daemon operations.

## Lab Firewall Planning Notes

- Allow MGMT HTTPS only from trusted admin segments.
- Allow UDP 500/4500 and ESP between participating tunnel endpoints.
- Deny unrelated inbound services by default and validate policy with post-change connectivity tests.

## Validation Checklist

- Confirm HTTPS (`TCP 443`) is reachable only from approved management source networks.
- Confirm IKE (`UDP 500`) and NAT-T (`UDP 4500`) are reachable only between intended peer endpoints.
- Confirm ESP (`IP protocol 50`) is allowed only where site-to-site encryption is required.
- Confirm WebSocket monitoring endpoint (`/api/v1/ws`) is reachable only over authenticated MGMT HTTPS sessions.
- Confirm deny-by-default posture remains for non-documented ports/protocols after policy changes.
