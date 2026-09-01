---
title: "Open-Sourcing the Cure for Attention Dilution: The Antigravity Attention Guard Plugin"
author: "Vinh Thang"
date: "2026-09-01"
categories: ["AI Engineering", "Autonomous Agents", "Open Source", "Architecture"]
tags: ["Antigravity", "Plugin", "GitHub", "Attention Dilution"]
---

In my [previous post](/posts/attention-dilution-context-windows-agents/), I detailed the mathematical realities of "Attention Dilution" in LLMs with massive context windows, and how we engineered deterministic lifecycle hooks to prevent autonomous agents from suffering architectural amnesia.

Today, I am thrilled to announce that we have packaged that exact solution into a fully open-source, cross-platform **Antigravity Plugin**.

You can now instantly secure your own agents by cloning the [Antigravity Attention Guard Plugin](https://github.com/vinhthang/antigravity-attention-guard-plugin) directly into your configuration.

## What is in the Box?

The plugin bundles three distinct layers of protection into a single, deployable unit:

1. **The Hardware-Grade Tool Blocker (`enforce-delegation.py`)**: A `PreToolUse` hook that physically prevents the Primary Agent from mutating files or running terminal commands, forcing it to delegate low-level execution to specialized subagents.
2. **The Time-Based Guard (`attention-guard.py`)**: A `PreInvocation` hook that tracks agent session duration. If an agent spins for more than 120 seconds (configurable) without delegating, it injects an ephemeral system message forcing the agent to stop and formulate a plan.
3. **The Dynamic Context Reset (`attention-check.py`)**: A `Stop` hook that verifies the agent's output. If the agent fails to summarize its skills, this hook scans all active workspaces for architectural rules (like `GEMINI.md` or `.agents/rules/ADRs`) and dynamically builds a custom error message, physically forcing the model to re-read its own project guidelines to refresh its context window.

## Zero-Config Installation

Because Antigravity supports native Git-backed plugins, installation requires zero package managers. Just clone the repository:

```bash
git clone https://github.com/vinhthang/antigravity-attention-guard-plugin.git ~/.gemini/config/plugins/attention-guard
```

Updating the plugin to get the latest security rules is as simple as running `git pull`.

## Built for Cross-Platform Teams

Initially, our tool-blocker was a simple Bash script. While effective on Linux and macOS, it left Windows engineers out in the cold. For this open-source release, we rewrote the entire hook logic in Python. 

By standardizing on Python, the Attention Guard runs flawlessly across any operating system that Antigravity supports, without needing to maintain separate `.sh` and `.ps1` files.

## The Future of Deterministic Agent Governance

We believe that the future of autonomous engineering lies not in asking an LLM to simply *remember* the rules, but in building deterministic infrastructure that physically *enforces* them. 

Check out the [repository on GitHub](https://github.com/vinhthang/antigravity-attention-guard-plugin), star it, and let's cure Attention Dilution once and for all.
