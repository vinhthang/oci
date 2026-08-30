---
title: "The Failure and Rollback of a Tailscale-Powered Hybrid K3s Cluster"
date: 2026-08-30T19:30:00+07:00
draft: false
tags: ["Kubernetes", "K3s", "Tailscale", "Oracle Cloud", "WireGuard", "Networking", "Post-Mortem"]
categories: ["DevOps", "Cloud Architecture"]
author: "Thang Hoang"
showToc: true
TocOpen: true
---

# The Ambition: A Hybrid-Cloud K3s Cluster

When building out the underlying infrastructure for `vinhthang.dev`, I had a bold idea: what if I could seamlessly blend Oracle Cloud Infrastructure (OCI) instances with external, high-RAM physical nodes into a single, cohesive Kubernetes cluster? 

The goal was to leverage a beefy 32GB RAM external node (which we called `oracle10`) to host heavy Java microservices and stateful applications (like a PostgreSQL replica and Apache Pulsar), while keeping the control plane firmly rooted in my OCI Always Free `arm10` instance.

To bridge the gap across the public internet, I reached for **Tailscale**. Tailscale's zero-config WireGuard mesh seemed like the perfect solution to create a secure, flat network overlay for K3s. 

It worked... until it didn't. This is the story of why injecting an external node over a Tailscale WAN into a K3s cluster became a networking nightmare, and why I ultimately had to rip it out.

## The Architecture

The initial setup was elegant on paper:
1. **Control Plane (`arm10`)**: Running in OCI, serving the K3s API.
2. **Worker Node (`oracle10`)**: An external physical machine, joined to the cluster via Tailscale's IP space (`100.x.x.x`).
3. **Flannel CNI**: Configured to route Pod-to-Pod traffic strictly over `--flannel-iface tailscale0`.

## The Cracks Begin to Show (Routing Blackholes)

The first major issue emerged when I tried to optimize local network throughput. 
Routing *all* traffic through `tailscale0` meant that even pods communicating locally within the Oracle VCN (between `arm10` and `amd11`) were being pushed through the Tailscale encryption overhead, severely throttling bandwidth.

To fix this, I dropped Tailscale as the primary K3s interface, forcing K3s to use the high-speed Oracle VCN (`eth0`) as the internal node IP. But this immediately broke the cluster.

Because the default Flannel `vxlan` interface strictly binds to the physical interface associated with the internal node IP, it refused to process encapsulated Pod-to-Pod packets arriving over `tailscale0` from `oracle10`. Pods on the external node lost cluster DNS and cross-node communication entirely. My Apache Pulsar deployment, which relied on Zookeeper quorums across nodes, instantly crashed.

## The WireGuard-Native Band-Aid

To resolve the VXLAN routing blackhole, I switched the K3s Flannel backend from `vxlan` to `wireguard-native`. 

Unlike VXLAN, the WireGuard backend creates a `flannel-wg` interface that operates purely at Layer 3 (UDP port 51820) and isn't strictly bound to a single underlying hardware interface. This successfully allowed encrypted Flannel packets to traverse both the Oracle VCN and the Tailscale overlay seamlessly.

For a moment, the cluster was green again. But the architectural friction was just beginning.

## Stateful Workloads over a WAN Mesh

Kubernetes assumes a highly reliable, low-latency network between nodes. Stretching a cluster across a WAN overlay violates this assumption.

By placing `oracle10` in the cluster, the scheduler naturally started assigning workloads to it due to its massive 32GB RAM capacity. However, this introduced severe single points of failure:
- **PostgreSQL Replication**: The read replica on `oracle10` began suffering from sync lag when the Tailscale mesh experienced temporary latency spikes.
- **Apache Pulsar**: Distributed event streaming requires strict quorum and low-latency storage. Splitting BookKeeper nodes across a WAN resulted in frequent connection timeouts and dropped messages.

## The Final Straw: The MTU Jumbo Frame Bug

The decision was made: **Rollback**. 

I cordoned and drained `oracle10`, removed it from Terraform, and pulled all stateful workloads back to the internal Oracle VCN. With the external node gone, there was no longer a need for the `wireguard-native` Flannel backend, so I reverted K3s back to the default `vxlan`.

But the rollback introduced one final, brutal network bug: **The Jumbo Frame Blackhole**.

Oracle Cloud instances use an MTU of 9000 (Jumbo frames). When Flannel was reverted to VXLAN, it automatically calculated the pod interface MTU as 8950 (9000 - 50 bytes for VXLAN encapsulation). 

However, when a K3s pod attempted to connect to the public internet (which strictly enforces a 1500 MTU), the large packets were dropped by the internet gateway. Path MTU Discovery (PMTUD) failed, resulting in agonizing `TLS handshake timeouts` whenever a pod tried to make an HTTPS request (like our AI Incident Commander querying the GitHub API).

I ultimately had to apply a manual TCP MSS clamping rule via `iptables` on the master node to dynamically resize outbound packets to fit the 1500 MTU limit:
```bash
sudo iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
```

## Lessons Learned

1. **Don't stretch clusters across WANs**: If you need multi-region or hybrid deployments, use multi-cluster orchestration (like cluster federation or external load balancing) rather than stretching a single K3s control plane over a VPN.
2. **CNI Networking is unforgiving**: Mixing VXLAN, WireGuard, and Tailscale overlays creates deeply complex routing topologies that are nearly impossible to debug when things go wrong.
3. **Beware MTU mismatches**: When switching CNI plugins or networking backends, always verify your MTU values. A mismatch will manifest as baffling, intermittent application timeouts rather than outright connection failures.

Tailscale remains an incredible tool for developer access, zero-trust perimeters, and secure ingress. But as the foundational network layer for a distributed Kubernetes cluster? I'll stick to local subnets.
