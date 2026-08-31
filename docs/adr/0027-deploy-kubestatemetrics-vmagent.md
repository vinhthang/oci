# ADR-0027: Deploy Kube-State-Metrics and VMagent for Native Kubernetes Health Monitoring

## Status
Accepted

## Context
Our existing observability stack utilized Vector to scrape Kubernetes logs and stream them to VictoriaLogs. However, we lacked a mechanism to capture cluster state metrics (like pod restarts, CPU/memory limits, and node health) into our VictoriaMetrics TSDB. As a result, our Grafana alerting engine was failing because the required Prometheus metrics (e.g., `kube_pod_container_status_restarts_total`) did not exist in the database.

## Decision
We will deploy `kube-state-metrics` and `vmagent` (VictoriaMetrics Agent) via the Master Helm Chart (`vinhthang-fleet`) to provide robust, lightweight, and native metrics scraping across the cluster.

1. **kube-state-metrics**: Scrapes the Kubernetes API to generate metrics about the state of deployments, pods, nodes, and other resources.
2. **vmagent**: A drop-in replacement for Prometheus scraper that is highly optimized. It will discover `kube-state-metrics` and cAdvisor endpoints natively, scrape them, and remote-write the metrics to our existing single-node VictoriaMetrics instance.

## Consequences
- **Positive**: Grafana Unified Alerting will have real data to evaluate, restoring the health of our AI Incident Commander webhook pipeline.
- **Positive**: We gain full visibility into cluster health.
- **Negative**: Adds a slight memory overhead to the cluster. However, `vmagent` is exceptionally lightweight compared to a full Prometheus server.
