# Functional Specification: WireGuard US VPN Server on GCP Host (`gce10`)

**Feature ID**: `wireguard-us-vpn`  
**Status**: Proposed (Pending Human Approval)  
**Target Host**: `gce10` (`gce-free-vm`, GCP US-Central1, Public IPv4: `136.111.37.17`)  
**Scope**: Host Networking / GCP Cloud Firewall / WireGuard VPN  

---

## 1. Problem Statement & Context

The user requires a secure personal VPN server running on the Google Cloud Platform host (`gce10`) located in the United States (`us-central1`, Iowa). Connecting through this VPN server must route full-tunnel internet traffic through `gce10`'s public IPv4 address (`136.111.37.17`), presenting a genuine US IP address to external websites and services.

Host `gce10` is an `e2-micro` Google Cloud Always Free VM strictly capped at **1 GB RAM** and currently functions as:
1. A K3s worker node running a `vector` log harvester daemonset.
2. A dual-edge static cache gateway running Caddy.
3. A WireGuard mesh client on interface `wg0` (`10.10.0.4/24`) connecting to `amd10` in Tokyo.

The solution must operate with near-zero memory footprint, preserve existing `wg0` and K3s cluster networking, and survive reboots cleanly.

---

## 2. Normative Requirements

### `REQ-001`: Dedicated Interface & Port Isolation
- The VPN server MUST operate on a dedicated WireGuard interface named `wg1` (or `wg-vpn0`).
- The VPN server MUST listen on static UDP port `51820`.
- The VPN interface MUST use a dedicated non-overlapping subnet: `10.66.0.0/24` (Server: `10.66.0.1/24`, Client 1: `10.66.0.2/32`).
- The VPN server MUST NOT modify, alter, or interrupt existing interface `wg0` (`10.10.0.0/24`) or K3s Flannel interfaces (`cni0`, `flannel.1`).

### `REQ-002`: Persistent In-Kernel Execution
- The VPN server MUST run natively in the Linux kernel via `/usr/bin/wg` and `/usr/bin/wg-quick`.
- The service MUST be managed by standard systemd unit `wg-quick@wg1` enabled at boot (`systemctl enable wg-quick@wg1`).
- The solution MUST NOT run long-running userspace daemon containers or heavy Node.js/Go proxies to respect the 1 GB RAM invariant on `gce10`.

### `REQ-003`: Full-Tunnel IPv4 Forwarding & NAT Masquerading
- Linux IPv4 packet forwarding MUST be enabled and persisted in `/etc/sysctl.d/99-wireguard-forwarding.conf` (`net.ipv4.ip_forward = 1`).
- `iptables` rules MUST be declared in `PostUp` and `PostDown` of `/etc/wireguard/wg1.conf`:
  - Allow UDP traffic on port `51820` (`-A INPUT -p udp --dport 51820 -j ACCEPT`).
  - Allow bidirectional forwarding for `wg1` (`-A FORWARD -i wg1 -j ACCEPT`, `-A FORWARD -o wg1 -m state --state RELATED,ESTABLISHED -j ACCEPT`).
  - Masquerade outbound packets leaving physical interface `eth0` from `10.66.0.0/24` (`-t nat -A POSTROUTING -o eth0 -s 10.66.0.0/24 -j MASQUERADE`).

### `REQ-004`: Google Cloud VPC Ingress Firewall Rule
- An ingress firewall rule named `allow-wireguard-vpn` MUST be provisioned in Google Cloud project `vietcalendar` on network `default`.
- The rule MUST allow incoming protocol `udp` on port `51820` from source range `0.0.0.0/0`.
- The rule MUST target `gce-free-vm` via network tag `http-server` (or direct instance target).

### `REQ-005`: Client Configuration & Mobile QR Code Delivery
- The system MUST generate a cryptographically valid client key pair (`client_private.key`, `client_public.key`).
- The system MUST output a complete ready-to-use client `.conf` file configured for full-tunnel routing:
  - `Endpoint = 136.111.37.17:51820`
  - `AllowedIPs = 0.0.0.0/0, ::/0`
  - `DNS = 1.1.1.1, 8.8.8.8`
  - `PersistentKeepalive = 25`
- The system MUST render an ANSI UTF-8 QR code in the terminal using `qrencode` for instant 1-tap camera scanning into WireGuard mobile apps (iOS / Android).

### `REQ-006`: Governance & ADR Registry
- An Architecture Decision Record `ADR-0041: WireGuard US VPN Server on GCP Host (gce10)` MUST be authored in `docs/adr/0041-wireguard-us-vpn-server-on-gce10.md` following standard Nygard format.
- `ADR-0041` MUST be registered in `docs/README.md`.
