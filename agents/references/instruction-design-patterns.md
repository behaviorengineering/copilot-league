# Instruction Design Patterns

Load when designing or reviewing any agent/skill instruction that must filter or evaluate
a set of candidates (files, components, diff hunks, rubric items) and apply a qualifying rule.

## Table of Contents
1. [Forced Intermediate State](#instruction-design--forced-intermediate-state)
2. [Why Prose Rules Fail](#instruction-design--why-prose-rules-fail)
3. [Gate Template Slots](#instruction-design--gate-template-slots)
4. [When Not to Use](#instruction-design--when-not-to-use)

---

## Instruction Design — Forced Intermediate State

### The Pattern

Force the model to declare intermediate state in a structured template for each candidate
BEFORE writing any output for that candidate. The conclusion follows from the declared
state — a conclusion that contradicts declared state is a visible self-contradiction, which
models are strongly trained to avoid.

**Minimum gate structure:**
```
Candidate: [item name]
[Gate condition]: YES — [quote evidence] / NO
Decision: [outcome A] | [outcome B] | [outcome C]
If [outcome A]: [consequence field 1]: [value]
               [consequence field 2]: [value]
```

**CORRECT:**
```markdown
**Step 2 — Candidate Evaluation:** For each component changed in the diff, complete this
gate in working memory before deciding its output slot:

Candidate: [component name]
Call site in diff: YES — [quote the exact removed/added lines from calling code] / NO
Decision: H3 (YES) | FOLD into primary body (context needed) | OMIT (NO)
If H3: (1) team no longer does: [one clause]
        (2) now does instead:   [one clause]

Work through every candidate. Only candidates with YES become H3s.
Do not write output for any candidate until its gate is complete.
```

**PROHIBITED:**
```markdown
# WRONG — prose rule without gate; model skips reasoning
**Step 2:** For each component, decide whether it gets an H3.
Only include caller-facing changes — do not include internal infrastructure.
```
Violation: violation is invisible in the model trace; model pattern-matches familiar output
shape and applies the rule loosely or not at all.

---

## Instruction Design — Why Prose Rules Fail

Three failure modes that prose rules produce, all of which the gate pattern prevents:

| Failure mode | What happens | Gate prevention |
|---|---|---|
| **Reasoning skip** | Model fills output shape directly, applies rule post-hoc | Gate forces reasoning before output |
| **List exhaustion** | Model checks explicit examples, creates H3 for anything not listed | Gate requires YES evidence, not absence of NO |
| **Invisible violation** | Model breaks rule with no detectable contradiction | Gate makes contradiction visible in trace |

**Rules:**
- MUST require evidence quotation for YES — not self-reported YES/NO
- MUST declare consequence fields in the gate before writing output
- MUST limit decisions to 3 outcomes maximum — more creates ambiguity

---

## Instruction Design — Gate Template Slots

Four required slots. All MUST be present for the pattern to function.

| Slot | Purpose | Constraint |
|---|---|---|
| `Candidate` | Item being evaluated | MUST name it explicitly — no batch evaluation |
| `Gate condition` | Binary YES/NO test | YES MUST require quoted evidence from source material |
| `Decision` | Allowed outcomes | 3 maximum; MUST be exhaustive for the domain |
| `Consequence fields` | Pre-declared output content | MUST be filled in the gate, NOT at write time |

### Gate Condition Design

**CORRECT — requires evidence:**
```
Call site in diff: YES — [quote exact removed/added lines from calling code] / NO
```

**PROHIBITED — self-reported:**
```
Caller-facing: YES / NO
```
Violation: model answers YES without checking; evidence requirement forces the lookup.

### Consequence Field Design

**CORRECT — pre-declared in gate:**
```
If H3: (1) team no longer does: [clause filled here before writing]
        (2) now does instead:   [clause filled here before writing]
```

**PROHIBITED — deferred to write time:**
```
If H3: write a sentence describing the decision.
```
Violation: model reverts to architectural description or API documentation at write time.

---

## Instruction Design — When Not to Use

| Situation | Alternative |
|---|---|
| Simple inclusion rule, no candidate iteration | MUST/NEVER constraint with CORRECT/PROHIBITED examples |
| Candidate set is small and fixed | Enumerate them explicitly in the instruction |
| Rule is structural (slot presence) not evaluative (which candidates qualify) | Structural checklist item |
| Output shape is always identical regardless of input | Template with fixed slots — no gate needed |

**Signal that the gate IS needed:** The instruction contains "for each X, decide Y" or
"only include X if condition Z" — any per-item decision with a qualifying rule.
