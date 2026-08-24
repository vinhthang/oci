# 🏗️ Oracle Cloud Always Free 3-Node Architecture & AI Cluster Guide (2026)

This comprehensive architecture document details the complete 3-Node Always Free Cloud Infrastructure, multi-architecture K3s Kubernetes cluster, and self-hosted AI services deployed across Oracle Cloud Tokyo (`ap-tokyo-1`).

---

## 📊 1. Infrastructure Overview & Machine Inventory

| Node | Architecture | Shape | CPU / RAM | Boot Volume (Reclaimed) | Primary Roles |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`amd10`** | `x86_64` (AMD) | `VM.Standard.E2.1.Micro` | 1 OCPU / 1 GB RAM | 45 GB NVMe (37 GB Free) | Dedicated Public Edge Gateway, Caddy Ingress SSL, AdGuard Home (DoT Port 853), Hugo PaperMod Blog |
| **`amd11`** | `x86_64` (AMD) | `VM.Standard.E2.1.Micro` | 1 OCPU / 1 GB RAM | 45 GB NVMe (24 GB Free) | K3s Worker Node, Navidrome 45 GB Lossless FLAC Music, FileBrowser (Google OAuth2 SSO), VietCalendar API |
| **`arm10`** | `aarch64` (ARM64) | `VM.Standard.A1.Flex` | **2 OCPUs / 12 GB RAM** | 45 GB NVMe (36 GB Free) | K3s Master / Control Plane, PostgreSQL 18.6 with `pgvector 0.8.6`, Memos AI Digital Journal, AnythingLLM RAG Engine |

---

## ⚡ 2. Kubernetes Cluster Topology (`oci-k3s`)

* **Kubernetes Distribution**: Stripped **K3s v1.36.3** with `containerd` container runtime.
* **Master Node (`arm10`)**:
  * Internal Private IP: `10.0.0.216`
  * Control plane components: CoreDNS, API Server, Scheduler, SQLite state storage.
  * Memory footprint: ~400 MB RAM (Leaving **~8.9 GB RAM available** for AI workloads!).
* **Worker Node (`amd11`)**:
  * Internal Private IP: `10.0.0.10`
  * Connects over private VCN (`10.0.0.0/16`) to `arm10:6443`.
  * Node labels: `node-role.kubernetes.io/worker=worker`, `storage-node=true`.
  * Memory footprint: ~120 MB RAM (`kubelet` + `containerd`).

---

## 🐘 3. Central AI Database: PostgreSQL 18.6 + `pgvector`

* **Container Image**: `pgvector/pgvector:pg18` (ARM64 Native).
* **Storage**: Persistent high-speed NVMe mount at `/opt/postgres/data`.
* **Database Features**:
  * **Asynchronous I/O (AIO)**: High-throughput non-blocking disk reads for vector similarity searches.
  * **64-bit Transaction IDs**: Zero transaction wraparound freezing.
  * **`pgvector 0.8.6`**: Accelerated `HNSW` and `IVFFlat` vector indexing.
* **Databases Created**:
  * `memos`: Complete relational backend for Memos note-taking.
  * `vietcalendar`: Ready for API monetization, rate-limiting, and user subscriptions.
  * `vector_db`: Vector embeddings repository for custom AI pipelines.

---

## 🤖 4. Self-Hosted AI Ecosystem

### 📝 Memos (Personal Digital Notebook & MCP Memory)
* **Domain**: `https://memos.thang-gcloud.duckdns.org`
* **Port**: `5230`
* **Role**: Captures quick daily thoughts, code snippets, tags, and mobile voice memos. Serves as permanent working memory for Antigravity via Model Context Protocol (MCP).

### 📚 AnythingLLM (Document RAG & Autonomous AI Agents)
* **Domain**: `https://ai.thang-gcloud.duckdns.org`
* **Port**: `3001`
* **LLM Engine**: Powered by Google Gemini (`gemini-3.7-flash`, `gemini-3.1-pro-preview`) with Gemini Embeddings (`text-embedding-004`).
* **AI Agent Mode (`@agent`)**: Equipped with live web browsing (DuckDuckGo), SQL database connectors (PostgreSQL 18), and multi-document synthesis.

---

## 🔒 5. Public Service Routing & Ingress Map

| Subdomain | Proxy Destination | Ingress Features |
| :--- | :--- | :--- |
| `https://thang-gcloud.duckdns.org` | `10.0.0.10:8080` (VietCalendar) | Fast Axum Rust API |
| `https://adguard.thang-gcloud.duckdns.org` | `127.0.0.1:3000` (AdGuard) | Private DNS-over-TLS (Port 853) |
| `https://music.thang-gcloud.duckdns.org` | `10.0.0.10:4533` (Navidrome) | Lossless FLAC streaming (Symfonium/Subsonic) |
| `https://files.thang-gcloud.duckdns.org` | `10.0.0.10:4180` (FileBrowser) | Google OAuth2 SSO Proxy (20GB uploads) |
| `https://memos.thang-gcloud.duckdns.org` | `10.0.0.216:5230` (Memos) | Real-time websocket & Postgres backend |
| `https://ai.thang-gcloud.duckdns.org` | `10.0.0.216:3001` (AnythingLLM) | 500MB PDF uploads & streaming AI tokens |
| `https://blog.thang-gcloud.duckdns.org` | Local `/opt/hugo-blog/public` | High-speed static web engine |

---

## 💻 6. Unified CLI Management

From your local Mac terminal:
```bash
# View all Kubernetes nodes
kubectl get nodes -o wide --context oci-k3s

# View all running pods across both machines
kubectl get pods -A -o wide --context oci-k3s

# Stream database logs
kubectl logs -f deployment/postgres --context oci-k3s
```
