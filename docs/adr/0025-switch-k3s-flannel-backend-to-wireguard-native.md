# 25. Switch K3s Flannel Backend to Wireguard-Native

Date: 2026-08-29

## Status
Deprecated (Superseded by ADR-0030)

## Context
In ADR-0020, we optimized the local network throughput between `arm10` and `amd11` by removing Tailscale as the primary K3s network interface. This forced K3s to use the high-speed Oracle VCN (`eth0` / `enp0s6`) as the internal node IP.
However, this caused a severe routing black hole for our external worker node (`oracle10`), which relies entirely on Tailscale. Because the default Flannel `vxlan` interface (`flannel.1`) strictly binds to the physical interface associated with the internal node IP, it refused to process encapsulated Pod-to-Pod packets arriving over `tailscale0`. This broke cluster DNS and cross-node communication for pods on `oracle10`, effectively blocking the Apache Pulsar deployment.

## Decision
We switched the K3s Flannel backend from `vxlan` to `wireguard-native`.
The WireGuard backend creates a `flannel-wg` interface that operates purely at Layer 3 (UDP port 51820) and is not strictly bound to a single underlying hardware interface like VXLAN. This allows encrypted Flannel packets to traverse both the Oracle VCN and the Tailscale overlay seamlessly.

## Consequences
- **Positive**: Pods on the external `oracle10` node can now communicate perfectly with CoreDNS and workloads on the internal nodes.
- **Positive**: Cross-cloud pod traffic is automatically encrypted by WireGuard natively within K3s, providing an additional layer of security.
- **Negative**: Adds slight encryption overhead to the high-speed Oracle VCN link, though WireGuard is highly performant.
