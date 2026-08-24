# Code Review Methodology

LOAD-WHEN: any coder agent enters review mode (user asks to "review", "audit", "rate quality", "check code", "production readiness")

## Review Stage Catalogue

Seven stages in two modes. MUST present as a numbered menu and ask which stages to run before executing any stage.

### Detect Stages — objective, pattern-matchable, no dialogue needed

| # | Stage | What it covers |
|---|-------|----------------|
| 1 | Automated Tools | Static analysis — run all tool slots, capture exit codes and raw output |
| 2 | Type Safety | Type hint coverage, use of `Any`, untyped return values, annotation correctness |
| 3 | Error Handling | Exception specificity, propagation chain, missing catches, bare except |
| 7 | Code Clarity | Naming, docstrings, log message quality, readability |

AI finds issues, reports them with code pairs. No user input required mid-stage.

### Consultant Stages — require domain knowledge the user holds

| # | Stage | What it covers |
|---|-------|----------------|
| 4 | Architecture | SRP, cohesion, coupling, design patterns, composition correctness |
| 5 | Robustness | Timeouts, env var validation, resource cleanup, edge cases, startup checks |
| 6 | Testability | DI seams, pure function extraction, mock surface, constructor test hooks |

AI surfaces **concerns as questions**, not verdicts. User answers → classified as finding or non-issue. User can't answer yet → recorded as open question and AI moves on. See [Consultant Stage Protocol](#consultant-stage-protocol).

**"All"** runs stages 1–7 in order.

**Rules:**
- MUST present this menu before executing anything
- MUST ask "Which stages? (numbers, ranges, or 'all')" and wait for reply
- MUST NOT begin stage execution without explicit stage selection from the user

---

## Stage Checklists

### Stage 2: Type Safety — Detect

Check every item. Flag any that fail.

- [ ] Every function/method has a return type annotation
- [ ] No parameter is missing a type annotation
- [ ] No bare `Any` used where a concrete type is known
- [ ] No `# type: ignore` without a specific error code (e.g. `# type: ignore[no-untyped-call]`)
- [ ] No old-style typing imports: `Union`, `Optional`, `List`, `Dict` — use `|`, `list`, `dict`
- [ ] Nullable returns (`T | None`) are guarded before attribute access
- [ ] Annotation-only imports are under `TYPE_CHECKING`

---

### Stage 3: Error Handling — Detect

Check every item. Flag any that fail.

- [ ] No bare `except:` — all except clauses catch a specific type
- [ ] No `except Exception:` without re-raising or logging with full context
- [ ] All `raise X from e` chains preserve the original exception
- [ ] `os.environ["KEY"]` calls are wrapped — raw `KeyError` is not acceptable at a boundary
- [ ] External call failures (HTTP, SOAP, DB) produce a domain exception, not a raw library exception
- [ ] No silent swallowing: `except ...: pass` without a comment explaining why
- [ ] Resources opened in `try` blocks are closed in `finally` or via context manager

---

### Stage 4: Architecture — Consultant

For each item below, inspect the code, then ask the user one question if the concern applies.

**Inspect first (detectable):**
- Class method count > 10 → possible God class
- Module imports > 8 other internal modules → possible high coupling
- Class has methods from clearly different concern domains (e.g. both data access and business logic) → possible SRP violation
- Circular import chain detectable by tracing imports
- Controller calls repository directly, skipping service layer → layer violation

**Then ask (consultant):**
- "This class has [N] methods across [concern A] and [concern B]. Is that intentional, or should they be split?"
- "This module imports from [N] other modules. Is that expected for its role, or has scope crept in?"
- "I see [class] handling both [X] and [Y]. Was that a deliberate design choice?"
- "The controller calls the repository directly here. Is there a reason the service layer is bypassed?"

---

### Stage 5: Robustness — Consultant

**Inspect first (detectable):**
- `Transport(session=...)` or HTTP client with no `timeout` parameter → missing timeout
- `os.environ["KEY"]` without try/except → raw KeyError on missing config
- File path used without `.exists()` check before open → possible FileNotFoundError at runtime
- `Session` or connection object created but no `.close()` or context manager → resource leak
- Hardcoded URLs, ports, or credentials in source → config should be env vars
- No retry on network calls (single attempt, no backoff)

**Then ask (consultant):**
- "There's no timeout on [transport/client]. Is a hung downstream acceptable here, or should there be a circuit break?"
- "Missing env var raises a raw `KeyError`. Should startup fail fast with a clear message listing all required vars?"
- "The WSDL/config file path is not validated at startup. Is a deferred `FileNotFoundError` acceptable, or should it fail at init?"
- "No retry logic on [operation]. Is that intentional — e.g. is idempotency a concern here?"

---

### Stage 6: Testability — Consultant

**Inspect first (detectable):**
- External dependency (HTTP client, DB connection, SOAP client) instantiated directly inside `__init__` with no injection path
- No `@classmethod` or factory function accepting pre-built dependencies
- Side effects at module level (network calls, file reads outside of functions)
- Global mutable state (module-level variables mutated by functions)
- Functions that call `datetime.now()`, `random`, or `uuid` directly — not injectable
- Method is 40+ lines with multiple concerns — hard to test one path in isolation

**Then ask (consultant):**
- "[Class] constructs [dependency] directly in `__init__`. Is there a test environment where that's acceptable, or do tests need to inject a mock?"
- "There's no factory or classmethod that accepts a pre-built [dependency]. Is that a gap, or are tests expected to patch at the module level?"
- "This function calls `datetime.now()` directly. Does the test suite need to control time, or is that not a concern?"
- "[Function] is [N] lines covering [concerns]. Is splitting it in scope, or is the current boundary intentional?"

---

### Stage 7: Code Clarity — Detect

Check every item. Flag any that fail.

- [ ] All public functions/classes/methods have docstrings
- [ ] No single-letter variable names outside of loop counters (`i`, `j`, `k`)
- [ ] No function names shorter than 5 characters (except well-known conventions: `get`, `set`)
- [ ] No consecutive `print()` calls for a single logical message — use `inspect.cleandoc` + one `print(var)`
- [ ] No complex expressions embedded directly in `cleandoc` f-strings
- [ ] Log messages include the key discriminator fields (IDs, operation names)
- [ ] No TODO/FIXME/HACK comments without a linked issue or explanation

---

## Review Tool Slots

Each coder agent provides these slot values when loading this reference.

| Slot | Description | Required |
|------|-------------|----------|
| `{STATIC_ANALYSIS}` | Type checker — validates type correctness | Yes |
| `{LINT}` | Linter — detects code quality violations | Yes |
| `{FORMAT_CHECK}` | Formatter check — detects formatting violations | Yes |
| `{SECURITY}` | Security scanner — detects vulnerability patterns | Yes — tool AND project config file must be present |
| `{COMPLEXITY}` | Complexity analyser — flags functions above threshold | Yes — tool AND project config file must be present |

**CONSTRAINT:** All five tool slots MUST be runnable before Stage 1 can begin. Tools marked "Yes" are not optional. If a tool is missing or its project config file is absent, Stage 1 MUST stop and report the gap before running any slot.

Stage 1 pre-flight check:
1. Verify each tool binary is on PATH
2. Verify any required project config file exists (e.g. `.golangci.yml`, `.gosec.yaml`)
3. If any slot fails pre-flight: report missing tool/config, instruct the user to install/commit it, then stop
4. Only run slots once all five pass pre-flight

---

## Consultant Stage Protocol

Applies to stages 4 (Architecture), 5 (Robustness), 6 (Testability).

**For each concern detected, AI MUST:**
1. State what it observed (factual, no verdict)
2. Ask one focused question to determine if it is intentional
3. Wait for user reply

**Three outcomes:**

| User reply | Action |
|------------|--------|
| Confirms it is a problem | Classify as finding, write to plan file with severity + code pair |
| Explains it is intentional / has context AI lacked | Note as non-issue, write rationale to plan file |
| "I don't know" / "I need to check" / no clear answer | Record as **open question** in plan file, move on |

**Question format:**
```
I noticed [specific observation in file:line].
This could mean [consequence A] or it could be intentional if [condition B].
Is [specific question]?
(If you're not sure, say so and I'll log it as an open question.)
```

**Rules:**
- MUST ask one question at a time — not a list of questions at once
- MUST NOT issue a verdict before the user replies
- MUST NOT block the stage on an unanswered question — if user says "move on", record as open question immediately
- MUST move to the next concern after each reply (answered or deferred)

---

## Review Plan File

**Location:** `tmp/review-<slug>-<YYYY-MM-DD>.md`

**slug:** target path with slashes replaced by dashes, max 30 chars
- `src/services/api_client/` → `services-api-client`
- `src/app/controllers/users.py` → `app-controllers-users`

**Format:**
```markdown
# Review Plan: <slug>
**Date:** <YYYY-MM-DD>
**Target:** <file or directory>
**Selected Stages:** <comma-separated list, e.g. "1, 2, 5, 6">

## Stages
- [ ] 1. Automated Tools
- [ ] 2. Type Safety
- [ ] 5. Robustness
- [ ] 6. Testability

## Findings

### Stage 1: Automated Tools
[appended after stage 1 completes]

### Stage 2: Type Safety
[appended after stage 2 completes]

## Open Questions

### Stage 5: Robustness
[open questions appended here — one entry per deferred concern]

### Stage 6: Testability
[open questions appended here]
```

**Rules:**
- MUST create the plan file before executing stage 1
- MUST update stage checkbox from `[ ]` to `[x]` immediately after stage completes
- MUST append findings under the correct stage heading before marking complete
- MUST NOT overwrite or delete previous stage findings
- IF `tmp/` directory does not exist: create it
- IF user says "continue", "resume", or "next stage" without active review context:
  1. List `tmp/review-*.md` files and ask which review to resume (if more than one)
  2. `readFile tmp/review-<slug>-<date>.md`
  3. Identify the first stage still marked `[ ]`
  4. Inform the user: "Resuming review of <target> — next stage: N. <Name>. Continue?"
  5. MUST wait for confirmation before executing the stage

---

## Per-Stage Report Format

After each stage completes, output exactly this structure in chat — findings summary only, not the full code pairs (those go in the plan file):

```
---
**Stage N: <Name>** [Detect / Consultant] — Score: X/10

🔴 <count> critical  🟡 <count> medium  🟢 <count> low  ❓ <count> open questions

<finding bullets, one per issue, max 2 lines each>
🔴 <category>: <one-line description>
🟡 <category>: <one-line description>
🟢 <category>: <one-line description>
❓ <category>: <one-line open question summary>

(or "No issues found." if clean)

---
Next: Stage N+1 — <Name>. Continue?
```

**Rules:**
- MUST include score even if 10/10
- MUST include open question count for consultant stages (may be 0)
- MUST NOT paste full code blocks in the per-stage chat summary — full code pairs go in the plan file only
- MUST end every stage output with "Continue?" or "Review complete." if last stage
- MUST wait for user reply before proceeding to next stage
- Severity classification: 🔴 architecture / security / resource leaks | 🟡 missing catches / robustness / testability gaps | 🟢 naming / clarity / minor | ❓ deferred — needs investigation

---

## Plan File Findings Format

Each finding written into the plan file MUST use this format:

```markdown
#### <Severity emoji> <Category>: <Short title>
**Location:** `path/to/file.py:line`
**Severity:** High / Medium / Low

**Current Code:**
```python
# exact problematic code
```

**Recommendation:**
```python
# working alternative
```

**Rationale:** <Impact type>: <specific consequence>
```

Each open question written into the plan file MUST use this format:

```markdown
#### ❓ <Category>: <Short title>
**Location:** `path/to/file.py:line`
**Observation:** <what AI detected, factual>
**Question:** <the unanswered question>
**Possible outcomes:**
- If [condition A]: classify as [severity] finding → [recommended action]
- If [condition B]: non-issue, no action needed
```

---

## Completion Handoff

When all selected stages are marked `[x]` in the plan file, output:

```
## Review Complete: <slug>

| Stage | Score | Open Qs |
|-------|-------|---------|
| 1. Automated Tools | X/10 | — |
| ...   | ...   | ...     |
| **Overall** | X/10 | N open |

**Top findings:**
- 🔴 <most critical>
- 🟡 <most impactful medium>
- 🟡 <second medium>

**Open questions requiring investigation:** (if any)
- ❓ <Stage N>: <one-line summary>
- ❓ <Stage N>: <one-line summary>
  (Full details in tmp/review-<slug>-<date>.md → ## Open Questions)

Fix options:
  A) Fix with <CODER-AGENT> — delegates all findings to the coder agent (open questions excluded)
  B) Fix here — apply fixes directly, one finding at a time (highest severity first)
  C) Stop — review only, plan file left in tmp/ for later
```

**Rules:**
- MUST present all three options
- IF option A: pass plan file path to the coder agent as context; coder reads findings and applies fixes; open questions are NOT passed — they require human investigation
- IF option B: fix one finding per turn, mark it resolved in the plan file, confirm with user before next; skip open questions
- IF option C: STOP — leave plan file intact
- MUST NOT auto-select an option — wait for user reply
- Open questions are NEVER auto-fixed — they always require explicit user direction
