# ADR-0030: Revert K3s Flannel Backend to VXLAN (Remove WireGuard-Native)

## Status
🟢 Accepted

## Context
In ADR-0025, we switched the K3s Flannel backend from `vxlan` to `wireguard-native` to resolve cross-node routing issues specifically for our external physical node (`oracle10`) over Tailscale.
With the removal of `oracle10` (ADR-0029), our cluster architecture is now strictly contained within Oracle Cloud Infrastructure (OCI) and GCP, using Oracle VCN and standard networking. The `wireguard-native` backend adds unnecessary encryption overhead to the high-speed internal Oracle VCN and is no longer required for cross-cloud compatibility since we leverage Tailscale for the GCP node `gce10` and internal VCN for the rest.

## Decision
1. **Revert Flannel Backend**: Revert K3s Flannel backend from `wireguard-native` back to the default `vxlan`. 
2. **Remove Network Rules**: Remove the ingress security rule for UDP port 51820 (WireGuard Mesh VPN) from the OCI Terraform `network.tf` file to close the unused port.

## Consequences
- **Positive**: Reduces CPU overhead on K3s nodes caused by in-cluster native WireGuard encryption.
- **Positive**: Simplifies the network security surface by removing the exposed UDP 51820 port.
- **Negative**: Traffic between K3s pods within the cluster will use unencrypted VXLAN, which is acceptable since our internal nodes (`arm10`, `amd11`) reside in a Private Subnet (ADR-0013). (Cross-cloud Tailscale traffic remains encrypted by Tailscale itself).
