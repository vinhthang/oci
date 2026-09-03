<rule name="agent-delegation">
  <description>
    Two-phase agent lifecycle protocol defining primary agent planning and subagent execution/escalation policies.
  </description>

  <constraints>
    - For non-trivial tasks (multi-file changes, migrations, complex debugging, architectural decisions), produce a structured numbered plan before making edits.
    - Explicitly map blast radius, component dependencies, and exact files to inspect/modify.
    - Spawn execution subagents with `Model: "flash"` (the platform's latest flash-tier alias) for running commands (`cargo test`, `npm test`, `kubectl`, `helm`), applying edits, and parsing heavy command/test outputs.
    - Subagents execute the plan steps, validate intermediate checks, and summarize findings.
    - If a subagent encounters unexpected structural errors twice consecutively, it must halt and escalate back to the primary agent (`gemini-pro`) for re-planning and root-cause analysis.
  </constraints>

  <instructions>
    # Agent Delegation Protocol

    ## 1. Planning Phase (Pro Tier / Primary Agent)
    - For non-trivial tasks (multi-file changes, migrations, complex debugging, architectural decisions), produce a structured numbered plan before making edits.
    - Explicitly map blast radius, component dependencies, and exact files to inspect/modify.

    ## 2. Execution Phase (Flash Tier Subagent)
    - Spawn execution subagents with `Model: "flash"` (the platform's latest flash-tier alias) for running commands (`cargo test`, `npm test`, `kubectl`, `helm`), applying edits, and parsing heavy command/test outputs.
    - Subagents execute the plan steps, validate intermediate checks, and summarize findings.

    ## 3. Escalation & Fallback
    - If a subagent encounters unexpected structural errors twice consecutively, it must halt and escalate back to the primary agent (`gemini-pro`) for re-planning and root-cause analysis.
  </instructions>
</rule>
