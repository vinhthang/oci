# ADR 0041: In-Kernel WireGuard US VPN Server on GCP Host (`gce10`)

## Context
- **Need for US Egress IP Address**: Accessing US-restricted services, conducting geographic testing, and maintaining secure remote tunneling requires an authentic US-based IP address (`136.111.37.17`) without recurring subscription costs or privacy compromises associated with commercial third-party VPN providers.
- **Hardware Memory Boundary on `gce10`**: The host `gce10` (GCP e2-micro instance in us-central1) is strictly memory-capped at **1 GB RAM**. Heavy userspace VPN daemons or GUI-based VPN suites (such as OpenVPN, Pritunl, or WireGuard Docker wrappers) introduce unacceptable memory overhead and risk triggering the Linux OOM killer on existing K3s worker and Caddy edge services.
- **Preservation of Mesh Infrastructure**: The node `gce10` already operates WireGuard interface `wg0` (`10.10.0.4/24`) for inter-cloud K3s flannel routing with OCI and Hyper-V nodes. Any new VPN solution must not interfere with `wg0`, Flannel VXLAN, or existing host firewall configurations.

## Decision
1. **Deploy In-Kernel WireGuard Server on Interface `wg1`**:
   - Utilize native Linux in-kernel WireGuard via `wg-quick@wg1` on dedicated listening port `51820` (UDP).
   - Configure a dedicated, non-overlapping subnet `10.66.0.0/24` with server address `10.66.0.1/24` and client peer addresses starting at `10.66.0.2/32`.
2. **Firewall and Kernel Packet Forwarding**:
   - Enable persistent IPv4 and IPv6 packet forwarding via `/etc/sysctl.d/99-wireguard-forwarding.conf` (`net.ipv4.ip_forward = 1` and `net.ipv6.conf.all.forwarding = 1`).
   - Create GCP VPC firewall ingress rule `allow-wireguard-vpn` permitting `udp:51820` from `0.0.0.0/0` targeting instances tagged with `http-server`.
   - Apply automated `iptables` `POSTROUTING` NAT masquerade on `eth0` during `PostUp`/`PostDown` lifecycle events for `wg1`.
3. **Client Configuration & Onboarding Artifacts**:
   - Provide standard client configuration `wg1-client.conf` configured for full-tunnel internet routing (`AllowedIPs = 0.0.0.0/0, ::/0`) with upstream public DNS (`1.1.1.1, 8.8.8.8`) and `PersistentKeepalive = 25`.
   - Install `qrencode` on `gce10` to generate high-contrast ASCII/UTF-8 terminal QR codes (`wg1-client-qr.txt`) for immediate mobile scanning.

## Consequences
- **Zero Userspace Daemon Overhead**: In-kernel WireGuard runs within the Linux kernel space with negligible CPU and zero RAM consumption overhead, completely respecting `gce10`'s 1 GB RAM invariant.
- **Full US Egress Tunneling**: Client traffic routes seamlessly through `136.111.37.17`, masking client public IP addresses with a verified US egress IP.
- **Zero Impact on K3s and Cross-Cloud Mesh**: The existing `wg0` cross-cloud cluster overlay and Caddy edge reverse-proxy remain untouched and completely isolated from `wg1` road-warrior traffic.
- **Frictionless Road-Warrior Onboarding**: Immediate client onboarding via 1-click mobile camera QR scan (`wg1-client-qr.txt`) or desktop profile import (`wg1-client.conf`).
