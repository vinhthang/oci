---
trigger: always_on
---

# ADR & Architecture Governance Protocol

Whenever working on the **OCI Project (`vinhthang.dev`)**, the AI Assistant MUST ALWAYS follow these governance protocols:

## 1. Mandatory Pre-Flight ADR Review
Before designing, proposing, or implementing any architectural, infrastructure, database, Kubernetes, or ingress changes:
* **Read `docs/README.md` and review existing ADRs in `docs/adr/` first.**
* Understand all fixed invariants:
  * `amd10` (Edge Gateway) & `amd11` (Worker) are strictly capped at **1 GB RAM**.
  * `arm10` (Master) has **10 GB RAM**; all relational databases and AI runtimes must be scheduled here.
  * Ingress perimeter is strictly protected via Caddy Google OAuth2 Forward-Auth (`auth.vinhthang.dev`).

## 2. Mandatory ADR Generation for System Changes
Whenever a major system change occurs, including:
* Adding or retiring a microservice.
* Database schema, vector engine, or persistence layer modifications.
* Ingress, Caddy routing, TLS, or authentication changes.
* Observability, logging, or monitoring stack alterations.
* GitOps, CI/CD, or deployment pipeline updates.

You **MUST PROACTIVELY**:
1. Create a new Architecture Decision Record in `docs/adr/XXXX-<title>.md` following the standard Nygard format (Context, Decision, Consequences).
2. Register the new ADR in `docs/README.md` with a clickable link.
3. Update the Master Helm Chart (`charts/vinhthang-fleet/`) and `k8s/` manifests accordingly.
4. Commit and push the changes so the in-cluster GitOps webhook can deploy automatically.
