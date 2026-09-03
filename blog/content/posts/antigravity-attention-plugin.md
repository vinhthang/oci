---
title: "Under the Hood: How the Antigravity Attention Guard Plugin Enforces Deterministic Agent Governance"
author: "Vinh Thang"
date: "2026-09-03"
draft: false
categories: ["AI Engineering", "Autonomous Agents", "Architecture", "Open Source"]
tags: ["Antigravity", "Attention Dilution", "LLM Governance", "Subagents", "Python", "RTK", "Plugins"]
---

In our previous discussions on autonomous engineering, we explored the phenomenon of **Attention Dilution**—the silent degradation of instruction-following fidelity as context windows swell past tens of thousands of tokens. While modern frontier models boast context windows of 1M+ tokens, attention mechanisms remain vulnerable to informational entropy. As terminal logs, stack traces, and code diffs accumulate, system prompt constraints drift out of the model's active attention focus.

When left unchecked, agents exhibit architectural amnesia: they bypass project-level Architecture Decision Records (ADRs), run uncompressed shell commands that flood context, guess port allocations, or skip verification steps.

To solve this, we open-sourced the [Antigravity Attention Guard Plugin](https://github.com/vinhthang/antigravity-attention-guard-plugin). In this post, we dive into the internal mechanics of the plugin, examining how its lifecycle hooks, dynamic tool inspection, and subagent orchestration transform non-deterministic LLM behavior into predictable, production-grade engineering workflows.

---

## Architectural Philosophy: Guardrails Over Prompting

A common anti-pattern in agent design is attempting to cure attention loss through more prompting: repeating instructions, shouting in capital letters, or stuffing more examples into the system context. This exacerbates the problem by consuming tokens and diluting attention further.

The Antigravity Attention Guard Plugin takes the opposite approach: **deterministic runtime interception**. Instead of hoping the model follows governance rules, the plugin enforces invariants at the agent platform's lifecycle hook boundaries:

1. **PreToolUse Hooks**: Intercept, validate, rewrite, or reject tool calls before execution.
2. **Stop Hooks**: Intercept agent completion states, verify output quality, and reject improper halts with contextual memory refreshes.

```
       +-----------------------------------------------------------+
       |                   Primary Agent Turn                      |
       +-----------------------------------------------------------+
                                     |
                          [Tool Execution Request]
                                     |
                                     v
                 +---------------------------------------+
                 |    PreToolUse Hook Pipeline           |
                 +---------------------------------------+
                 | 1. enforce-delegation.py              |
                 |    - Is tool mutating?                |
                 |    - Is caller Primary Agent?         |
                 |    ==> DENY (force Subagent spawn)    |
                 |                                       |
                 | 2. rtk-enforcer.py                    |
                 |    - Is command allowlisted?          |
                 |    ==> OVERWRITE (prepend `rtk `)     |
                 |                                       |
                 | 3. inject-rules.py                    |
                 |    - Is invoke_subagent called?       |
                 |    ==> OVERWRITE (inject AGENTS.md)   |
                 +---------------------------------------+
                                     |
                                     v
       +-----------------------------------------------------------+
       |               Execution or Subagent Handoff               |
       +-----------------------------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 |          Stop Hook Pipeline           |
                 +---------------------------------------+
                 | attention-check.py                    |
                 | - Elapsed time > threshold?           |
                 | - Valid skill summary present?        |
                 | ==> CONTINUE & INJECT CONTEXT RULES   |
                 +---------------------------------------+
```

Let's dissect the core components and recent updates powering this pipeline.

---

## 1. Hardware-Grade Delegation (`enforce-delegation.py`)

The centerpiece of the plugin is enforcing a strict **two-phase lifecycle**:
- **Phase 1 (Primary Agent)**: High-level reasoning, risk analysis, task breakdown (`task.md`), and implementation planning (`implementation_plan.md`). The Primary Agent is strictly forbidden from directly touching codebase files or executing arbitrary shell commands.
- **Phase 2 (Subagents)**: Focused, short-lived subagents spawned to perform deterministic code modifications, run tests, or execute terminal commands.

### Dynamic MCP Write Tool Discovery

Hardcoding tool names is fragile. Modern AI workflows interact with diverse Model Context Protocol (MCP) servers—GitLab, OCI, local filesystems, databases, and issue trackers.

`enforce-delegation.py` dynamically scans the MCP schema directory (`~/.gemini/antigravity/mcp/`) to detect mutating operations on the fly:

```python
WRITE_VERB_PREFIXES = (
    "write", "edit", "create", "update", "delete", "remove",
    "push", "move", "fork", "insert", "modify", "set", "put",
    "patch", "deploy", "add", "transition", "fill",
)
```

Any MCP tool matching mutating verb prefixes is automatically categorized as a write operation. If the Primary Agent attempts to invoke it directly, the hook returns a deterministic rejection payload:

```json
{
  "decision": "deny",
  "reason": "Attention Dilution Guard: The Primary Agent is restricted to planning and artifact creation. Direct code modification and shell execution must be delegated to a subagent (Model: 'flash')."
}
```

To eliminate filesystem scanning overhead during fast conversational loops, discovered tools are cached in a user-scoped directory (`~/.gemini/antigravity/cache/agy_mcp_write_tools.json`) with a 5-minute TTL.

### Robust Subagent Detection

In the Antigravity hook contract, subagents are identified primarily via model naming (`flash` tiers vs. full reasoning models) and secondarily via conversation ID tracking against the workspace primary:

```python
def is_subagent(data):
    model_name = data.get("modelName", "").lower()
    if "flash" in model_name:
        return True
    
    # Secondary: workspace-level conversation ID tracking
    conv_id = data.get("conversationId", "")
    workspace_paths = data.get("workspacePaths", [])
    if conv_id and workspace_paths:
        ...
```

Artifact paths (`/brain/<uuid>/...`) are explicitly allowlisted, allowing the Primary Agent to author plans, checklists, and documentation while blocking unreviewed changes to production code.

---

## 2. Token Compression at the Gate (`rtk-enforcer.py`)

A primary contributor to Attention Dilution is noisy terminal output: verbose build logs, wide `ps aux` tables, mega-byte JSON payloads from cloud CLIs, and full diffs.

[RTK (Rust Token Killer)](https://github.com/vinhthang/rtk) solves this by pre-filtering and compressing CLI output by 60% to 95%. However, agents under attention stress frequently forget to type the `rtk` prefix.

`rtk-enforcer.py` acts as an automated proxy inside the `PreToolUse` hook for `run_command`. It checks an extensive allowlist of token-heavy tools:

```python
RTK_COMPATIBLE = [
    "kubectl", "git", "docker", "docker-compose", "podman",
    "mvn", "gradle", "./gradlew", "go ", "cargo", "rustc",
    "npm", "npx", "pnpm", "yarn",
    "pip ", "pip3", "uv ", "ruff", "pytest",
    "aws", "oci", "gcloud", "az ",
    "terraform", "tofu", "helm", "curl", "brew",
    "lsof", "ps ", "rg ", "find ", ...
]
```

When a subagent issues a command such as `git log -n 10 --stat`, the hook intercepts the call and rewrites it dynamically:

```json
{
  "decision": "allow",
  "overwrite": {
    "CommandLine": "rtk git log -n 10 --stat"
  }
}
```

The script gracefully handles environments where RTK is not yet installed via `shutil.which("rtk")`, and skips commands that already include `rtk` or pipe through it.

---

## 3. Automated Rule Injection on Subagent Spawn (`inject-rules.py`)

When the Primary Agent spawns a subagent, the subagent initializes with a clean context window. However, without explicit instruction injection, subagents can lose awareness of critical project rules, such as escalation protocols or JSON handoff standards.

`inject-rules.py` targets the `invoke_subagent` tool. When invoked, it reads the plugin's canonical `rules/AGENTS.md` and dynamically appends it to each subagent's prompt:

```python
tool_call = payload.get("toolCall", {})
if tool_call.get("name") == "invoke_subagent":
    args = tool_call.get("args", {})
    subagents = args.get("Subagents", [])
    for sa in subagents:
        sa["Prompt"] = sa.get("Prompt", "") + injected

    print(json.dumps({
        "decision": "allow",
        "overwrite": {
            "Subagents": subagents
        }
    }))
```

This guarantees that every subagent, regardless of how concisely the Primary Agent framed the prompt, operates under identical governance standards from turn zero.

---

## 4. Context Refresh via Stop Hook (`attention-check.py`)

Even with delegation and token compression, agents in deep multi-step sessions can drift. A common symptom is concluding a task without providing required verification artifacts or skill summaries.

`attention-check.py` executes on the `Stop` event. It evaluates session duration and inspects the final model response:

1. **Reverse Transcript Parsing**: Reads the JSONL transcript file backwards in chunks from disk, locating the final `PLANNER_RESPONSE` in constant time without loading gigabyte-sized session histories into memory.
2. **Quality Verification**: Checks whether mandatory summary markers (e.g., `Summary of skills used:`) are present.
3. **Dynamic Rule Harvesting**: If omission is detected after the timeout threshold (default 120s), the hook walks:
   - Plugin-specific rules (`rules/*.md`)
   - Workspace rules (`GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`)
   - Global user rules (`~/.gemini/config/rules/*.md`)
   - Global skill definitions (`~/.gemini/config/skills/*/SKILL.md`)
4. **Context Injection**: Rejects the `Stop` event with `{"decision": "continue"}` and injects the assembled rule contents directly into the agent's context as an ephemeral system message.
5. **Infinite Loop Protection**: Tracks consecutive rejections in a session tracker (`agy_start_<conv_id>_stop_count`). After 3 consecutive rejections, it yields gracefully to avoid deadlock.

---

## 5. Model Selection Framework & Strict JSON Handoffs

In the latest updates, the plugin formalizes the **Model Selection Framework** and communication protocol in `rules/AGENTS.md`:

| Model Tier | Role | Permitted Actions |
|---|---|---|
| **`pro`** | Deep Reasoning & Escalation | High autonomy, net-new architecture, complex root-cause debugging (SSH, k3s, kernel/network). |
| **`flash`** | Mechanical Execution | Applying targeted diffs, running test suites, executing pre-planned commands. |
| **`flash_lite`** | Read-Only Research | Grep searches, file viewing, non-mutating codebase exploration. |

### The Escalation Protocol

If a `flash` subagent hits an unexpected failure (e.g., compile error, test failure), it is forbidden from guessing or blindly applying patches. It must immediately halt and return a structured failure report. The Primary Agent then escalates the investigation to a `pro` subagent.

### Zero Conversational Fluff

Subagent-to-primary communication via `send_message` is strictly constrained to valid JSON payloads:

```json
{
  "status": "completed",
  "summary": "Applied goldmark LaTeX rendering configuration to hugo.toml",
  "files_modified": ["blog/hugo.toml"],
  "verify_cmd": "rtk git diff blog/hugo.toml"
}
```

Conversational pleasantries ("Sure thing! Here is what I did...") waste context tokens and dilute primary agent attention. Strict JSON guarantees clean, machine-parseable state transitions.

---

## Installation and Setup

The plugin requires zero external Python dependencies and works out of the box with Python 3.6+:

```bash
# Clone directly into Antigravity's plugin directory
git clone https://github.com/vinhthang/antigravity-attention-guard-plugin.git \
  ~/.gemini/config/plugins/attention-guard
```

To update to the latest rules and hook scripts:

```bash
cd ~/.gemini/config/plugins/attention-guard && git pull
```

Antigravity reloads plugins dynamically without needing an IDE restart.

---

## Conclusion

Massive context windows are a superpower, but without architectural guardrails, entropy always wins. By combining hardware-level tool interception, automated token compression, dynamic rule injection, and strict subagent governance, the Antigravity Attention Guard Plugin ensures that agents remain reliable, disciplined, and obedient—whether on turn 1 or turn 100.
