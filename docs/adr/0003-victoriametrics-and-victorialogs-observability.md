# ADR-0003: Ultra-Lightweight Observability (VictoriaMetrics & VictoriaLogs)

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
We need full-spectrum telemetry (metrics, logs, traces, synthetic health, and visitor analytics) across all microservices. However, standard enterprise stacks (Prometheus + Thanos + Loki + Elasticsearch) consume 2–4 GB of RAM, which would overwhelm our Always Free compute resources.

---

## 2. Decision
1. **Metrics TSDB**: Deployed **VictoriaMetrics** (`victoriametrics/victoria-metrics:v1.109.1`).
   * Drop-in PromQL replacement using **`< 35 MB RAM`** (10x lighter than Prometheus).
   * Built-in Prometheus scraper scraping Uptime Kuma and OpenTelemetry Collector with 30-day auto-retention.
2. **Log Aggregation**: Deployed **VictoriaLogs** (`victoriametrics/victoria-logs:v1.51.1`) paired with a **Promtail DaemonSet** (`grafana/promtail:3.0.0`).
   * Promtail tails `/var/log/pods/*/*/*.log` on both `arm10` and `amd11`.
   * VictoriaLogs stores millions of log lines with 15x compression in **`< 40 MB RAM`**.
3. **Single-Pane Visualization**: Deployed **Grafana 11.5.0** (`NodePort 30008`) pre-configured with 5 DataSources:
   * VictoriaMetrics (PromQL)
   * VictoriaLogs (`victoriametrics-logs-datasource` plugin)
   * PostgreSQL 18 (Umami analytics & Memos SQL)
   * OpenTelemetry APM Collector
4. **Synthetic Health**: Maintained **Uptime Kuma 2.5.3** for external HTTP/TLS probes and SSL expiration tracking.

---

## 3. Consequences
### Positive:
* Complete APM, full-text log search, and metrics running in **`< 120 MB RAM total`**.
* Single Command Center dashboard in Grafana with zero login friction via Google SSO.

### Negative / Trade-offs:
* VictoriaLogs uses LogsQL syntax for querying rather than LogQL, requiring the official `victoriametrics-logs-datasource` Grafana plugin.
