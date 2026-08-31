# ADR-0016: Active-Active Geo-Distributed Dual-Edge Ingress for Hugo Blog

## Status
🟢 **Accepted** (2026-08-27)

## Context
The tech blog (`vinhthang.dev`) was originally served exclusively from `amd10` in OCI Tokyo, Japan (`152.70.101.162`). While performance was optimal for visitors within Asia and the Western Pacific, readers in the Americas and Europe incurred ~140–180 ms cross-ocean round-trip latency.

With the addition of `gce10` (Google Cloud Always Free `e2-micro` VM in `us-central1`, Iowa, IP `34.61.16.208`), we gained a public-facing US compute node on Google's high-speed global fiber backbone.

## Decision

We deployed an **Active-Active Geo-Distributed Dual-Edge Ingress Architecture** for the static Hugo blog:

```
                     [ Readers Worldwide ]
                                │
                                ▼
                   DNS Query: vinhthang.dev
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
   [ Americas & Europe ]                         [ Asia & Vietnam ]
        │                                               │
        ▼                                               ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│  gce10 (GCP - US Central)     │               │  amd10 (OCI - Tokyo, Japan)   │
│  IP: 34.61.16.208             │               │  IP: 152.70.101.162           │
│  Latency: ~10-25 ms (US/EU)   │               │  Latency: ~5-15 ms (VN/Japan) │
│  Caddy Server (/opt/hugo-blog)│               │  Caddy Server (/opt/hugo-blog)│
└───────────────────────────────┘               └───────────────────────────────┘
        ▲                                               ▲
        │                                               │
        └───────────────── GitOps Sync ─────────────────┘
                    (Built on git push to main)
```

### Key Architectural Specifications:
1. **Edge Node 1 (Asia Edge - `amd10`)**:
   - Location: OCI Tokyo, Japan (`152.70.101.162`).
   - Software: Native Caddy v2.9.1.
   - Root: `/opt/hugo-blog/public`.
   - Ingress roles: Serves public blog for Asian readers + reverse-proxies internal private cluster microservices (`auth`, `umami`, `memos`, `grafana`, `navidrome`).
2. **Edge Node 2 (Americas Edge - `gce10`)**:
   - Location: GCP `us-central1`, Iowa, USA (`34.61.16.208`).
   - Software: Native Caddy v2.9.1 (SELinux hardened on Oracle Linux 10 UEK).
   - Root: `/opt/hugo-blog/public`.
   - Ingress roles: Serves public blog for US/EU visitors at native fiber speeds.
3. **Automated GitOps Synchronization**:
   - Script [`scripts/gitops-sync.sh`](../../scripts/gitops-sync.sh) builds Hugo static artifacts upon `git push`.
   - Syncs static assets to both `amd10` and `gce10` simultaneously via SSH streaming tar archives.
   - Hot-reloads Caddy on both edge servers in `< 1.2s`.
4. **DNS Ingress Layer (Cloudflare / Authoritative DNS)**:
   - Dual A-records for `vinhthang.dev` pointing to `152.70.101.162` and `34.61.16.208`.
   - With Cloudflare Proxy enabled, Cloudflare Anycast automatically balances requests to the closest origin edge.

## Consequences

### Positive
- **Sub-15ms Global Latency**: Readers in North America and Asia experience instant static page loads.
- **100% Zero-Downtime High Availability**: Complete fault tolerance against cloud-provider regional outages (GCP vs OCI).
- **Zero Financial Cost ($0/mo)**: Leverages Always Free tiers on both Oracle Cloud and Google Cloud.
- **Decoupled Edge**: Heavy web crawling and search engine indexing are offloaded across two public IPv4 gateways.
