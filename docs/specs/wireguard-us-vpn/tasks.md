# Implementation Tasks: WireGuard US VPN Server on GCP Host (`gce10`)

**Feature ID**: `wireguard-us-vpn`  
**Status**: Complete  

---

## Task Checklist

- [x] **Task 1: Google Cloud VPC Firewall Rule Provisioning**
  - Run `gcloud compute firewall-rules create allow-wireguard-vpn` in `vietcalendar`.
  - Allow `udp:51820` targeting `http-server` tag.
  - Traceability: `REQ-004`

- [x] **Task 2: Linux IPv4 Forwarding & Sysctl Persistence on `gce10`**
  - Create `/etc/sysctl.d/99-wireguard-forwarding.conf` with `net.ipv4.ip_forward = 1`.
  - Apply immediately via `sysctl --system`.
  - Traceability: `REQ-003`

- [x] **Task 3: Key Generation & Server Configuration (`wg1.conf`)**
  - Generate server private/public key pair: `server_private.key`, `server_public.key`.
  - Generate client private/public key pair: `client_private.key`, `client_public.key`.
  - Deploy `/etc/wireguard/wg1.conf` with `chmod 600`.
  - Traceability: `REQ-001`, `REQ-002`, `REQ-003`

- [x] **Task 4: Systemd Service Enablement (`wg-quick@wg1`)**
  - Enable and start `systemctl enable --now wg-quick@wg1`.
  - Verify interface status with `wg show wg1`.
  - Traceability: `REQ-001`, `REQ-002`

- [x] **Task 5: Client Configuration & QR Code Generation**
  - Generate client configuration file `wg1-client.conf`.
  - Generate terminal-compatible QR code via `qrencode -t ansiutf8`.
  - Traceability: `REQ-005`

- [x] **Task 6: Verification & End-to-End Testing**
  - Verify UDP 51820 port listening on `gce10`.
  - Verify iptables NAT masquerade rules in `POSTROUTING`.
  - Verify client handshake and outbound IP `136.111.37.17`.
  - Traceability: `REQ-001` through `REQ-005`

- [x] **Task 7: ADR-0041 & Architecture Documentation**
  - Author `docs/adr/0041-wireguard-us-vpn-server-on-gce10.md`.
  - Register in `docs/README.md`.
  - Commit and push to Git.
  - Traceability: `REQ-006`
