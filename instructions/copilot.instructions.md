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
Use the consuming project's `.venv`. This library opened alone may not have one.

## Agent Awareness

When answering questions about source code, read the relevant agent file(s) from `.github/agents/` before responding — they contain the standards, constraints, and patterns that apply to this project. In this library's own repo, drop the `.github/` prefix.

| Topic | Agent file |
|-------|-----------|
| Python code quality, type hints, formatting, linting, code review | `.github/agents/python-coder.agent.md` |
| Go code quality, GOPROXY, dspy-go | `.github/agents/golang-coder.agent.md` |
| Jenkins pipelines, CI/CD | `.github/agents/jenkins-coder.agent.md` |
| Git branch, commit, merge, push | `.github/agents/git-specialist.agent.md` |
| Documentation structure | `.github/agents/doc-architect.agent.md` |
| Documentation editing, tone | `.github/agents/doc-editor.agent.md` |
| PR evidence chronicle | `.github/agents/pr-chronicler.agent.md` |
| Session findings into `tmp/scribe/` | `.github/agents/copilot-session-scribe.agent.md` |
| Creating or reviewing agent definition files | `.github/agents/agent-smith.agent.md` |
| Copilot CLI invocations, agent files, plugins | `.github/agents/copilot-cli-specialist.agent.md` |

MUST use the agent's constraints and standards to inform your answer. MUST cite specific rules when they apply.
