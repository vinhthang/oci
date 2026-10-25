# ADR 0044: Public Edge Caddy Ingress for Web Reader Standalone Node (`reader.vinhthang.dev`)

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-10-25
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
- **Web Reader Deployment**: A bilingual reader platform (`web-reader`) serving 12 literary books and 52 synchronized audio chapters (~2.5 GB corpus) was deployed to standalone GCP node `gce10` (`oracle@136.111.37.17`) under `/opt/web-reader` and managed by systemd unit `web-reader.service` on port 3000.
- **Access Policy & Domain Requirement**: The reader is a public web application designed for open literary reading and audio streaming without Google OAuth2 SSO gating. It requires a branded, accessible public entrypoint at `reader.vinhthang.dev`.
- **Infrastructure & Memory Invariants**:
  - `gce10` (GCP `e2-micro`, Oracle Linux 10 UEK) is strictly memory-capped at **1 GB RAM**. Running production Kubernetes or heavyweight API gateways directly on `gce10` violates fleet memory invariants (`RULE[adr-governance]`).
  - Edge Gateway `amd10` (`152.70.101.162`) serves as the primary ingress perimeter and Cloudflare origin for `*.vinhthang.dev`.
  - Node `gce10` is connected to the fleet via in-kernel WireGuard overlay `wg0` (`10.10.0.4/24`).
- **Audio Streaming Optimization**: Next.js serves HTTP 206 Partial Content byte ranges for large multi-megabyte audio files. Standard reverse proxy buffering introduces high latency, stalls playback scrubbing, and consumes edge proxy memory buffers.

---

## 2. Decision

We establish declarative edge routing for `reader.vinhthang.dev` across the fleet mesh:

1. **Declarative Ingress in `caddy/Caddyfile`**:
   - Register `reader.vinhthang.dev` in the master Caddyfile:
     ```caddy
     # 18. Web Reader Bilingual Book & Audio Streaming Platform (Public Access)
     reader.vinhthang.dev {
         import security_headers
         reverse_proxy 10.10.0.4:3000 {
             flush_interval -1
         }
     }
     ```
   - **Public Access**: Exclude `forward_auth` to permit direct public access to reader pages, API endpoints, and audio streams.
   - **Unbuffered Streaming**: Set `flush_interval -1` to stream audio chunks and React Server Component payloads immediately without edge buffering.
   - **Mesh Transport**: Target `10.10.0.4:3000` over the WireGuard `wg0` overlay. On `amd10`, traffic routes through `wg0`; on `gce10`, `10.10.0.4` routes through local loopback.

2. **Host Firewall & Kernel Packet Invariants on `gce10`**:
   - Permitted TCP port 3000 traffic from WireGuard overlay `wg0` and local loopback `lo` in `iptables`:
     - `-i wg0 -p tcp --dport 3000 -j ACCEPT`
     - `-i lo -p tcp --dport 3000 -j ACCEPT`
   - Persisted rules to `/etc/sysconfig/iptables`.

3. **Dual-Edge GitOps Synchronization**:
   - Updated [`scripts/gitops-sync.sh`](../../scripts/gitops-sync.sh) to automatically synchronize `caddy/Caddyfile` to both `amd10` and `gce10` before reloading Caddy instances.

---

## 3. Consequences

### Positive:
- **Zero Ingress Gating**: Readers can access `https://reader.vinhthang.dev` globally without authentication barriers.
- **Low-Latency Audio Streaming**: `flush_interval -1` enables instantaneous audio scrubbing and byte-range streaming directly from disk to client.
- **Strict Memory Invariant Adherence**: `web-reader` runs as an isolated standalone Node.js service on `gce10`, isolating audio I/O and RAM usage from Kubernetes control plane nodes.
- **Automated TLS & Origin Protection**: Cloudflare proxy terminates edge TLS and forwards to `amd10` Caddy, which issues and maintains automated Let's Encrypt certificates.

### Negative / Trade-offs:
- Public audio streaming from `gce10` consumes GCP Always Free network egress bandwidth (within the 200 GB/month limit).
