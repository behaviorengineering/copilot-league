# Documentation Revision Skill

## When to Load

Load when DOC-ARCHITECT or DOC-EDITOR needs to systematically proofread and refine documentation through ordered editorial filters. Use when the user asks to "revise this doc", "run the revision process", "edit systematically", or wants step-by-step refinement rather than just assessment.

**LOAD-WHEN:** Any doc agent conducting editorial review (after `doc-cold-read` assessment or standalone).

## Purpose

Transform a draft into publication-ready documentation through five sequential filters. Each filter addresses a distinct class of problems. Do not skip steps.

---

## Core Constraints

**CONSTRAINT:** Revision MUST complete in 5 discrete steps — OPENING-CLARITY, VOICE-SCRUB, ACCESSIBILITY-PASS, FORMATTING-SWEEP, STRUCTURAL-INTEGRITY. Do NOT blend steps or omit any.

**CONSTRAINT:** Each step MUST be evaluated against strict pass/fail definitions. A step may NOT be marked Pass while any banned pattern is still present.

**CONSTRAINT:** All analysis output MUST include exact quoted violations from the original text, not paraphrased summaries.

**CONSTRAINT:** Preserve author's technical terminology, domain-specific wording, and structural headings. Change them only when required by a specific check (e.g., opening fails clarity audit, heading pattern violates rules).

---

## Pass/Fail Definitions

- **Pass**: All violations for this step are fixed in the proposed revised document. No forbidden patterns remain.
- **Fix Needed**: At least one violation from the checklist remains in the text. List them explicitly.

**A step may NOT be marked Pass while any banned pattern is still present.**

---

## The 5-Step Revision Process

| Step | Name | One-line purpose |
|------|------|------------------|
| **1** | Opening Clarity | Establish what this doc is for immediately |
| **2** | Voice Scrub | Remove hedges, passive piles, teacher framing, AI rhetoric |
| **3** | Accessibility Pass | Define jargon, verify technical terms, ensure scanability |
| **4** | Formatting Sweep | Enforce punctuation, emphasis, and visual consistency rules |
| **5** | Structural Integrity | Eliminate anti-patterns, verify logical flow and field compliance |

---

### Step 1: Opening Clarity (Title/Heading + First Section)

**Goal:** Ensure the opening immediately tells readers what this document is for and who should read it.

**Checks:**

- [ ] **Title/heading states clear purpose** (not a bland label)
  - For guides: "How to X" or "X Guide" (concrete)
  - For references: "X API Reference" or "X Configuration" (specific)
  - For explanations: "Why/How X works" (action or insight)
- [ ] **Title avoids corporate cadence** ("unlock", "elevate", "drive", "synergize")
- [ ] **No vague labels** (title is not "Overview", "Introduction", "Getting Started" without context)
- [ ] **First paragraph states audience + scope** (who should read this? what will it cover?)
- [ ] **No fake urgency** ("last chance", "everyone is talking about", "critical update")
- [ ] **No mystery boxes** (title/opening does not withhold what the doc is about)

**Do/Don't Examples:**

- Do: "Installation Guide: Setting Up Python 3.11 on macOS"
- Don't: "Getting Started"
- Do: "Why do browsers cache HTTP responses? (And how to bypass it)"
- Don't: "HTTP Caching Fundamentals"
- Do: "This guide walks operators through configuring Prometheus for Kubernetes environments."
- Don't: "Prometheus is a monitoring tool."

**Action:** Rewrite title and opening paragraph until all checks pass. Stop here if the opening is broken — no amount of polishing later sections fixes a weak premise.

---

### Step 2: Voice Scrub (Active, Direct, No Fluff)

**Goal:** Remove hedges, passive constructions, teacher framing, and filler phrases.

**Banned Phrases (delete or rewrite these):**

| Banned Pattern | Example | Fix |
|----------------|---------|-----|
| Teacher framing | "You will learn...", "You will see..." | Delete opener; start with direct statement |
| Filler hedges | "One possibility is...", "It is important to note..." | Delete hedge; state directly |
| Vague intensifiers | "very", "really", "truly", "fundamentally" | Delete intensifier; use precise language |
| Passive piles | "It was determined that...", "It was found that..." | Use active subject + verb |
| Adverb stacks | "quite fundamentally", "very significantly" | Use single, precise adverb or none |
| AI rhetoric | "This changes how we understand...", "Classic experiments reveal..." | Delete metacommentary; state findings |

**Checks:**

- [ ] **Every paragraph uses active voice** (subjects perform actions; not "the result was determined")
- [ ] **Zero banned phrases from the table above**
- [ ] **No new hedges or intensifiers** introduced that were not in the original
- [ ] **No stacks of abstract nouns** where a concrete verb would do ("implementation" → "implement")

**Do/Don't Examples:**

- Do: "See where this model fits in your architecture."
- Don't: "You will see where this model fits in your architecture."
- Do: "Place cells track location." (direct statement)
- Don't: "One live possibility is that place cells track location." (hedged)
- Do: "The API returns a 401 status when authentication fails."
- Don't: "It was found that a 401 status is returned when authentication fails."

**Action:** Rewrite passive sentences to active. Delete condescending openers and hedges. Replace nominalizations with verbs.

---

### Step 3: Accessibility Pass (Technical Term Handling + Scanability)

**Goal:** Ensure the document is understandable without reading source materials or external links. Preserve all technical terms.

**Technical Term Rule:**

- Do NOT remove or rename technical terms (e.g., "hippocampal system", "API gateway", "load balancer", "CORS")
- Keep the exact term and add a gloss in parentheses on first use
- **Fail this step if any technical term from the original is missing or paraphrased away**

**Checks:**

- [ ] **Every technical term has a plain-language gloss in parentheses on first use** (or is common knowledge)
  - CORRECT: "CORS (Cross-Origin Resource Sharing — allows requests between different domains)"
  - PROHIBITED: "cross-domain requests" (term dropped)
- [ ] **All original technical terms are preserved exactly; none are missing or paraphrased away**
- [ ] **No jargon used without context** (first mention includes explanation)
- [ ] **Concrete examples replace abstract descriptions** ("the server rejects the request" not "rejection semantics are invoked")
- [ ] **Short paragraphs** (1-4 lines) for scanability; dense paragraphs broken into chunks
- [ ] **Lists and code blocks used** where appropriate instead of prose
- [ ] **Technical acronyms spelled out on first use** (REST (Representational State Transfer))

**Do/Don't Examples:**

- Do: "The API gateway (the service that routes external requests to internal services) validates..."
- Don't: "The request router validates..." (term gateway dropped)
- Do: "CORS (Cross-Origin Resource Sharing) restricts which domains can access the API."
- Don't: "Cross-domain restrictions apply." (term dropped)
- Do: Break: "Authentication uses OAuth 2.0 (an open standard for secure delegation). Here's how it works: [steps in list]"
- Don't: Block: "OAuth 2.0 is a standard that allows applications to request access on behalf of users using tokens, and it works by..."

**Action:** Add glosses in parentheses on first mention. Chunk dense paragraphs. Use bulleted lists or code blocks for procedural steps. NEVER delete technical terms.

---

### Step 4: Formatting Sweep (Punctuation + Emphasis Rules)

**Goal:** Enforce mechanical consistency rules.

**Checks:**

- [ ] **ZERO em dashes** (`—`). Replace with commas, semicolons, colons, or parentheses.
  - Do: "The API supports three methods: GET, POST, PUT."
  - Don't: "The API supports three methods — GET, POST, PUT."
- [ ] **Bold restraint** (~2-5 spans per section, not wall-to-wall)
  - Do: Highlight **key term** and **critical value** per major section
  - Don't: "The **API** **returns** a **201** **status** for **successful** **POST** **requests**"
- [ ] **Bold covers coherent ideas, not isolated words** — each bold span must be 2–5 words capturing a phrase a skimmer can read standalone
  - Do: "We use a **dispatcher pattern** so parameter validation lives in one place."
  - Don't: "We use a **dispatcher** so **parameter** **validation** lives in one **place**."
- [ ] **Every paragraph has at least one bold phrase** if it contains a key idea a skimmer needs to grasp
- [ ] **No decorative emoji** in main body text (section headings ok if signaling type)
- [ ] **Backticks used correctly** for code/variable names, not general emphasis
  - Do: Set the `api_key` variable in `.env`.
  - Don't: Use the `important` field. (should be bold or plain, not backticks)
- [ ] **Consistent heading capitalization** (Title Case or sentence case, not mixed)
- [ ] **Consistent link formatting** (markdown `[text](url)`, not HTML or bare URLs in body)

**Action:** Search for `—` and replace. Audit bold density. Remove decorative punctuation. Ensure code formatting consistency.

---

### Step 5: Structural Integrity (Anti-Patterns + Logical Flow)

**Goal:** Eliminate structural flaws and verify content flow.

**Banned Anti-Patterns:**

| Pattern | Fix |
|---------|-----|
| Negation-first | "This is not X; it is Y" → "This is Y" |
| Passive piles (second occurrence) | "It was determined that..." → Direct statement |
| New hedges introduced during revision | "One possibility is...", "Some argue..." → Delete |
| Contradictory statements | Same fact stated differently in different sections → Consolidate |
| Orphaned sections | Sections with no connection to overall flow → Reorder or remove |

**Checks:**

- [ ] **Zero negation-first constructions** ("It is not X, it is Y" → "It is Y")
  - Do: "This is a behavioral map." (direct)
  - Don't: "This is not an algorithm; it is a behavioral map." (negation-first)
- [ ] **Logical flow verified** (sections follow reader journey: setup → concept → steps → examples)
- [ ] **No contradictions** between sections
- [ ] **Cross-references functional** (if section refers to another, that section exists and is findable)
- [ ] **Opening and closing align** (doc opens with premise; closing reinforces or extends it, not contradicts)
- [ ] **Examples paired with explanations** (no orphaned code blocks without rationale)

**Action:** Rewrite negation-first sentences as direct statements. Reorder sections if flow is broken. Verify all references are present. Remove orphaned examples or add explanations.

---

## Execution Workflow (Read-Only Analysis First)

**CONSTRAINT:** DO NOT write changes to the file until user explicitly confirms all proposed revisions.

1. **Read the document** fully before starting.
2. **Run doc-cold-read** (internal reference only; skip if already performed):
   - Quick STRUCTURE assessment (headings, sections, format)
   - Infer INTENT (audience, purpose, tone)
   - Note any obvious gaps
   - This informs step context but is NOT part of the revision output
3. **Work through Steps 1-5 in order.** Do not jump ahead.
4. **For each step, output:**
   - **Violations list:** Quote exact phrases from original that violate the step's rules (not paraphrased)
   - If no violations: state "No violations found"
   - **Before/After table:** Numbered rows showing: Location | Before | After
   - **Status line:** "Pass" or "Fix Needed" per Pass/Fail Definitions
5. **Stop and wait for user confirmation.** Present the full analysis with all violations lists and Before/After tables, then ask:
   ```
   Apply all changes? Or specify which steps (e.g., 'apply Steps 1-3', 'apply only Step 2', 'revert Step 4')?
   ```
6. **Only after explicit confirmation**, apply selected changes to the file.

---

## Required Output Format (Analysis Phase)

**For each step, produce:**

1. **Step header** with number and name
2. **Violations list** (quoted exact phrases from original, or "No violations found")
3. **Before/After table** with four columns: `#` | `Location` | `Before` | `After`
4. **Status line** indicating Pass/Fix Needed

**Example:**

```
### Step 1: Opening Clarity

**Violations found:**

- "Configuration Best Practices" (title is bland label, no purpose stated)
- "This guide covers how to set up your system." (opening states action but not audience or scope)

| # | Location | Before | After |
|---|----------|--------|-------|
| 1 | Title | Configuration Best Practices | Configuring Your API Gateway for Production: A Step-by-Step Guide |
| 2 | First paragraph | This guide covers how to set up your system. | This guide walks platform engineers through configuring an API gateway for high-traffic production environments. You'll learn to set up rate limiting, caching, and failover routing. |

**Status:** Pass (Title now states clear purpose. Opening identifies audience and scope.)
```

**At the end of all 5 steps:**

1. **Summary header:** "## Revision Summary"
2. **Status overview:** List each step with Pass/Fix Needed
3. **User prompt:**
   ```
   Apply all changes? Or specify which steps 
   (e.g., 'apply Steps 1-3', 'apply only Step 2', 'revert Step 4', 'no changes')?
   ```
4. **Proposed revised document** (optional, for reference; do not write yet)

---

## Selective Application (After User Confirmation)

Only after the user explicitly responds:

- `"apply all"` or `"yes"` → Write all changes from all steps to the file
- `"apply Step 2 only"` → Write only Step 2's changes
- `"apply Steps 3-4"` → Write only those steps' changes
- `"revert Step 1"` → Skip Step 1's changes; apply all others
- `"no"` or `"cancel"` → Do not write any changes

---

## Constraint Enforcement

**CONSTRAINT:** Agent MUST produce analysis phase output (all 5 steps with violations lists and Before/After tables) BEFORE prompting user for confirmation.

**CONSTRAINT:** If a step shows "Fix Needed" (violations remain), agent MUST ask user whether to proceed: "Step X still has [N] violations. Apply this step anyway, or revert it?"

**CONSTRAINT:** Do NOT write changes until user explicitly confirms which steps to apply. Confirmation must include step numbers or "all".

Violation: STOP and re-present analysis output. Do NOT apply changes without explicit confirmation.
