---
title: "Streaming Bilingual Books & Dramatic Audio at $0/Month: Inside reader.vinhthang.dev's Dual-Edge WireGuard Architecture"
author: "Thang Hoang & Antigravity"
date: "2026-10-25T20:00:00+07:00"
draft: false
showToc: true
TocOpen: true
categories: ["Cloud Architecture", "Multi-Cloud", "Networking & Performance"]
tags: ["Web Reader", "Caddy", "WireGuard", "Next.js", "Audio Streaming", "GCP Always Free", "Zero-Trust", "Oracle Cloud"]
---

Hosting a static Markdown blog on a 1 GB RAM cloud VM is straightforward. Hosting a public **bilingual reading and multi-character dramatic audio streaming platform**—spanning **12 literary books, 52 synchronized audio chapters, and ~2.5 GB of audio assets**—without paying a cent for managed object storage or CDNs is a completely different engineering problem.

Audio playback breaks every lazy assumption of standard web reverse proxying. Users scrub backward and forward across 45-minute MP3/AAC chapters, generating rapid-fire HTTP `206 Partial Content` byte-range requests. Meanwhile, our primary compute node `arm10` (4 OCPUs, 24 GB RAM) sits in an OCI private subnet running PostgreSQL 18, vector databases, and AI agents—and our edge gateways (`amd10` in Tokyo and `gce10` in Iowa) are strictly capped at **1 GB RAM**.

This post walks through how we deployed **`reader.vinhthang.dev`** (`web-reader`) as an isolated systemd service on our GCP Always Free node (`gce10`), bridged it across continents via an in-kernel **WireGuard (`wg0`) mesh**, eliminated proxy-induced audio scrubbing stalls with `flush_interval -1`, and locked down host ports with zero Google OAuth2 friction for readers.

---

## 1. The Placement Constraint: Keeping Heavy Disk & Audio I/O Off `arm10` and Out of 1 GB K3s Limits

Our multi-cloud fleet (`vinhthang.dev`) operates under rigid hardware boundaries documented in our Architecture Decision Records (ADRs):

| Node | Provider & Shape | Role | Memory Ceiling |
| :--- | :--- | :--- | :--- |
| **`arm10`** | OCI `VM.Standard.A1.Flex` | K3s Control Plane, DBs, AI & Observability | 24 GB RAM (Private Subnet) |
| **`amd10`** | OCI `VM.Standard.E2.1.Micro` | Primary Edge Gateway (Caddy, AdGuard, WireGuard) | **1 GB RAM** (Tokyo Public IP) |
| **`amd11`** | OCI `VM.Standard.E2.1.Micro` | Lightweight Worker (FileBrowser, VietCalendar, Navidrome) | **1 GB RAM** (Private Subnet) |
| **`gce10`** | GCP `e2-micro` (`us-central1`) | US Dual-Edge Mirror, WireGuard Outpost & `web-reader` | **1 GB RAM** (Iowa Public IP) |

When we built the `web-reader` Next.js platform—which renders synchronized bilingual text (`en`/`zh` alongside Vietnamese) paired with multi-character dramatic audiobook streams—putting a 2.5 GB audio corpus and Next.js byte-range file streaming inside the K3s cluster posed two issues:
1. **Unnecessary control-plane coupling**: Serving static/range-backed audio chunks doesn't need Kubernetes pod scheduling, kube-proxy NAT hops, or NodePort iptables overhead.
2. **Memory budget isolation on `gce10`**: `gce10` runs Oracle Linux 10 UEK with only **1 GB total RAM** (`e2-micro`), already hosting Caddy for our US dual-edge Hugo blog mirror and a WireGuard `wg1` US egress tunnel. Adding a heavyweight API gateway or container runtime layer on top of Next.js would risk triggering the Linux OOM killer during concurrent audio streams.

The solution in **ADR-0044** was clean decoupling: deploy `web-reader` directly onto `gce10` (`/opt/web-reader`) as a bare-metal `systemd` unit (`web-reader.service`) listening on port `3000`, and let our declarative Caddy edge fleet reverse-proxy public HTTPS traffic over the existing WireGuard `wg0` overlay.

---

## 2. Cross-Cloud Dual-Edge WireGuard Topology

Even though `web-reader.service` runs physically on `gce10` in Iowa (`136.111.37.17`), our primary Cloudflare origin and TLS edge gateway for `*.vinhthang.dev` is **`amd10` in Tokyo (`152.70.101.162`)**—with `gce10` acting as a synchronized US edge mirror.

Instead of opening port `3000` to the public internet on `gce10`, both edge gateways route to `web-reader` through the exact same private WireGuard overlay address: **`10.10.0.4:3000`**.

```text
                    Public Readers (Global)
                              │
                              ▼
                    [ Cloudflare Anycast ]
                     /                  \
       (Asia/Global)                      (US Edge Mirror)
            ▼                                    ▼
  ┌───────────────────────┐            ┌───────────────────────┐
  │  amd10 (OCI Tokyo)    │            │  gce10 (GCP Iowa)     │
  │  Caddy Edge Gateway   │            │  Caddy Edge Gateway   │
  │  152.70.101.162       │            │  136.111.37.17        │
  └──────────┬────────────┘            └──────────┬────────────┘
             │                                    │
   WireGuard wg0 (10.10.0.0/24)         Local Loopback / wg0
   Encrypted Cross-Cloud Tunnel         (Zero WAN Hop)
             │                                    │
             └──────────────► ┌───────────────────┴───────────────────┐
                              │  gce10 Host: web-reader.service       │
                              │  Bound Target: 10.10.0.4:3000         │
                              │  Next.js App + 2.5 GB Audio Corpus    │
                              │  (/opt/web-reader, systemd unit)      │
                              └───────────────────────────────────────┘
```

This topology gives us an elegant symmetry in `caddy/Caddyfile`:
* On **`amd10`**, packets destined for `10.10.0.4:3000` traverse the in-kernel `wg0` WireGuard tunnel across the Pacific to `gce10`.
* On **`gce10`**, `10.10.0.4` is its own `wg0` interface address, so the Linux kernel short-circuits the route directly over local loopback (`lo`) without leaving the machine.

Because both edge gateways share an identical `caddy/Caddyfile` synced via `scripts/gitops-sync.sh`, there is zero host-specific conditional templating required.

---

## 3. Unbuffered HTTP `206 Partial Content` Streaming (`flush_interval -1`)

Standard web reverse proxies optimize for small JSON payloads and HTML pages: they buffer upstream response chunks in memory before flushing them to the client. When streaming multi-megabyte dramatic audiobook chapters, default proxy buffering causes three immediate failures:

1. **Scrubbing stalls**: When a listener drags the audio player slider to minute 32:15, the browser aborts the previous socket and issues an `HTTP Range: bytes=31457280-` request. If the proxy buffers a few megabytes before flushing headers/chunks, playback freezes for seconds on every seek.
2. **Edge RAM spikes**: On a 1 GB RAM gateway (`amd10` or `gce10`), even a handful of concurrent buffered audio streams can balloon Caddy's RSS heap and starve co-located services like AdGuard Home or Vector.
3. **Broken React Server Component (RSC) streaming**: Next.js streams suspense boundaries progressively. Buffering collapses progressive hydration back into slow all-or-nothing page loads.

In `caddy/Caddyfile`, configuring **`flush_interval -1`** disables response buffering entirely so Caddy flushes every upstream byte from Next.js immediately to the TLS socket:

```caddy
# 18. Web Reader Bilingual Book & Audio Streaming Platform (Public Access)
reader.vinhthang.dev {
    import security_headers
    reverse_proxy 10.10.0.4:3000 {
        import strip_auth_headers
        flush_interval -1
    }
}
```

With `flush_interval -1`, HTTP `206 Partial Content` byte ranges flow continuously with near-zero proxy memory footprint, keeping timeline scrubbing crisp even across the cross-cloud Tokyo-to-Iowa `wg0` hop.

---

## 4. Public Access Without Trust Leaks (`strip_auth_headers` & `iptables`)

Almost every administrative dashboard on `*.vinhthang.dev` sits behind our `(sso_auth)` snippet (`auth.vinhthang.dev` Google OAuth2 Forward-Auth). For `reader.vinhthang.dev`, however, forcing readers to sign into Google OAuth before opening a literary chapter or hitting play on an audiobook defeats the purpose of an open reading platform.

Omitting `(sso_auth)` does **not** mean omitting perimeter security. Three layers keep the origin locked down:

### Layer 1: Header Spoof Stripping on Every Public Route
Even though `web-reader` is public, our Caddy fleet enforces a strict zero-trust ingress contract across all non-SSO routes via `(strip_auth_headers)`:

```caddy
# Global Security Headers Snippet
(security_headers) {
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy strict-origin-when-cross-origin
        -Server
    }
}

# Strip Forged Upstream Auth Headers on Non-SSO Reverse Proxy Routes
(strip_auth_headers) {
    header_up -X-Auth-Request-User
    header_up -X-Auth-Request-Email
    header_up -X-Proxy-Auth-Secret
}
```

This guarantees that no external caller can smuggle forged internal identity headers through the edge proxy, while `(security_headers)` enforces `nosniff`, `SAMEORIGIN`, strict referrer policy, and `-Server` banner removal.

### Layer 2: Kernel `iptables` Isolation on `gce10`
On `gce10`, port `3000` is completely unreachable from the public NIC (`eth0` / `ens4`). Host firewall rules persisted in `/etc/sysconfig/iptables` accept TCP `:3000` strictly from `wg0` and loopback `lo`:

```text
-A INPUT -i wg0 -p tcp --dport 3000 -j ACCEPT
-A INPUT -i lo  -p tcp --dport 3000 -j ACCEPT
```

Bypassing Cloudflare and hitting `http://136.111.37.17:3000` directly from the internet times out at the kernel packet filter—every request must enter over TLS on `:443` through Caddy.

### Layer 3: Dual-Edge Hot Reload via Caddy Admin API
Whenever `caddy/Caddyfile` changes, `scripts/gitops-sync.sh` pushes and validates the configuration on both `amd10` and `gce10` and reloads Caddy cleanly through its local IPv4 Admin API (`http://127.0.0.1:2019/load`)—avoiding `localhost` (`::1`) metrics collisions while dropping zero active audio streams.

---

## 5. Bandwidth Economics & Trade-Offs

Running a public audio streaming platform inside a `$0/month` multi-cloud setup comes with one obvious constraint: **egress metering**.

* **GCP Always Free egress**: `gce10` (`us-central1`) carries a **200 GB/month** free standard egress allowance (with China/Australia excluded from free tier). Serving 52 compressed dramatic audio chapters for personal and niche literary readership fits comfortably within that ceiling, while Cloudflare caches static Next.js JS/CSS chunks at the edge.
* **OCI Always Free egress**: Routing global traffic through `amd10` leverages OCI's generous **10 TB/month** outbound allowance, though cross-region `amd10` → `gce10` WireGuard traffic still consumes `gce10` egress bytes when pulling uncached audio ranges.
* **Zero K8s blast radius**: Because `web-reader` runs as a standalone `systemd` service isolated on `gce10`, an unexpected burst of audiobook downloads can never exhaust RAM or disk IOPS on `arm10`'s PostgreSQL 18 or K3s control plane.

By pairing bare-metal `systemd` simplicity with an in-kernel WireGuard mesh and unbuffered `flush_interval -1` Caddy streaming, `reader.vinhthang.dev` delivers instant bilingual reading and crisp audio scrubbing—without adding a single dollar to the monthly cloud bill.
