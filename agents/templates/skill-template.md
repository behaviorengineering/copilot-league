---
name: skill-name
description: One-line description of when to load this skill (50–120 chars)
user-invocable: false
---

# Skill Name

## When to Load

Load when [specific task, file type, or agent]. Be specific — vague triggers cause the file to be skipped.

**Cited by:** `.github/agents/<owning-agent>.agent.md` — every skill MUST be listed in at least one agent's load table.

## Purpose (optional)

One paragraph: what this skill makes the agent do, and what it MUST NOT do. Omit when When to Load plus the steps are enough.

---

## Core Constraints (optional)

**CONSTRAINT:** [Fundamental rule].
- Enforcement: [how to verify]
- Violation: STOP, [fix], re-verify

**CONSTRAINT:** Rules use MUST / NEVER / ALWAYS — not "should" or "consider".

Omit this section when the skill is a short procedure whose MUST/NEVER rules live under Steps.

---

## Steps

1. **[Step name]**
   - Exact command or `readFile` path
   - Pass / fail signal

2. **[Step name]**
   - ...

---

## Rules

- MUST load from `.github/agents/skills/<name>/SKILL.md` in a consuming project
- MUST keep YAML frontmatter (`name`, `description`, `user-invocable`)
- NEVER duplicate a reference file's pattern library here — link it instead
