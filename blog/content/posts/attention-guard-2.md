+++
title = "Securing Agentic Orchestration: Building the Attention Guard 2.0 State Machine"
date = "2026-09-05T14:00:00+07:00"
draft = false
tags = ["Antigravity", "AI Agents", "Security", "State Machines", "Architecture"]
categories = ["Engineering", "AI"]
author = "Vinh Thang"
+++

As autonomous AI agents evolve from isolated chatbots into orchestrators of complex, multi-pass software engineering tasks, the boundaries of execution become critical. In the **Antigravity** ecosystem, we rely heavily on specialized subagents—like `DeepCoder` and `DeepInvestigator`—to autonomously navigate codebases, test hypotheses, and execute shell commands. 

But what happens when an agent hallucinates a success? What happens when a long-running subagent hangs indefinitely? How do we prevent a deeply nested execution worker from going rogue and launching its own recursive subagents?

Today, I’m excited to share the engineering behind the **Antigravity Attention Guard Plugin 2.0**—a complete architectural rewrite that enforces rigorous execution boundaries using a deterministic Finite State Machine (FSM) backed by an atomic SQLite ledger.

---

### The 1.0 Problem: Boolean Patches and Ghost States

The original Attention Guard plugin relied on simple boolean patches and in-memory checks to limit what an agent could do. If an agent tried to run a dangerous command, the plugin blocked it. 

However, as we scaled up to complex coordinator workflows—where a Primary Agent delegates to a Coordinator, which then spawns multiple concurrent Leaf Workers—the boolean approach collapsed:
- **Hanging Workflows:** If a child worker crashed or went silent, the Primary Agent would block forever waiting for completion.
- **Race Conditions:** Concurrent workers claiming execution tokens frequently overwrote each other's state.
- **Late Arrivals:** A child that timed out could wake up days later, blindly overwrite its failure state with a success flag, and silently poison the parent’s workflow.

We needed a system that treated agent workflows exactly like distributed microservices.

---

### The 2.0 Solution: FSM & The Cryptographic Ledger

Attention Guard 2.0 completely replaces the legacy file-based token system with a highly concurrent, WAL-mode SQLite Ledger and a strict Finite State Machine. 

Here are the key technical pillars of the new architecture:

#### 1. Cryptographic UUID Tokens & Atomic Claims
Every time a subagent is invoked, it is issued a strict `[a-f0-9\-]` UUID token. To prevent race conditions during concurrent worker execution, token claiming is now bound by a transactional, atomic `UPDATE ... WHERE claimed = 0` query. This completely eliminates the multi-reader race condition, ensuring that an execution token can never be double-spent.

#### 2. Strict Execution Bounding (`remaining_depth`)
We implemented a strict hierarchical depth limit (`remaining_depth`). 
- **Primary Agents** are restricted to planning, reasoning, and artifact creation. Shell execution is physically denied.
- **Coordinators** (`DeepCoder`) are issued tokens with `may_delegate: True` and `remaining_depth: 1`, allowing them to spawn exactly one layer of execution workers.
- **Leaf Workers** receive `remaining_depth: 0`. If a leaf worker attempts to spawn a subagent or bypass its directive, the tool hook forcibly denies the action. 

#### 3. Heartbeat Liveness and Global Lazy Timeouts
In 1.0, a hung subagent permanently froze the Primary Agent. In 2.0, every time a child yields (the `WAITING` state), its `updated_at` heartbeat is refreshed in the ledger. 

Every time a hook fires, a global lazy pruning sweep runs across the database:
```sql
UPDATE work_items SET status = 'TIMED_OUT' 
WHERE status NOT IN ('TERMINATED', 'FAILED', 'TIMED_OUT') 
AND COALESCE(updated_at, created_at) < ?
```
If a Primary Agent checks its execution queue and finds all active work has been swept to `TIMED_OUT`, it legally injects a `WORK_TIMED_OUT` event on behalf of its dead children. This breaks the deadlock, transitioning the FSM to `RECOVERY_REQUIRED` and returning control to the orchestrator.

#### 4. Absolute Terminal Immutability
What happens if a timed-out worker suddenly wakes up and tries to report a successful completion? 

Attention Guard 2.0 enforces terminal immutability at the database level. Any transition to `TERMINATED` is strictly guarded by a `WHERE status = 'ACTIVE'` condition. If a late child tries to stop after being pruned, the `UPDATE` yields a rowcount of 0. The hook instantly exits without emitting a success event into the ledger, preserving the integrity of the FSM.

#### 5. Read-Only Diagnostics & Aggressive Retention
To ensure the ledger doesn’t grow indefinitely, we built an aggressive 48-hour retention policy that opportunistically prunes dead turns, orphaned tokens, and expired work items. Furthermore, we decoupled our diagnostic tooling to operate strictly under `?mode=ro` (read-only), allowing engineers to safely introspect the FSM state without accidentally triggering side-effects or locking the WAL file.

---

### Conclusion

By moving away from conversational prompt engineering and towards hard, cryptographic database constraints, the Antigravity Attention Guard 2.0 guarantees that autonomous AI orchestration remains secure, bounded, and deterministic. 

The days of phantom subagents and hung workflows are over. Welcome to production-ready agentic orchestration.
