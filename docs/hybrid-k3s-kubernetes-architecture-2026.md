---
title: "Architecting a Multi-Node Hybrid K3s Kubernetes Fleet on Oracle Cloud Always Free"
date: 2026-08-24T18:40:00+07:00
draft: false
tags: ["Kubernetes", "K3s", "Oracle Cloud", "DevOps", "Terraform", "PostgreSQL", "AI", "Architecture"]
categories: ["Cloud Architecture", "DevOps"]
author: "Thang Hoang & Antigravity"
showToc: true
TocOpen: true
---

How do you turn 3 separate Always Free cloud virtual machines into a resilient, production-grade, multi-architecture Kubernetes cluster capable of running high-performance relational databases, AI vector stores, lossless music streaming, and personal cloud storage?

In this post, I will break down the complete architecture of our newly deployed **3-Node Hybrid K3s Cluster** running on **Oracle Cloud Infrastructure (OCI)** under our custom domain [**`vinhthang.dev`**](https://vinhthang.dev).

---

## 🏛️ The 3-Node Cluster Topology

Oracle Cloud's Always Free tier offers an incredible set of compute resources:
- **2x AMD64 E2.1.Micro instances** (1 OCPU, 1 GB RAM each)
- **1x ARM64 Ampere A1 instance** (flexibly sized up to 4 OCPUs and 24 GB RAM; here sized at 2 OCPUs, 12 GB RAM)
- **1x Reserved Static Public IPv4 Address**

Instead of treating these machines as isolated Docker boxes, we unified them into a cohesive fleet:

```
                          [ 🌐 Internet Traffic (*.vinhthang.dev) ]
                                            │
                                            ▼
                          ┌─────────────────────────────────────┐
                          │    amd10 (Edge Ingress Gateway)     │
                          │   Edge Domain: vinhthang.dev  │
                          │  • Caddy Reverse Proxy & Let's Encrypt│
                          │  • AdGuard Home DNS-over-TLS (853)  │
                          │  • Hugo PaperMod Tech Blog Engine   │
                          └──────────────────┬──────────────────┘
                                             │ Private Oracle VCN (10.0.0.0/16)
                    ┌────────────────────────┴────────────────────────┐
                    │                                                 │
                    ▼                                                 ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│     arm10 (K3s Control Plane)         │ │     amd11 (K3s Worker Node)           │
│     ARM64 Ampere A1 (2 OCPU / 12GB)   │ │     AMD64 E2.1.Micro (1 OCPU / 1GB)   │
│ • K3s Control Plane & Scheduler       │ │ • K3s Agent / Worker                  │
│ • PostgreSQL 18.6 + pgvector 0.8.6    │ │ • Navidrome Music (45 GB FLAC disk)   │
│ • AnythingLLM AI Agent & Vector RAG   │ │ • FileBrowser Cloud Storage           │
│ • Memos AI Digital Notebook           │ │ • VietCalendar High-Speed Rust API    │
│ • Central Google OAuth2 SSO Gateway   │ └───────────────────────────────────────┘
└───────────────────────────────────────┘
```

---

## 🚀 Key Architectural Innovations

### 1. Heterogeneous Multi-Architecture Scheduling (`arm64` + `amd64`)
Our K3s cluster seamlessly schedules containers across both CPU architectures using Kubernetes node selectors:
* **ARM64 Workloads (`arm10`)**: Heavy compute, AI vector processing, and memory-intensive databases (`PostgreSQL 18`, `AnythingLLM`, `Memos`, `oauth2-proxy`).
* **AMD64 Workloads (`amd11`)**: I/O-bound storage services and x86-native binaries (`Navidrome`, `FileBrowser`, `VietCalendar`).

```yaml
# Example: Targeting AMD64 storage node in Kubernetes
spec:
  nodeSelector:
    kubernetes.io/hostname: amd11
    kubernetes.io/arch: amd64
```

---

### 2. State-of-the-Art PostgreSQL 18.6 with `pgvector 0.8.6`
At the heart of the cluster lies **PostgreSQL 18.6** paired with **`pgvector 0.8.6`** running natively on `arm10`:
* **Asynchronous Direct I/O (AIO)**: Non-blocking disk reads for fast vector retrieval.
* **64-bit Transaction IDs**: Eliminates transaction wraparound freezes permanently.
* **Unified Database Stores**: Backs Memos (`memos`), user analytics (`vietcalendar`), and custom AI embedding collections (`vector_db`).

---

### 3. Centralized Google OAuth2 Single Sign-On (SSO)
Rather than placing separate auth proxies on every microservice, we built a **Central Forward-Auth Gateway** (`auth.vinhthang.dev`):
* Caddy checks session cookies with `forward_auth` against `oauth2-proxy` running in K3s.
* A single Google login issues a shared wildcard cookie for **`.vinhthang.dev`**.
* Logging in once unlocks **`files.vinhthang.dev`**, **`ai.vinhthang.dev`**, and **`memos.vinhthang.dev`** with zero repeated prompts.

---

### 4. Lossless Audio & Cloud Storage Preserved via `hostPath`
Our 45 GB lossless FLAC music library and persistent storage were preserved without data migration by leveraging Kubernetes `hostPath` volume mounts on `amd11`:
* **Navidrome** directly streams from `/opt/navidrome/music`.
* **FileBrowser** provides web-based file management over `/srv/Music`.

---

## 🛠️ Unified Multi-Cluster Management

From our development workstation, we unified management across **50 Kubernetes clusters** inside a single `~/.kube/config`:
* `oci-k3s` (Our Oracle Cloud fleet)
* `asgard.local` & `unicron.local` (Local bare-metal clusters)
* 47 live Google Kubernetes Engine (GKE) clusters across enterprise projects.

```bash
# Switch to Oracle Cloud K3s cluster in 1 command:
kubectl get nodes -o wide --context oci-k3s
```

---

## 🌐 Live Production Service Directory

All services are publicly live under our newly registered custom domain:

| Service | Endpoint | Description |
| :--- | :--- | :--- |
| **📝 Tech Blog** | [**`vinhthang.dev`**](https://vinhthang.dev) | Static Hugo site served with Brotli/Zstandard |
| **🤖 AnythingLLM** | [**`ai.vinhthang.dev`**](https://ai.vinhthang.dev) | Autonomous AI Agent & Document RAG |
| **📝 Memos** | [**`memos.vinhthang.dev`**](https://memos.vinhthang.dev) | PostgreSQL-backed AI Journal & Notes |
| **🎵 Navidrome** | [**`music.vinhthang.dev`**](https://music.vinhthang.dev) | Subsonic FLAC Lossless Music Streaming |
| **📁 FileBrowser** | [**`files.vinhthang.dev`**](https://files.vinhthang.dev) | Google SSO Cloud Storage |
| **🔌 VietCalendar API** | [**`api.vinhthang.dev`**](https://api.vinhthang.dev) | Axum Rust Lunar Calendar Engine |
| **🛡️ AdGuard Home** | [**`adguard.vinhthang.dev`**](https://adguard.vinhthang.dev) | Private DNS-over-TLS (Port 853) |

---

*Co-authored with prompt engineering and pair-programming using Google Antigravity.*
