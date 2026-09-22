---
title: "Spec-Driven Development for Autonomous Agents: Inside the AI Review Plugin's Two-Stage Architecture"
author: "Vinh Thang"
date: "2026-09-23T00:30:00+07:00"
draft: false
categories: ["AI Engineering", "Code Review", "Architecture", "Software Engineering"]
tags: ["Spec-Driven Development", "AI Review", "DeepSeek", "WorkBuddy", "Ray Dalio", "Agent Governance", "Antigravity"]
---

When software engineers collaborate with autonomous AI coding agents, the default workflow is almost always **chat-and-code**: describe a feature in natural language, watch the model propose a code diff, test it, and iterate.

For small, single-function scripts, this works reasonably well. But for production-grade distributed systems, microservices, and multi-module architectures, this approach invariably breaks down. 

Left unconstrained, AI models suffer from **Specification Conflation**: they blur the line between **WHAT & WHY** (the architectural contracts, invariant boundaries, and failure modes) and **HOW** (the file edits, variable names, and task sequencing). The result is predictable:
- **Scope Creep:** The agent introduces unapproved libraries, extra parameters, or unintended API surface changes.
- **Architectural Amnesia:** System topology constraints, database pooling rules, or thread safety invariants defined in ADRs are silently bypassed.
- **Untested Failure Modes:** Happy paths work, but network partition recovery, deserialization bugs, and timeout semantics are ignored.

To solve this, we redesigned the **AI Review Plugin** for Google Antigravity around a strict **Two-Stage Spec-Driven Development (SDD)** workflow aligned with **Ray Dalio's 5-Step Process** and multi-model adversarial peer review.

In this article, we dive into the internal mechanics of the Two-Stage Review Architecture, our complete decoupling from legacy monolithic scripts into a modular review engine, and how pairing frontier models with **DeepSeek (`deepseek-v4.1-flash`)** delivers uncompromising code quality.

---

## 1. The Architectural Solution: Two-Stage Spec-Driven Development

The fundamental insight behind Spec-Driven Development is simple: **You cannot evaluate an implementation plan without an immutable, approved specification.**

Conflating the specification and the plan into a single document causes reviewers (both humans and AI) to focus on code diff details while missing foundational architectural flaws. The AI Review Plugin enforces a two-stage pipeline:

```
+-------------------------------------------------------------------------------------+
|                          SPEC-DRIVEN DEVELOPMENT WORKFLOW                           |
|                                                                                     |
|  +--------------------+        +---------------------+        +------------------+  |
|  |   BRAINSTORMING    | -----> |     SPEC-REVIEW     | -----> |  DESIGN-REVIEW   |  |
|  |  (Set Clear Goals) |        | (Validate WHAT/WHY) |        |  (Validate HOW)  |  |
|  +--------------------+        +---------------------+        +------------------+  |
|                                           |                            |            |
|                                           v                            v            |
|                                      SPEC APPROVAL               PLAN APPROVAL      |
|                                           |                            |            |
|                                           +----------------------------+            |
|                                                         |                           |
|                                                         v                           |
|                                                    SUBAGENT EXEC                    |
+-------------------------------------------------------------------------------------+
```

### Stage 1: The Specification Tier (`spec-review`)
- **Document Location:** `docs/specs/<feature-id>/spec.md`
- **Focus:** **WHAT & WHY**.
  - Problem framing, business goals, and domain boundaries.
  - Component topology and interface contracts (REST, gRPC, Pulsar topics, STOMP payloads).
  - Explicit failure modes, thread interruption behavior, and circuit breaking.
  - Test falsifiability criteria and architectural invariants.
- **Strict Invariant:** Prohibits operational checklists (`- [ ]`), task orderings, and code editing operations. A spec is a normative contract, not a task list.
- **The Gate:** Must pass adversarial peer review (`P0 = 0`, `P1 = 0`) and receive explicit human approval (`SPEC_GATE`) before any planning begins.

### Stage 2: The Implementation Plan Tier (`design-review`)
- **Document Location:** `docs/plans/<feature-id>/plan.md`
- **Focus:** **HOW & SEQUENCE**.
  - Clearly bounded, 2-to-5 minute implementation tasks formatted as markdown checkboxes (`- [ ]`).
  - Explicit file paths (`[NEW]`, `[MODIFY]`, `[DELETE]`).
  - Strict input/output interface definitions (`Consumes` / `Produces`).
  - Concrete test verification commands with expected exit codes and outputs.
- **Mandatory Bidirectional Traceability (`SPEC_GATE`)**:
  - The plan header must declare `**Spec:** <path_to_spec.md>`.
  - The reviewer programmatically verifies that **100% of specification requirements are covered by plan tasks**, and that **zero unapproved scope** has been snuck into the plan.
- **The Gate:** Only after `design-review` passes and receives explicit human approval (`APPROVAL_GATE`) are execution subagents dispatched.

---

## 2. Codifying Ray Dalio: "Don't Tolerate Problems"

The AI Review Plugin translates Ray Dalio’s engineering principles into automated machine gates:

```
[Review Engine Audit Output]
              │
    Are there P0 or P1 issues?
             / \
      YES   /   \   NO
           /     \
          ▼       ▼
    [BLOCK / HALT]   [APPROVAL_GATE]
    - Zero Error     - Await Human Sign-Off
      Suppression    - Delegate to Subagents
    - Remediate
```

### Zero Error Suppression
In conventional CI/CD or code review, engineers frequently ignore warnings, mask failing assertions with bare `catch (Exception e) {}`, or suppress linter errors with `|| true`. 

The AI Review Plugin treats any command failure or assertion break as a **structural blocker**:
- **Severity P0 (Critical Architectural / Security Flaw):** Discovered violations of ADRs, data races, unauthorized interface breaking changes, or memory corruption vectors. Hard execution blocker.
- **Severity P1 (Functional Omission / Contract Gap):** Unhandled error cases, missing edge-case tests, unverified external assumptions, or broken bidirectional traceability. Hard execution blocker.
- **Severity P2 (Advisory / Non-Blocking):** Stylistic feedback, naming recommendations, or minor documentation enhancements.

If a single P0 or P1 issue is detected, the review cycle halts immediately. The agent cannot proceed to code generation until the root cause is resolved and verified.

---

## 3. Decoupling from Superpowers: The Modular Review Engine

Earlier versions of the reviewer relied on external, monolithic scripts originally inherited from legacy prototypes. We executed a complete architectural refactor, completely decoupling from legacy dependencies and organizing the engine into a clean, modular Python package under `scripts/review/`:

```
scripts/
├── peer_review.py          # Unified CLI Facade
└── review/
    ├── audit.py            # CLI entrypoint, argument parsing, & ADR context budget
    ├── engines/            # Multi-engine adapter implementations
    │   ├── base.py         # Abstract ReviewEngineAdapter interface
    │   ├── workbuddy.py    # WorkBuddy AI adapter (DeepSeek engine)
    │   └── codex.py        # OpenAI Codex adapter
    ├── models.py           # Strict JSON Schema, Issue dataclasses, & Envelopes
    ├── remediation.py      # Sanitization of prior review context
    ├── fsm.py              # Declarative Finite State Machine
    └── governance.py       # ADR indexing & requirement traceability validation
```

### Key Technical Enhancements in the Modular Engine

#### 1. Context-Budgeted ADR Injection
To prevent reviewing code in a vacuum, `review.audit` dynamically indexes project Architecture Decision Records (`docs/adr/` and `docs/specs/`). It budgets up to **500,000 characters** of architectural context, ensuring the reviewer verifies system invariants without blowing past context boundaries:
```python
diag_len = len(diagnostic_text) if diagnostic_text else 0
adr_budget = max(0, 500_000 - diag_len)
adr_content = build_adr_context(repo, target_content, spec_content, max_chars=adr_budget)
```

#### 2. Declarative Finite State Machine (`review.fsm`)
Review sessions are modeled as formal state machines (`AUDIT` $\rightarrow$ `REMEDIATION` $\rightarrow$ `GOVERNANCE`). Multi-turn debates are tracked with bounded escalation counters (`attempt_counter >= 5` or `debate_counter >= 3`), preventing agents from spiraling into infinite circular arguments.

#### 3. Prompt-Injection Defense (`review.remediation`)
When feeding a prior review's findings back into an agent for remediation, untrusted code snippets in the diff could attempt to override the reviewer's instructions. `sanitize_prior_review()` escapes closing XML/Markdown delimiters (`</prior_review_context>` to `&lt;/prior_review_context&gt;`), strips non-printable control characters, and enforces strict length bounding.

#### 4. Atomic Envelope Writing with POSIX Permissions
Review outputs are written atomically using temporary swap files with restrictive `0o600` permissions, preventing race conditions or permission tampering on shared developer workstations:
```python
flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
with os.fdopen(os.open(temp_path, flags, 0o600), "w", encoding="utf-8") as f:
    json.dump(envelope, f, indent=2)
os.replace(temp_path, output_file)
```

---

## 4. Multi-Model Adversarial Rigor: DeepSeek Engine Pinning

A major vulnerability in single-model AI engineering is **Cognitive Blind Spots**: if the same model family that writes the code also reviews the code, it tends to validate its own assumptions, overlook its typical hallucinations, and rubber-stamp subtle concurrency bugs.

To achieve genuine adversarial rigor, the AI Review Plugin mandates **Heterogeneous Multi-Model Review**:

```
 ┌────────────────────────────────────────────────────────┐
 │                      PRIMARY AGENT                     │
 │          Google Gemini / OpenAI Codex / Claude         │
 │          (High-level planning & orchestration)         │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼ Dispatches Peer Review
 ┌────────────────────────────────────────────────────────┐
 │                   REVIEW ENGINE ADAPTER                │
 │         scripts/peer_review.py --engine workbuddy      │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼ Strict Engine Pinning
 ┌────────────────────────────────────────────────────────┐
 │                 ADVERSARIAL REVIEWER                   │
 │                deepseek-v4.1-flash                     │
 │  - Ultra-fast token generation                         │
 │  - Unforgiving structural flaw detection               │
 │  - Zero shared training bias with orchestrator         │
 └────────────────────────────────────────────────────────┘
```

### Why `deepseek-v4.1-flash`?
1. **Adversarial Diversity:** DeepSeek's reasoning patterns and training distributions are fundamentally distinct from Gemini and GPT-5, allowing it to catch edge cases that the primary model took for granted.
2. **Deterministic Speed:** Reviews return in seconds, preventing engineers from abandoning the review gate out of impatience.
3. **Strict Engine Pinning:** We codified strict model normalization in `review.models` to guarantee that all WorkBuddy review invocations resolve to `deepseek-v4.1-flash`. This prevents unexpected model escalation, eliminates quota blowouts, and ensures 100% predictable review latency.

---

## 5. The Three Review Skills in Action

The AI Review Plugin exposes three intuitive skills inside Antigravity:

| Skill | Target | Purpose | Key Gate |
| :--- | :--- | :--- | :--- |
| **`spec-review`** | `docs/specs/<feature>/spec.md` | Validates architecture, boundaries, interfaces, and failure modes. | `SPEC_GATE` (Must receive human approval before plan creation). |
| **`design-review`** | `docs/plans/<feature>/plan.md` | Validates task sizing, test commands, and 100% bidirectional spec traceability. | `APPROVAL_GATE` (Blocks code generation until spec alignment is proven). |
| **`code-review`** | Git staged/working diff | Conducts adversarial peer review on generated code diffs, outputs to `review.md`. | `QUALITY_GATE` (P0/P1 must be 0 before merging). |

---

## Conclusion: From Hope to Guarantees

The transition from hobbyist AI assistance to enterprise-grade autonomous engineering requires abandoning hope-based prompts in favor of **deterministic architectural governance**.

By splitting the engineering lifecycle into **Two-Stage Spec-Driven Development**, backing it with a **modular state machine**, and enforcing **heterogeneous multi-model review with DeepSeek**, the AI Review Plugin guarantees that software written by AI meets the exact same standards of architectural integrity as software written by principal human engineers.

Explore the architecture and inspect the open-source implementation:
👉 **[github.com/vinhthang/ai-review-plugin](https://github.com/vinhthang/ai-review-plugin)**
