# ADR-0022: Private Tailscale-Only Perimeter for Weaviate Vector Database & MCP Endpoint

## Status
🟢 **Accepted & Implemented**

## Context
Following the migration of the Weaviate Vector Database into the `ai` namespace on `arm10` (ADR-0021):
* **Security & Confidentiality**: Weaviate stores proprietary vector embeddings, semantic knowledge bases, and document chunks (`Vedge_api`), as well as native MCP server capabilities (`/v1/mcp`).
* **Public Attack Surface**: Exposing AI vector engines and MCP endpoints to the public internet introduces unnecessary risk of unauthorized scraping, query injection, and denial-of-service.
* **OAuth Friction for Agents & IDEs**: AI development agents, local IDE tooling, and programmatic microservices require direct, zero-friction REST/gRPC/MCP connectivity without interactive OAuth2 browser redirects or cookie session handling.

## Decision

1. **Zero Public Internet Exposure**:
   * Removed public reverse proxy routes (`weaviate.vinhthang.dev`) and Google OAuth2 forward-auth proxying from the edge gateway Caddyfile (`caddy/Caddyfile`).
   * Weaviate is not resolvable or reachable from the public internet.

2. **Tailscale-Only Private Access Boundary**:
   * All external management, developer IDEs, local AI agent tooling, and MCP integrations access Weaviate exclusively via the private Tailscale WireGuard mesh:
     * **HTTP REST & Native MCP**: `http://100.110.28.71:30011` (`/v1/meta`, `/v1/schema`, `/v1/mcp`)
     * **gRPC Protocol**: `100.110.28.71:32082`
   * **In-Cluster Microservice Discovery**: Internal cluster workloads (e.g. 20+ Spring Boot services on `oracle10`, AnythingLLM on `arm10`) connect directly via Kubernetes CoreDNS:
     * `http://weaviate.ai.svc.cluster.local:8080`
     * `grpc://weaviate.ai.svc.cluster.local:50051`

3. **No OAuth Overhead for Machine-to-Machine & MCP Workloads**:
   * Authentication is enforced at the network transport layer via Tailscale's cryptographically verified WireGuard device identity (Zero-Trust Network Access).
   * This removes OAuth latency, cookie management, and authentication redirects for programmatic MCP clients.

## Consequences

### Positive
* **Zero Attack Surface**: Weaviate cannot be accessed or scanned from the public internet.
* **Frictionless MCP & Agent Integration**: IDEs, MCP clients, and Spring Boot microservices connect directly to `http://100.110.28.71:30011` with zero authentication friction.
* **Low Latency**: Eliminates OAuth2 forward-auth roundtrips on every vector query.
