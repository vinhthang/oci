# ADR 0037: Deploy OpenViking Context Database to K3s Fleet

## Context
AI agents require structured, persistent memory and context retrieval across sessions. Traditional RAG systems suffer from context fragmentation and flat vector search limitations. OpenViking is an open-source context database designed by Volcengine specifically for AI agents, structuring context, memories, and skills into a hierarchical, navigable virtual filesystem (`viking://`) with a built-in Model Context Protocol (MCP) server and REST API.

## Decision
We deploy `OpenViking` into a dedicated `openviking` namespace scheduled on the `arm10` master node (10 GB RAM).
- **Packaging & Manifests**: Codified within the Master Umbrella Helm Chart (`charts/vinhthang-fleet/templates/openviking.yaml`) and configured declaratively via `charts/vinhthang-fleet/values.yaml`.
- **Image**: Pinned to official release `ghcr.io/volcengine/openviking:latest` (or exact release tag `v0.4.21`).
- **Port Allocation**: ContainerPort `1933`, Service Port `1933`, NodePort `30013` (avoiding generic port `8080`).
- **Persistence**: Dedicated 5Gi `PersistentVolumeClaim` (`openviking-data-pvc`) utilizing `storageClassName: local-storage` bound to `/opt/openviking/data` on `arm10` with single replica and `strategy: Recreate`.
- **Model Engine**: Backed by Google Gemini (`gemini-embedding-2` for dense embeddings and Gemini for semantic extraction) configured via `ov.conf`.
- **Authentication**: Native token authentication (`OPENVIKING_API_KEY`) enforced for all data and MCP operations, with root administration protected via `root_api_key`.
- **Edge Ingress**: Declaratively defined in `caddy/Caddyfile` under `openviking.vinhthang.dev`, proxying directly to `10.0.0.216:30013` with TLS termination to enable direct client connectivity from laptops, CLI tools, and remote MCP clients without OAuth SSO redirection.
- **MCP Integration**: Configured in local Antigravity environment (`~/.gemini/config/mcp_config.json`) using `mcp-remote` connecting to `https://openviking.vinhthang.dev/mcp`.

## Consequences
- Agents and developer tools can leverage hierarchical context and persistent memory through a standardized MCP interface.
- Follows all architectural invariants: scheduled on `arm10`, dedicated port allocation (`1933` / NodePort `30013`), Helm-only deployment policy, and declarative Caddy reverse proxy.
- Direct API key authentication eliminates OAuth cookie requirements for external agents while preserving transport security via Let's Encrypt TLS.
