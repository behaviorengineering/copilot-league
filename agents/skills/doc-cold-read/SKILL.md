---
name: doc-cold-read
description: 'Rapid assessment technique for understanding unfamiliar documentation without prior context. Use when doc agents encounter unknown docs: scan structure, identify tone/audience, assess gaps, classify work needed.'
user-invocable: false
---

# Documentation Cold Read

## When to Load

Load when DOC-ARCHITECT or DOC-EDITOR encounter unfamiliar documentation and need to quickly assess its structure, intent, and gaps before deciding what work is required.

## Core Constraints

**CONSTRAINT:** A cold read MUST complete in 4 discrete phases — READ-STRUCTURE, IDENTIFY-INTENT, ASSESS-GAPS, CLASSIFY-WORK. Do NOT blend phases or omit any.

**CONSTRAINT:** Each phase MUST produce a specific, machine-verifiable output before proceeding to the next.

---

## Phase 1: READ-STRUCTURE (Scan Physical Layout)

**Goal:** Extract the document's hierarchical shape in 60 seconds.

**Process:**

1. Read the first 500 characters (title + opening paragraph)
2. Scan all headings (H1 → H6) — capture level and text
3. Check for table of contents or navigation aids
4. Note file metadata: length, format (Markdown/AsciiDoc/RST), images/diagrams present
5. Identify the document's "sections" (logical groupings between headings)

**Output Template:**

```
STRUCTURE ASSESSMENT:
- Title: [exact title]
- Length: [word count or byte range]
- Format: [Markdown / AsciiDoc / RST / Other]
- Heading hierarchy: [list as tree, e.g. "H1 > H2 > H3 > H3 > H2 > H2"]
- Sections: [number of major logical groups]
- Visual aids: [present/absent; if present, count and describe type]
- TOC: [present/absent]
```

**Rules:**
- MUST extract hierarchy, not read content details
- MUST capture ALL top-level headings to understand document extent
- If TOC present, MUST note whether it matches actual structure
- NEVER spend >90 seconds on this phase

---

## Phase 2: IDENTIFY-INTENT (Determine Audience + Purpose)

**Goal:** Infer what the document is FOR and who it's FOR in 90 seconds.

**Process:**

1. Read the opening 200–300 words (abstract, intro, or first section)
2. Look for explicit signals:
   - Audience signal: "This guide is for [role/persona]" or implied by terminology
   - Purpose signal: "This document explains...", "How to...", "Reference for..."
3. Infer tone: Is it instructional, reference, explanatory, or procedural?
4. Check closing: Does the final section summarize, list next steps, or point elsewhere?
5. Identify gaps in the opening: Does it say what prerequisites are needed?

**Output Template:**

```
INTENT ASSESSMENT:
- Primary audience: [role(s) the doc targets: developer/operator/end-user/maintainer]
- Purpose: [one phrase: "how-to guide", "API reference", "architecture overview", "troubleshooting manual", etc.]
- Tone: [instructional / reference / explanatory / procedural / narrative]
- Implicit prerequisite knowledge: [what reader is assumed to know]
- Opening clarity: [does first 300 words clearly state purpose? YES/NO]
- Scope statement: [does doc define its boundaries? YES/NO — what is IN scope, what is OUT]
```

**Rules:**
- MUST NOT read the entire document to infer intent
- MUST identify audience from terminology and examples, not guesswork
- MUST distinguish between "what this doc teaches" vs "what this doc is for"
- Implicit prerequisite = knowledge NOT stated but assumed (e.g., "assumes you know Docker")

---

## Phase 3: ASSESS-GAPS (Identify Missing Pieces)

**Goal:** Spot structural and content omissions in 120 seconds.

**Process:**

1. Against the purpose identified in Phase 2, ask: "What would a reader need to understand this doc?"
2. Scan the body (read section headings + first sentence of each section)
3. Note what's MISSING:
   - Prerequisite section (setup, installation, environment)?
   - Quick-start or hello-world example?
   - Conceptual explanation before procedural steps?
   - Error handling or troubleshooting section?
   - Links to related docs?
   - Versioning or currency statement (when was this written)?
4. Note what's PRESENT but under-explained:
   - Jargon without definition?
   - Complex steps without rationale?
   - Examples but no explanation?
5. Check for STRUCTURAL gaps:
   - Does flow match reader journey? (e.g., setup → basic usage → advanced usage)
   - Are related topics scattered or grouped?
   - Is navigation clear (TOC, cross-links, next/previous)?

**Output Template:**

```
GAP ASSESSMENT:
- Critical missing sections: [list, or "none"]
- Under-explained: [topics with examples but no rationale; jargon without definition]
- Structural issues: [flow problems, poor grouping, unclear navigation]
- Metadata gaps: [currency, versioning, audience, scope statement missing]
- Examples present? [YES/NO — if yes, tied to explanation? YES/NO]
- Reader journey clarity: [do sections follow logical order? YES/NO]
```

**Rules:**
- MUST NOT attempt to fix gaps — only identify them
- MUST distinguish between "missing section" vs "section exists but is thin"
- MUST evaluate gaps AGAINST the stated purpose (Phase 2)

---

## Phase 4: CLASSIFY-WORK (Decide What's Needed)

**Goal:** Determine what type of work to perform on this doc.

**Process:**

Read all outputs from Phases 1–3. Ask these questions in order:

```
Q1: Are critical structural or intent errors present?
    (e.g., doc says it's a reference but reads as a tutorial;
     heading hierarchy is broken; audience is unclear)
    
    YES → RESTRUCTURE required
    NO  → Q2

Q2: Are significant content gaps blocking reader understanding?
    (e.g., no prerequisite section; critical steps missing;
     no examples for procedural sections)
    
    YES → EXPAND required
    NO  → Q3

Q3: Is tone inconsistent, jargon undefined, or explanations vague?
    (e.g., shifts between procedural and reference mid-doc;
     technical terms used without definition;
     steps lack rationale)
    
    YES → REFINE required (edit tone, define terms, add rationale)
    NO  → Q4

Q4: Is the doc complete and clear but could benefit from polish?
    (e.g., TOC formatting, cross-link additions, minor rewording)
    
    YES → POLISH required (minor edits)
    NO  → COMPLETE (no work needed; inform user)
```

**Output Template:**

```
WORK CLASSIFICATION:
- Classification: [RESTRUCTURE / EXPAND / REFINE / POLISH / COMPLETE]
- Justification: [which question(s) led to this classification]
- Specific work items: [3–5 concrete tasks to perform, in priority order]
- Estimated complexity: [LOW / MEDIUM / HIGH]
- Risk: [rewrite scope affects X sections; might break Y external links; etc.]
```

**Rules:**
- MUST evaluate in order (Q1 → Q2 → Q3 → Q4)
- MUST stop at first YES and classify based on that
- Specific work items MUST be concrete actions, not vague goals
- MUST assess risk of structural changes (e.g., if reorganizing, what breaks?)

---

## Decision Tree (Complete Example)

```
EXAMPLE INPUT: Unknown technical reference for a cloud deployment tool

PHASE 1 — STRUCTURE:
  Title: "Acme Cloud Deployer — API Reference"
  Length: 8,500 words
  Format: Markdown
  Hierarchy: H1 > H2 (Endpoints) > H3 (4x GET, 3x POST) > H4 (parameters, examples)
  Sections: 6 (Overview, Authentication, Endpoints [grouped by resource], Error Codes, Rate Limits)
  Visual aids: No diagrams; code blocks present (JSON examples)
  TOC: Yes, matches structure

PHASE 2 — INTENT:
  Audience: Backend developers integrating with Acme Cloud API
  Purpose: API reference (method signatures, parameters, response formats)
  Tone: Reference (terse, example-driven)
  Prerequisites: Assumes developer knows REST, HTTP status codes, JSON
  Opening clarity: YES ("This reference documents all REST endpoints for Acme Cloud Deployer v3.0")
  Scope: IN: endpoint contracts; OUT: implementation patterns, SDK usage

PHASE 3 — GAPS:
  Critical missing: "Quick Start" section (how to make first API call?); no authentication setup examples
  Under-explained: Rate limit headers explained but no retry strategy provided
  Structural: Authentication section buried in middle; should precede endpoints
  Metadata: No version history; "Last updated: [date]" missing
  Examples present? YES; tied to explanation? Partially (request shown, response shown, but rationale missing)
  Reader journey: Unclear — is this reference-first or tutorial-first?

PHASE 4 — CLASSIFY:
  Q1: Structural error? YES — auth should precede endpoints
  → Classification: RESTRUCTURE
  Specific work: (1) Move auth section before endpoints; (2) Add quick-start example; (3) Add version history; (4) Clarify scope boundary
  Complexity: MEDIUM
  Risk: Moving auth section may break deep links (e.g., docs.site#authentication → docs.site#authentication-v3)
```

---

## Output Checklist (Completeness Verification)

- [ ] **Phase 1 output:** Document structure (title, hierarchy, sections, TOC status)
      Method: Template filled; heading tree captured
      Pass: All fields populated
      Fail: Missing hierarchy or section count

- [ ] **Phase 2 output:** Audience, purpose, tone, prerequisites, scope
      Method: Template filled; audience/purpose stated in plain language
      Pass: Audience identifiable; purpose stated in one phrase
      Fail: Audience vague ("technical users"); purpose unclear

- [ ] **Phase 3 output:** Gaps and structural issues identified
      Method: Template filled; gaps listed as specific sections or omissions, not vague complaints
      Pass: 3+ concrete gaps identified OR "none" with justification
      Fail: "Needs more detail" (vague); "could be better organized" (not specific)

- [ ] **Phase 4 output:** Work classification with justification and specific tasks
      Method: Classification matches decision tree logic; work items are concrete actions
      Pass: Classification clear; 3–5 actionable tasks listed
      Fail: Classification vague; work items are generic ("improve doc", "make it better")

---

## Rules for Doc Agents Using This Skill

**CONSTRAINT:** DOC-ARCHITECT MUST execute all four phases before deciding to restructure or create a new outline.

**CONSTRAINT:** DOC-EDITOR MUST NOT attempt refinement (Phase 4 → REFINE) without completing a cold read first.

**CONSTRAINT:** If a cold read outputs POLISH or COMPLETE, DOC-EDITOR MAY skip this skill and proceed directly with minor edits or inform user no work is needed.

**CONSTRAINT:** If RESTRUCTURE or EXPAND is classified, DOC-ARCHITECT takes the lead; DOC-EDITOR does NOT attempt these unilaterally.
