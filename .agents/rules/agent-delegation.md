# Agent Delegation Protocol

## 1. Planning Phase (Gemini 3.1 Pro / Primary Agent)
- For non-trivial tasks (multi-file changes, migrations, complex debugging, architectural decisions), produce a structured numbered plan before making edits.
- Explicitly map blast radius, component dependencies, and exact files to inspect/modify.

## 2. Execution Phase (Gemini 3.7 Flash Subagent)
- Spawn execution subagents with `Model: "flash"` (`gemini-3.7-flash`) for running commands (`cargo test`, `npm test`, `kubectl`, `helm`), applying edits, and parsing heavy command/test outputs.
- Subagents execute the plan steps, validate intermediate checks, and summarize findings.

## 3. Escalation & Fallback
- If a subagent encounters unexpected structural errors twice consecutively, it must halt and escalate back to the primary agent (`gemini-3.1-pro`) for re-planning and root-cause analysis.
