# VS Code Copilot Agents

![Copilot League](media/copilot-league.jpeg)

## *Not all heroes wear capes. Some just know the rules.*

A self-maintaining library of VS Code GitHub Copilot agents. Each agent is a specialised mode: a domain expert that enforces a specific standard (code style, pipeline structure, documentation clarity). The library stays coherent because every agent was authored and is maintained to the same foundational standard: the one defined by AGENT-SMITH.

## What You'll Learn

**Getting Started:**
- [What's Included](#whats-included) - Agents, personas, and instructions shipped with this library
- [Adding to a Project](#adding-to-a-project) - Clone into `.github/` and start using in under a minute

**How It Works:**
- [Personas](#personas) - Behavioural blueprints that govern how agents confirm intent and resolve forks
- [How the Library Stays Consistent](#how-the-library-stays-consistent) - The four standards every agent is built and maintained to

## 📋 What's Included

**Agents** (`.github/agents/`) — each built and maintained to AGENT-SMITH's standards:

| Agent | What it does |
|---|---|
| 🤖 AGENT-SMITH | Creates and maintains agent definition files |
| ⚡ COPILOT-CLI-SPECIALIST | Designs Copilot CLI invocations, agent files, and plugin configs |
| 📓 COPILOT-SESSION-SCRIBE | Captures live session findings into `tmp/scribe/` docs in PR-CHRONICLER-ready format |
| 🏗️ DOC-ARCHITECT | Structures documentation for cognition — hierarchy, narrative, disclosure |
| 📝 DOC-EDITOR | Removes fluff from technical docs while preserving rationale |
| 🔀 GIT-SPECIALIST | Diagnoses branch state and executes branch, commit, merge, and push workflows safely |
| 🐹 GOLANG-CODER | Enforces safe, formatted, idiomatic Go |
| 🔧 JENKINS-CODER | Builds Jenkins pipelines following dispatcher pattern and enterprise standards |
| 📜 PR-CHRONICLER | Produces a dated evidence chronicle for a branch/PR from git and workspace artefacts |
| 🐍 PYTHON-CODER | Enforces type hints, formatting, linting compliance, and code review |

Once cloned into `.github/`, the agents appear in VS Code's agent picker automatically:

![VS Code agent list showing the agents in the Copilot chat panel](media/vscode-agent-list.png)

**Global instructions** (`copilot-instructions.md`) — workspace-wide rules active in every Copilot mode including Ask.

**Personas** (`.github/agents/personas/`) — behavioural blueprints referenced by the agents.

## 📦 Adding to a Project

Clone the repo directly as the `.github` folder in your project root, then ignore it so it stays out of your project's git history:

```bash
cd /path/to/your/project
git clone ssh://git@git.example.com/org/vscode-copilot-agents.git .github
echo ".github" >> .gitignore
```

Replace the clone URL with your org's copy of this library. Then set `REGISTRY_VENDOR` to `artifactory` or `nexus` in `.github/agents/references/environment.md` and fill every Value cell with your registry hosts, credential IDs, proxy, and git URLs. Agents read that file for all org-specific values.

VS Code picks up agents and instructions automatically.

## 🎭 Personas

Personas govern how agents behave before and during execution. Two personas ship with this library:

**Intent-First** — agent states its read of the goal and asks "Does this match what you have in mind?" before touching anything.

**Consultant** — when execution reaches a fork with meaningful trade-offs, agent proposes options and waits for a decision.

Most agents compose both: Intent-First confirms the goal, Consultant resolves approach forks mid-execution.

## ⚙️ How the Library Stays Consistent

AGENT-SMITH is the meta-agent that defines the generic workflow, constraint language, and verification standards every other agent is held to. Every agent in this library was built by AGENT-SMITH, and any new agent goes through it before being added.

Four standards apply to every agent:

**Confirm intent before acting.** Every agent uses the Intent-First workflow: state your read of the goal, wait for explicit confirmation before touching anything.

**Constraint language.** Requirements use MUST/NEVER/ALWAYS, not "should" or "consider". Agents issue commands, not suggestions.

**Binary verification.** Every checklist item has a TRUE/FALSE outcome with a concrete verification method. No subjective "looks good": every check either passes or it does not.

**Executable examples.** Every constraint pairs a CORRECT and PROHIBITED implementation. No requirement ships without a template the AI can act on directly.
