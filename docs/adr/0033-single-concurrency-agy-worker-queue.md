# ADR-0033: Single-Concurrency Worker Queue for AI Incident Commander

**Date:** 2026-08-31
**Status:** 🟢 Accepted
**Domain:** Architecture / AI Integration

## Context

The `ai-incident-commander` microservice operates as the automated autonomous response system, taking Grafana webhooks and dynamically generating codebase fixes. To accomplish this, the system shells out to the Antigravity (`agy`) CLI binary, passing it contextual prompts via standard input and receiving the AI's triage/fix output.

Previously, each webhook handler spawned an independent `agy` process natively via `exec.CommandContext`. While functional, this unconstrained approach surfaced two critical stability risks:

1. **CPU & Memory Spikes:** The `arm10` K3s master node (which hosts the incident commander pod) would suffer severe kernel pressure if multiple Grafana webhooks fired simultaneously. Spawning 5-10 concurrent heavy AI agent binaries could trigger node-wide OOM kills.
2. **LLM Context Contamination (if using a persistent process):** Re-using the exact same `agy` process state for multiple incidents could cause the LLM to cross-contaminate context, mixing up telemetry logs from "Incident A" with "Incident B", leading to hallucinations and completely inaccurate codebase fixes.

## Decision

We have decided to refactor the internal execution architecture of the `ai-incident-commander` to utilize a **Strict Single-Concurrency Worker Queue pattern implemented via native Go Channels**.

The implementation involves:
1. **Global Buffered Channel:** A centralized `chan AgyJob` acts as the single point of entry for all `agy` requests, buffering up to 100 concurrent webhook events.
2. **Singleton Background Worker:** A single background goroutine (`StartAgyWorker`) ranges over the channel, guaranteeing mathematically that exactly **one** `exec.Command("agy")` process runs at any given time.
3. **Synchronous Result Delivery:** The webhook handlers submit `AgyJob` structs containing a response channel, seamlessly blocking their independent HTTP request lifecycle while waiting for the singleton worker to hand back the stdout/stderr result.

## Consequences

### Positive
- **Guaranteed Node Stability:** The CPU and Memory footprint of the LLM process on `arm10` is strictly capped. An "alert storm" from Grafana will elegantly queue up and process sequentially rather than crashing the Kubernetes cluster.
- **Strict Incident Isolation:** Because a fresh `exec.Command("agy")` is spawned and killed sequentially per job, every single incident receives a pristine, clean LLM context free of previous triage bias.
- **Idiomatic Concurrency:** Relies completely on Go's internal standard library channels, avoiding the need for external queueing middleware like Redis or RabbitMQ just to serialize shell commands.

### Negative
- **Sequential Backpressure Latency:** If 10 alerts fire at once, the 10th alert must wait for the previous 9 LLM sessions to generate output. Given LLM generation latency, this means the final alert might not receive a fix for several minutes. However, this is an acceptable tradeoff since incident generation is inherently an asynchronous, background pipeline.
