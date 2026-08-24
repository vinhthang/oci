---
title: "Autonomous AI Infrastructure: AnythingLLM, PostgreSQL 18 pgvector, and the Antigravity CLI (agy) System Agent"
date: 2026-08-24T18:43:00+07:00
draft: false
tags: ["AI", "LLM", "AnythingLLM", "PostgreSQL", "pgvector", "Antigravity", "DevOps", "Automation"]
categories: ["Artificial Intelligence", "DevOps"]
author: "Thang Hoang & Antigravity"
showToc: true
TocOpen: true
---

Most self-hosted AI setups stop at running a basic chat UI connected to a remote API. But what if your self-hosted AI wasn't just a conversational bot, but a **fully empowered autonomous system agent** capable of managing your infrastructure, installing command-line tools, debugging services, and querying custom vector databases?

In this post, I will explore our complete self-hosted AI architecture running on an Always Free cloud Kubernetes cluster—featuring **AnythingLLM**, **PostgreSQL 18 with `pgvector`**, and the **Google Antigravity CLI (`agy`)**.

---

## 🏗️ The End-to-End AI Stack

Our AI stack is organized into three complementary layers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        1. User Interaction Layer                        │
│   • AnythingLLM Web UI (https://ai.vinhthang.dev)                       │
│   • Document RAG, PDF Analysis, Workspace Memory, Voice Synthesizer     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        2. System Agent Core                             │
│   • Antigravity CLI (`agy`) Daemon & OpenAI-Compatible Gateway          │
│   • Autonomous Terminal Execution (install git, compile, run scripts)  │
│   • Tool Calling, Multi-Agent Delegation, and Real-Time Reasoning       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        3. High-Performance Data Layer                   │
│   • PostgreSQL 18.6 with `pgvector 0.8.6`                               │
│   • Asynchronous I/O (AIO) for Ultra-Fast Vector Cosine Similarity      │
│   • LanceDB Embedded Fast Local Storage                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 1. AnythingLLM: The Unified Knowledge & RAG Hub

For interacting with complex technical specifications, architecture diagrams, and research papers, we run **AnythingLLM** in Kubernetes on our ARM64 powerhouse node (`arm10` with 12 GB RAM):

* **Document Chunking & Vector Search**: Ingests multi-page PDFs, markdown wikis, and codebases, converting them into semantic vector embeddings.
* **Granular Workspaces**: Isolate context across different domains (e.g. DevOps, Backend Services, Personal Notes).
* **Privacy & Security**: Enforced with a **Centralized Google OAuth2 Single Sign-On (SSO)** gateway, allowing only whitelisted administrative accounts to access the portal.

---

## 🛠️ 2. The Powerhouse: Antigravity CLI (`agy`) as an Autonomous System Agent

The true differentiator in our setup is integrating the **Google Antigravity CLI (`agy`)**. 

Unlike conventional language models that can only output text into a chatbox, `agy` is equipped with **deep host-level execution capabilities**:

### ⚡ What the `agy` Agent Can Do on the Host:
1. **Package & Tool Installation**:
   When tasked with setting up a project, `agy` can automatically update system repositories and install packages like `git`, `docker`, `rustc`, `ripgrep`, or `kubectl` without requiring manual terminal babysitting.
2. **Command Execution & Terminal Automation**:
   It can compile codebases, run test suites, inspect system logs with `journalctl`, and diagnose container failures in real time.
3. **Infrastructure & Kubernetes Management**:
   The agent can craft Kubernetes YAML manifests, apply them to the cluster via `kubectl`, verify pod health, and perform rolling updates.
4. **Autonomous Problem Solving**:
   When an error occurs (such as an unreachable port or a missing dependency), `agy` inspects firewall rules, checks listening ports with `ss -tulpn`, edits configuration files, and restarts services autonomously.

```bash
# Running Antigravity CLI in automated headless mode
agy -p "Inspect the cluster pods and verify all services are healthy" --dangerously-skip-permissions
```

To allow AnythingLLM to query `agy` as an AI model, we built a lightweight **FastAPI OpenAI Proxy (`agy-proxy`)** running as a native systemd service on the server. AnythingLLM simply sends standard `/v1/chat/completions` requests to `http://localhost:8000/v1`, and the proxy delegates execution directly to the authenticated Antigravity engine!

---

## 🐘 3. PostgreSQL 18.6 with `pgvector 0.8.6`: Next-Gen Vector Storage

Relational data and AI vector embeddings converge in our **PostgreSQL 18.6** instance:

* **Native Asynchronous Direct I/O (AIO)**: PostgreSQL 18 introduces true asynchronous disk reads, drastically reducing latency during high-dimensional vector nearest-neighbor searches (HNSW / IVFFlat).
* **64-bit Transaction IDs**: Eliminates transaction wraparound freezes, ensuring uninterrupted operation for high-frequency database writes.
* **Unified State Store**: Powering our **Memos AI Journal** (`memos.vinhthang.dev`) and vector collections under a single, highly optimized relational engine.

---

## 🚀 The Advantage of Self-Hosted Hybrid AI

| Capability | Standard Web Chatbot | Our Autonomous AI Stack |
| :--- | :--- | :--- |
| **Document Understanding** | Limited to small uploads | Hundreds of pages via PostgreSQL vector RAG |
| **System Administration** | ❌ None (Text only) | ✅ Installs packages, runs shell commands, edits files |
| **Cloud Orchestration** | ❌ None | ✅ Manages Kubernetes, GitOps, and Docker containers |
| **Data Privacy** | Third-party cloud storage | 🔒 Self-hosted on private NVMe disk with Google SSO |
| **Cost** | Expensive monthly tiers | ♾️ **100% Free on Oracle Cloud Infrastructure** |

---

## 🎯 Conclusion

By bridging **AnythingLLM** with the autonomous capabilities of the **Antigravity CLI (`agy`)** and the speed of **PostgreSQL 18 + `pgvector`**, we've transformed a simple cloud server into an intelligent, self-healing developer companion that can build, maintain, and expand its own environment.

*Stay tuned for more deep dives into autonomous AI and cloud architecture on [vinhthang.dev](https://vinhthang.dev)!*
