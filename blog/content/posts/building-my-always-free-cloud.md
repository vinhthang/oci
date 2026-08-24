---
title: "🛠️ Building a Production-Grade Home Cloud on Oracle's $0 Always Free Tier"
date: 2026-08-21T00:21:00+07:00
draft: false
tags: ["Oracle Cloud", "DevOps", "Self-Hosted", "Rust", "AdGuard", "Docker", "Terraform", "Hugo"]
categories: ["Cloud Infrastructure"]
author: "Thang Hoang"
showToc: true
TocOpen: true
weight: 1
---

What can you actually run on a **$0/month Always Free cloud server**?

In this post, I document the end-to-end journey of turning an Oracle Cloud **1 GB AMD Micro instance (`amd10`)** in Tokyo into a multi-service personal cloud hub — complete with **Dual-Stack DNS ad-blocking**, **Google Single Sign-On (SSO)**, **lossless Hi-Res music streaming**, a **Rust-powered REST & AI MCP API**, and a **Hugo static blog**.

---

## 🏗️ Architecture & Network Blueprint

```mermaid
graph TD
    Internet["🌐 Internet / Home Network / Mobile"] --> Caddy["🔒 Caddy (Auto Let's Encrypt SSL)"]
    
    subgraph OCI Cloud Instance (amd10 - Tokyo)
        Caddy -->|/| VietCal["📅 VietCalendar REST & MCP (Rust :8080)"]
        Caddy -->|files.*| Oauth["🔑 OAuth2-Proxy (Google SSO :4180)"]
        Oauth --> FileBrowser["📁 FileBrowser Cloud Drive (:8082)"]
        Caddy -->|music.*| Navidrome["🎵 Navidrome Lossless FLAC (:4533)"]
        Caddy -->|blog.*| Hugo["📝 Hugo Static Site (:443)"]
        Caddy -->|adguard.*| AdGuardWeb["🛡️ AdGuard Dashboard (:3000)"]
        
        Router["🏠 Home Router (Fiber IPv4 & IPv6)"] --> AdGuardDNS["🛡️ AdGuard DNS Server (:53 & :853 DoT)"]
    end
```

---

## ⚡ 1. Reclaiming Hardware RAM (The `crashkernel` Discovery)

On a standard 1 GB VM, Linux kdump can silently reserve up to **448 MB RAM** (nearly half the server's memory!). 

By disabling `crashkernel=no` in GRUB:
* Reclaimed physical RAM from **512 MB → 946 MB**.
* Added a **2.5 GB swap file** with `zram`/swappiness tuning.
* **Result**: Plenty of headroom to run 6 concurrent services simultaneously.

---

## 🛡️ 2. Whole-Home Dual-Stack Ad-Blocking & Private DNS

We provisioned a dual-stack network with reserved static addresses:
* **Public IPv4**: `152.70.xxx.xxx` *(Always Free Reserved Static IP)*
* **Public IPv6**: `2603:c021:8022:100::xxxx` *(Always Free /56 Prefix)*
* **Android / iOS Private DNS (DoT)**: `<your-domain>.duckdns.org` on Port 853 with automatic Let's Encrypt TLS.
* **Router DNS**: Configured on our home fiber router, blocking ads and tracking telemetry across Smart TVs, iPhones, laptops, and IoT devices.

---

## 📅 3. VietCalendar: High-Performance Rust & AI MCP Server

Running on native Rust (Axum framework):
* Computes accurate Vietnamese Solar-to-Lunar conversions and public holiday schedules.
* Exposes an interactive **Swagger OpenAPI UI** at `/swagger-ui/`.
* Exposes a **Universal Model Context Protocol (MCP)** endpoint at `/mcp/sse` for AI assistants like Antigravity and Claude.
* **RAM footprint**: An astonishing **< 1 MB RAM**!

---

## 🎵 4. Navidrome: Bit-Perfect Lossless FLAC Streaming

* Deployed **Navidrome** in Go to stream Hi-Res 24-bit / 96kHz FLAC and ALAC audio.
* Full **Subsonic API** compatibility with audiophile mobile apps:
  * **Android**: *Symfonium* (bit-perfect USB DAC output).
  * **iOS**: *Amperfy* and *play:Sub*.
* **RAM footprint**: **~48 MB RAM**.

---

## 📁 5. FileBrowser with Google Single Sign-On (SSO)

* Self-hosted cloud drive on the **38 GB free NVMe disk**.
* Secured by **OAuth2-Proxy**: Whitelisted strictly to personal Google accounts. No passwords required — 1 click **"Sign In with Google"** logs you in directly.
* **Seamless Synergy**: Uploading audio files into the `Music/` folder in FileBrowser automatically syncs them into Navidrome for streaming!
* **Blog Synergy**: Markdown posts created in the `Blog/` folder auto-publish to this website!

---

## 📝 6. Hugo + PaperMod: Sub-Millisecond Static Tech Blog

* Static site generator built with **Hugo** and the **PaperMod** theme.
* Served directly by **Caddy** with gzip/zstd compression.
* **0 MB RAM runtime overhead** and instant sub-second auto-rebuilding whenever a Markdown post is saved.

---

## 📊 Live Server Resource Breakdown (`amd10`)

All 6 services running concurrently on **1 single core and 1 GB RAM**:

| Service | Port | Memory Usage | Status |
| :--- | :--- | :--- | :--- |
| **📁 FileBrowser** | `8082` | **18.1 MB** | 🟢 Active |
| **🔑 OAuth2-Proxy** | `4180` | **22.8 MB** | 🟢 Active |
| **🎵 Navidrome** | `4533` | **53.0 MB** | 🟢 Active |
| **🛡️ AdGuard Home** | `53 / 853` | **104.7 MB** | 🟢 Active |
| **📅 VietCalendar** | `8080` | **0.8 MB** | 🟢 Active |
| **📝 Hugo Auto-Rebuilder**| `systemd` | **26.8 MB** | 🟢 Active |
| **🔒 Caddy Web Server** | `80 / 443` | **~25.0 MB** | 🟢 Active |
| **TOTAL FREE MEMORY** | — | **~320 MB Free Physical RAM + 2.2 GB Swap** | 🟢 Healthy |

---

## 💻 Infrastructure as Code & Open Source

The complete automated provisioning runbook, security lists, and Terraform configurations are open-sourced on GitHub:

👉 **[https://github.com/vinhthang/oci](https://github.com/vinhthang/oci)**

*Written on and served from `amd10` in Tokyo.*
