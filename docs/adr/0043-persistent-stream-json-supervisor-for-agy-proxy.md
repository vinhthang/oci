# ADR-0043: Persistent Stream-JSON Supervisor Daemon for Antigravity Proxy

**Date:** 2026-10-19  
**Status:** 🟢 Accepted  
**Domain:** AI Infrastructure / Host Services  

## Context

The `agy_proxy.py` service on host `arm10` (systemd: `agy-proxy.service`, port `8000`) provides OpenAI-compatible `/v1/chat/completions` and structured schema verification `/v1/review` endpoints for tools across the fleet, including Open WebUI, AnythingLLM, and external code review bridges.

Previously, `agy_proxy.py` invoked the Antigravity CLI binary (`agy`) in one-shot command-line print mode per request:
```bash
agy -p "<prompt>" --dangerously-skip-permissions [--model <model>] [--output-format json --json-schema <schema>]
```

While functional, this process-per-request architecture suffered from significant drawbacks:
1. **High Cold-Start Latency:** Every invocation incurred 10–15 seconds of process startup overhead, including runtime initialization, auth token checks, keyring lookups, plugin discovery, and tool registration, before LLM token generation could begin.
2. **Brittle Streaming Emulation:** Emulating token streaming required reading line-buffered stdout from a one-shot process, susceptible to buffering delays and missing native token delta events.
3. **Subprocess Resource Waste:** Spawning and destroying complex Python/Go runtime environments per HTTP request generated unnecessary CPU and memory churn on `arm10`.

The Antigravity CLI (`agy` v1.4.2+) includes programmatic streaming capabilities via `--input-format stream-json --output-format stream-json`. In this mode, `agy` runs as a long-lived process reading line-delimited NDJSON events from standard input (`{"event": "user", "message": {"content": "..."}}\n`) and streaming events on stdout (`init`, `step_update` with `text_delta` tokens, and `result` with final status and token usage). In benchmarks, warm turns in persistent mode execute in **2–4 seconds** (a ~5x speedup over cold start).

## Decision

We have decided to re-architect `agy_proxy.py` around a persistent **Stream-JSON Supervisor (`AgySupervisor`)**:

1. **Persistent Warm Worker:**
   - On application startup, the proxy initializes an `AgySupervisor` managing a long-lived `agy --input-format stream-json --output-format stream-json --dangerously-skip-permissions` subprocess.
   - The supervisor keeps stdin open and runs an asynchronous background reader task reading NDJSON events from stdout.

2. **Strict Concurrency Serialization via `asyncio.Lock`:**
   - In stream-json mode, `stdin` and `stdout` are strictly sequential. The supervisor serializes turns using an `asyncio.Lock()` to prevent race conditions or interleaved I/O.

3. **Real-Time Token Streaming via `step_update`:**
   - For `/v1/chat/completions` requests with `stream: true`, the supervisor streams token chunks directly from `step_update.text_delta` events as Server-Sent Events (SSE) compliant with the OpenAI specification.

4. **Lifecycle Management & Auto-Recycling:**
   - **Timeout Protection:** Each turn is guarded by a configurable 600-second timeout. If a turn exceeds the deadline, the supervisor kills the unresponsive subprocess, spawns a fresh worker, and returns HTTP 504.
   - **Context & Resource Recycling:** To prevent unbounded memory expansion or conversation state bloat, the supervisor automatically recycles the worker after `MAX_TURNS_PER_WORKER = 30` completed turns or upon encountering an unrecoverable process error.
   - **Explicit Reset Endpoint:** A management endpoint `POST /v1/supervisor/restart` is provided to allow forcing a fresh worker on demand.

5. **Dedicated Structured Runner for One-Off Review Schemas & Model Skew:**
   - Dynamic `/v1/review` requests requiring custom, arbitrary JSON schemas or divergent models (e.g., `claude-opus-4-6-thinking`) are routed to the dedicated structured runner with `--json-schema` and `--output-format json`, guaranteeing schema compliance and avoiding CLI flag conflicts.

## Consequences

### Positive
- **5x Latency Reduction:** Standard completions drop from 15–20s down to 2–4s per turn by eliminating CLI cold starts.
- **Native Real-Time Streaming:** Direct consumption of `step_update.text_delta` enables smooth, instantaneous SSE streaming to WebUI frontends.
- **Self-Healing Resilience:** Automatic health checks and supervisor respawns ensure crashes or hung CLI processes do not permanently disable the proxy.
- **Clean Observability:** `GET /` reports real-time supervisor status, PID, active turn count, and backend CLI version.

### Negative / Trade-offs
- **Single Concurrency:** Requests on the warm worker are processed sequentially. Simultaneous bursts queue on the `asyncio.Lock()`. Given `arm10`'s role as a private master node and the single-concurrency mandate established in ADR-0033, this is an intentional safety invariant.
- **Worker Recycling Latency:** Every 30 turns, the worker recycles, incurring a single 10s cold-start on the recycling turn.
