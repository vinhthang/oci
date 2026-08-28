# ADR-0021: Migration of Weaviate Vector Database & Native MCP Engine to Kubernetes (`ai` Namespace on `arm10`)

## Status
🟢 **Accepted & Implemented**

## Context
Prior to this migration, Weaviate 1.39.0 was deployed as a standalone Docker container (`weaviate-central`) on the workstation `oracle10`.
* **Durability Constraint**: `oracle10` is an external/remote workstation that may experience intermittent network disconnections or shutdowns. Critical AI memory, vector schemas (`Vedge_api`), and Model Context Protocol (MCP) tooling must remain **24/7 durable and always accessible** in the cloud.
* **Domain Partitioning**: Following ADR-0018, AI agents, Vector DBs, and MCP servers belong to their own dedicated domain namespace (**`ai`**), separate from transactional relational databases (**`data`**) and business applications (**`apps`**).
* **Secret Hygiene**: Google Generative AI API keys (`GOOGLE_APIKEY`) must not be stored in plaintext within container specs.

## Decision

1. **Dedicated AI Domain Namespace (`ai`) on 24/7 Cloud Master (`arm10`)**:
   * Created the dedicated `ai` namespace.
   * Scheduled Weaviate on `arm10` (OCI 24/7 master node with 10 GB RAM) via `nodeSelector: kubernetes.io/hostname: arm10`.
   * Allocated 10Gi persistent local storage at `/opt/weaviate/data` via `weaviate-data-pv` and `weaviate-data-pvc`.

2. **Secret Hygiene with Kubernetes Secrets**:
   * Created `weaviate-secret` in the `ai` namespace to store `GOOGLE_APIKEY`.
   * Referenced via `secretKeyRef` in the Weaviate deployment specification.

3. **Zero-Loss Data Migration over Tailscale Mesh**:
   * Gracefully stopped the Docker container on `oracle10`.
   * Streamed the 7.7 MB data volume (`classifications.db`, `modules.db`, `raft/`, `schema.db`, and `vedge_api/`) directly to `arm10:/opt/weaviate/data` over Tailscale.
   * All 139 vector objects and class properties were restored and verified intact.

4. **Service Discovery & Edge Ingress**:
   * **Internal DNS**: `weaviate.ai.svc.cluster.local` (Port `8080` for HTTP/REST/MCP, Port `50051` for gRPC).
   * **NodePort & Ingress**: Exposed on NodePort `30011` with Caddy edge proxy at `weaviate.vinhthang.dev` protected by Google OAuth2 forward-auth.

5. **Fault Isolation**:
   * If `oracle10` goes offline, Weaviate and all cloud services on `arm10`, `amd11`, and `gce10` remain 100% operational without degradation.

## Consequences

### Positive
* **24/7 Durability**: AI semantic search and native MCP tools (`/v1/mcp`) remain online continuously.
* **Fast Cross-Node Connectivity**: Incoming Spring Boot services on `oracle10` connect to `weaviate.ai.svc.cluster.local:8080` and `:50051` across the Tailscale mesh with low latency.
* **Declarative Helm-Only Management**: Weaviate is codified in `charts/vinhthang-fleet/templates/weaviate.yaml` and `values.yaml`.
