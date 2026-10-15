# Architecture Decisions: WireGuard US VPN Server on GCP Host (`gce10`)

**Feature ID**: `wireguard-us-vpn`  
**Status**: Proposed  

---

## ADR-0001: Selection of Kernel WireGuard over Userspace Proxies

- **Context**: The user requires a VPN server on `gce10` to egress internet traffic via Google Cloud US IP `136.111.37.17`. `gce10` has strictly 1 GB RAM, running K3s worker, Vector, and Caddy. Running containerized VPN servers (OpenVPN, Outline, Shadowsocks, Xray) introduces userspace memory consumption (50–150 MB) and context-switching overhead.
- **Decision**: Use native Linux kernel WireGuard via `wg-quick@wg1`.
- **Consequences**:
  - Positive: Zero daemon RAM footprint in userspace; maximum throughput via kernel crypto; native WireGuard apps across macOS, iOS, Android, and Windows.
  - Negative: Requires UDP traffic to be unblocked by upstream networks.

---

## ADR-0002: IP Subnet Allocation & Conflict Prevention

- **Context**: The cluster and host networking topology includes:
  - `10.0.0.0/16`: OCI Virtual Cloud Network (VCN).
  - `10.10.0.0/24`: Cross-cloud WireGuard mesh between `amd10` and `gce10` (`wg0`).
  - `10.42.0.0/16`: K3s Pod CIDR.
  - `10.43.0.0/16`: K3s Service CIDR.
  - `10.128.0.0/20`: GCP VPC default subnet.
- **Decision**: Assign `10.66.0.0/24` exclusively to the road-warrior VPN interface `wg1`.
- **Consequences**:
  - Positive: Guarantees 0 routing collisions with Kubernetes or inter-cloud mesh tunnels.
  - Negative: None.

---

## ADR-0003: GCP Firewall Management via `gcloud` CLI

- **Context**: `gce-free-vm` in GCP project `vietcalendar` resides behind GCP VPC firewall. Ingress traffic on UDP 51820 is dropped by default.
- **Decision**: Use `gcloud compute firewall-rules create` with `--project vietcalendar --account thanghv@gmail.com` to provision an ingress rule allowing UDP port 51820 targeting tag `http-server`.
- **Consequences**:
  - Positive: Clean, declarative cloud infrastructure configuration without manual Web Console edits.
  - Negative: Requires valid credentials for `thanghv@gmail.com`.
