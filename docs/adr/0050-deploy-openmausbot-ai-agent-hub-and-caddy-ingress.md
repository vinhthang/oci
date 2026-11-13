# ADR-0050: Deploy OpenMausBot AI Agent Team and Caddy Edge Ingress

* **Status**: Accepted
* **Date**: 2026-11-13
* **Category**: AI / Ingress & Multi-Agent Infrastructure

---

## Context

To expand self-hosted AI agent orchestration capabilities on the cluster without recurring subscription middleware fees, we evaluated [OpenMausBot](https://github.com/milind-soni/OpenMausBot) (an open-source local-first alternative to Grok Bot and Lindy AI). 

Following the vertical scaling of `arm10` to 4 OCPUs and 24 GB RAM (ADR-0046), `arm10` holds over 13.5 GiB of available unallocated physical RAM. OpenMausBot provides a multi-agent roster with native support for 30+ AI engines (including Google Gemini / Antigravity, Claude, OpenAI Codex, and Grok), built-in ARM64 Chromium 156 browser automation, interactive human-in-the-loop permission cards, and mobile/desktop pairing.

---

## Decision

1. **Deploy OpenMausBot on `arm10` with 5 GB RAM Cap**:
   - Schedule OpenMausBot in namespace `apps` pinned to `arm10` via `nodeSelector: kubernetes.io/hostname: arm10`.
   - Allocate resource bounds: `requests: { cpu: 100m, memory: 512Mi }`, `limits: { cpu: 2000m, memory: 5120Mi }`.
   - Provide a 1 GiB memory-backed `emptyDir` mount at `/dev/shm` for Chromium browser stability.
   - Bind to `0.0.0.0` via `OMB_LAN="1"` and expose the internal HTTP harness (`8799`) via dedicated NodePort `30014` (avoiding port `8080`).
2. **Expose Edge Ingress via Declarative `caddy/Caddyfile`**:
   - Route `mausbot.vinhthang.dev` and `openmausbot.vinhthang.dev` through Caddy reverse proxy to `10.0.0.216:30014`.
   - Enable `flush_interval -1` to support unbuffered Server-Sent Events (SSE) and LLM token streaming.
   - Utilize OpenMausBot's zero-trust pairing code architecture (`openmausbot pair --public-url https://mausbot.vinhthang.dev`) to prevent URL hash fragment stripping caused by OAuth redirects.
3. **Synchronize Edge Gateways**:
   - Validate and reload the updated Caddyfile across both edge nodes `amd10` and `gce10`.

---

## Consequences

### Positive
* **Self-Hosted Multi-Agent Hub**: Access specialized AI bots and delegated agent workflows 24/7 across desktop and mobile devices.
* **Streamlined Streaming**: Real-time token generation and SSE delivery via `flush_interval -1`.
* **Zero Host OOM Risk**: The 5 GB memory cgroup limit ensures that heavy browser tasks or tool execution cannot threaten mission-critical databases or Apache Pulsar on `arm10`.

### Negative / Trade-offs
* **Pairing Expiry**: One-time pairing codes expire after their configured TTL and require running `openmausbot pair` to authorize new devices.
