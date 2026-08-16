---
applyTo: "**"
description: "Workspace-wide rules: scope consent before changes, no unsolicited docs, agent-file-aware responses."
---
## Scope Consent (Mandatory for All Code Changes)

Before modifying any file, function, or code that was not explicitly referenced in the request, STOP.
State what additional change is required and why, then ask: "This also requires changing [X] — proceed?"
Do NOT make the change until the user confirms. This applies to all agents and all modes.

## Documentation Rules

- MUST NOT create README.md or any documentation file unless explicitly requested
- MUST NOT add docstrings, comments, or type annotations to code that was not changed
- If a change summary is needed, provide it in the response text — never as a file

## Scripting Language

When a helper or utility script is needed, MUST use Python.
MUST NOT create PowerShell scripts (.ps1) or shell scripts (.sh) as helpers.
The workspace has a `.venv` already configured — use it.

## Agent Awareness

When answering questions about source code, read the relevant agent file(s) from `agents/` before responding — they contain the standards, constraints, and patterns that apply to this project:

| Topic | Agent file |
|-------|-----------|
| Python code quality, type hints, formatting, linting, code review | `agents/python-coder.agent.md` |
| Jenkins pipelines, CI/CD | `agents/jenkins-coder.agent.md` |
| Documentation structure | `agents/doc-architect.agent.md` |
| Documentation editing, tone | `agents/doc-editor.agent.md` |

MUST use the agent's constraints and standards to inform your answer. MUST cite specific rules when they apply.
