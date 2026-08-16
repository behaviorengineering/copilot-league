---
name: dspy-prompt-engineering
description: >-
  DSPy prompt engineering for Go: signature design, system instructions, field
  descriptions, rationale fields, bias mitigation, ChainOfThought guidance, and
  XML-aligned prompt examples. Use when writing or revising module prompts,
  generator/evaluator signatures, or optimizing instructions for structured output.
user-invocable: false
---

# DSPy prompt engineering

In dspy-go, **signatures** define structure; **instructions** define behavior. Field **descriptions** steer XML shape and parser behavior.

---

## Signature + instruction pattern

```go
signature := core.NewSignature(inputs, outputs).
    WithInstruction(`You are a specialized evaluator.
- Analyze content objectively
- State uncertainties explicitly`)
predict := modules.NewPredict(signature)
```

Order of influence: **persona (if any) → instruction → field descriptions → XML format rules** (added by `WithXMLFormatting` in constructors).

---

## Field descriptions drive parsing

| You want | Write in description |
|----------|----------------------|
| Scalar text | Plain description; model puts text directly in tag |
| List | Include **"list of"** or **"array"**; document `<item>` children in prompt examples |
| Key-value map | **"map"** or **"dictionary"** — never use **"object"** for maps |
| Rationale | Use shared helpers (`RationaleDescriptionWithContext`) — see below |

Descriptions must match XML examples in `{job}_modules.go`.

---

## Rationale field contract (generators)

1. **Objective recitation first:** `VOICE:`, `MUST:`, `ANTI_PATTERN:` (from persona/objectives).
2. **Then action-chain:** short bullets of what was done (cap ~5 lines unless job defines a longer structured plan).
3. **Plain text only** in rationale — no XML/JSON inside rationale content.
4. **Prose follows rationale** — fix drift in output fields, not by rewriting rationale to match weak prose.

Helpers: `RationaleDescriptionWithContext(taskFocus)`, `RationaleDescriptionWithExtra(taskFocus, extraConstraints)` for emit-order or length rules.

`GeneratorObjectiveRecitation` is appended automatically by `CreateGeneratorModule`.

**Evaluators** use `DefaultChainedEvaluatorSignature()` rationale rules; they do not get generator objective recitation.

---

## Bias mitigation (instruction-level)

Address in system instructions where relevant:

- **Confirmation bias** — require considering counterexamples.
- **Anchoring** — do not overweight first input field alone.
- **Availability** — weigh less salient but relevant context.
- **Semantic grounding** — ask model to flag low-confidence claims.

For evaluators: require explicit feedback when criteria are not met; empty feedback is a contract violation, not success.

---

## ChainOfThought generators

- Put task rules in **instruction**; put per-field format in **output descriptions** + XML examples.
- Do not duplicate output fields in instruction that ChainOfThought already exposes in the signature.
- For phased jobs, state which tags to emit **this phase only** (see structured-xml skill).

---

## Evaluator prompts (chained)

Standard envelope (`DefaultChainedEvaluatorSignature`):

- Inputs: `generator_input`, `generator_output` (maps — inner keys are job-specific).
- Outputs: `criterion_scores`, `feedback`, `rationale`.

**Score prompt:** built from criterion IDs via `EvaluatorScorePromptBuilder` — score keys must match `ChainedEvaluatorConfig.CriterionIDs`.

**Feedback prompt:** must align with same criteria; never encourage empty feedback when issues exist.

**Consolidator:** base prompt + pipeline suffix via `ConsolidatorPromptBuilder.WithSuffix(...)`.

---

## XML examples in prompts

- Show exact tag names matching signature output fields.
- For lists, show multiple `<item>` siblings under one parent field tag.
- For phased output, show only tags valid for that phase.
