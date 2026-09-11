# ADR 0034: Add On-Premise Hyper-V Nodes via WireGuard

## Status
Accepted

## Context
Our current K3s cluster spans Oracle Cloud Infrastructure (OCI) across `arm10`, `amd10`, and `amd11`. We want to scale our worker nodes by introducing on-premise compute capacity to handle heavier workloads without incurring additional cloud costs. We have `pc-1` running Oracle Linux 10 VMs via Hyper-V locally.

However, these on-premise nodes reside behind a strict NAT/firewall and do not have public IP addresses. To securely join them to the existing K3s cluster, we need a reliable Layer 3 VPN mesh.

## Decision
1. **WireGuard VPN Hub**: We will deploy a WireGuard server on `amd10` (our public edge gateway on OCI).
2. **Subnet Allocation**: We will allocate `10.10.0.0/24` for the WireGuard VPN mesh.
3. **On-Premise Nodes**: We will configure the on-premise Hyper-V nodes (like `pc-1`) as WireGuard peers connecting to the `amd10` public endpoint. 
4. **Integration**: The on-premise nodes will receive an IP from the `10.10.0.0/24` subnet. We will allow this subnet to communicate with the internal VCN resources (`10.0.0.0/16`) via `amd10`'s masquerading and updated security lists.
5. **Cluster Expansion**: The on-premise nodes will be provisioned using Terraform (using native Hyper-V commands) and will join K3s as worker nodes.

## Consequences
- **Positive**: Seamlessly extends K3s compute to local on-premise hardware without exposing the local network.
- **Positive**: Reduces cloud compute expenditure by utilizing idle local resources.
- **Negative**: Adds networking overhead (WireGuard encapsulation) and dependency on the `amd10` gateway's uptime for hybrid connectivity.
