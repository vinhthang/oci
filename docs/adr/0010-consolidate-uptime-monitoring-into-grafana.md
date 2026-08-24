# ADR-0010: Consolidation of Synthetic Uptime Monitoring into Grafana 11 & OpenTelemetry

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-25
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
We previously ran **Uptime Kuma 2.5.3** as a standalone Node.js container with SQLite storage to monitor HTTP endpoints, response latencies, and SSL certificate expiration. While functional, running a separate Node.js runtime consumed ~100 MB of RAM, introduced another database file (`kuma.db`), and fractured observability between two separate web interfaces (Uptime Kuma and Grafana).

---

## 2. Decision
We retired Uptime Kuma and consolidated 100% of synthetic health checking, SLA monitoring, and alerting into our **existing OpenTelemetry Collector + VictoriaMetrics + Grafana 11 stack**:
1. **Endpoint Probing**: Configured OpenTelemetry Collector's native `httpcheck` receiver to probe all `*.vinhthang.dev` endpoints every 15 seconds.
2. **PromQL TSDB**: Exported probe status (`httpcheck_status`) and response durations to VictoriaMetrics with 30-day retention.
3. **Unified Visualization & Status Page**:
   * Grafana 11 serves as the unified Command Center for both private deep metrics and public SLA status history.
   * Enabled anonymous viewer access for `status.vinhthang.dev`, allowing public visitors to view uptime status dashboards directly.
4. **Ingress Routing**: Updated Caddy on `amd10` to proxy `status.vinhthang.dev` directly to Grafana 11 (`10.0.0.216:30008`).

---

## 3. Consequences
### Positive:
* **Resource Reclamation**: Eliminated the Node.js Uptime Kuma container and SQLite storage, saving ~100 MB RAM on `arm10`.
* **True Single Pane of Glass**: 100% of metrics (PromQL), logs (LogsQL), APM traces, and uptime health are unified inside Grafana 11.
* **Unified Alerting**: Endpoint outage alerts now route through Grafana 11 Unified Alerting engine.

### Negative / Trade-offs:
* Status pages are rendered as Grafana dashboard panels rather than Uptime Kuma's dedicated UI.
