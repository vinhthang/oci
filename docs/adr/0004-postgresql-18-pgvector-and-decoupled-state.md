# ADR-0004: PostgreSQL 18.6 `pgvector` & Decoupled State Architecture

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Our architecture includes applications with diverse data requirements:
* Relational visitor analytics (Umami).
* Digital journaling with relational tags and search (Memos).
* AI vector embeddings for semantic document search (AnythingLLM).
* Stateless mathematical astronomical calculations (VietCalendar).
* Critical synthetic health monitoring (Uptime Kuma).

---

## 2. Decision
1. **Centralized PostgreSQL 18.6 (`pgvector/pgvector:pg18`) on `arm10`**:
   * Configured as the single high-performance relational engine hosting:
     * `umami`: Web visitor analytics database.
     * `memos`: Digital notes and tags database.
     * `vector_db`: Vector embeddings using `pgvector 0.8.6` for AnythingLLM document RAG.
2. **Decoupled State for Uptime Kuma**:
   * Kept Uptime Kuma on embedded SQLite with Write-Ahead Logging (WAL) in `/opt/uptime-kuma/kuma.db`.
   * *Rationale*: Ensures the health monitor never fails due to database connectivity issues, maintaining independent watchdog capabilities.
3. **Stateless VietCalendar**:
   * VietCalendar is implemented in pure in-memory Rust Axum with zero database dependencies.

---

## 3. Consequences
### Positive:
* Single robust PostgreSQL 18 instance with `pgvector` powering analytics, notes, and AI vectors.
* Zero cascading failure risks for uptime monitoring.
* High-speed, stateless execution for mathematical calendar calculations.

### Negative / Trade-offs:
* PostgreSQL 18 host storage (`/opt/postgres`) is state-critical and must be backed up regularly.
