# DSPy Pipeline Jobs — Reference

LOAD-WHEN: Adding evaluators, wiring criteria, implementing CLI preview, handling version selection fallbacks, or adopting this pattern in a new project.

---

## DSPy Evaluator Input Envelope

`DefaultChainedEvaluatorSignature()` fixes only the **outer** shape:

- `generator_input` — map from `XInput.ToMap()`
- `generator_output` — map from generator result

**Inner keys are per job.** Prompts in `{job}_modules.go` must name fields that Go actually passes. If a prompt references `transcript` but `ToMap()` omits it, the model cannot recover it.

**Preferred:** `runner.BuildEvaluationInputs(genInput.ToMap(), generatorOutput)` in every `Evaluate*` method.

---

## DSPy Criteria Alignment

Single source of truth for a job's criteria = **union of `CriterionIDs`** on its chained evaluator config.

Use that same set for:

1. `ChainedEvaluatorConfig.CriterionIDs`
2. Score prompt keys (`EvaluatorScorePromptBuilder`)
3. Human review criterion list (if applicable)

Do not add review-only criteria that no in-loop evaluator scores.

---

## DSPy Version Selection Fallback Order

When early-exit or guard logic needs an existing version:

1. Most recent `pending`
2. Most recent `approved`
3. Most recent any status

Return domain error only when no records exist. Never return `uuid.Nil` on success paths.

Use pipeline status **constants**, not string literals, where the codebase defines them.

---

## DSPy Anti-Fluff Criterion

`CriterionIDAntiFluffCompliance` — for user-facing prose jobs.

When adding:

1. Append to job's criterion slice.
2. Rebuild score prompt with updated IDs.
3. Mirror in `ChainedEvaluatorConfig.CriterionIDs`.
4. Mention in evaluator feedback prompt.
5. Align human review if present.

**Skip** for label-only / structural jobs unless strings are primary UX.

---

## DSPy Regenerate List Scope

Regenerate selectors should list entities that **already have versions** for that job, unless the command explicitly targets all roots.

---

## DSPy CLI Preview Pattern

After successful analyze/regenerate:

1. Print success message.
2. If not `MaxVersionsReached`, call `GetSelectedForDisplay`.
3. Print preview only when display string is non-empty.
4. `GetSelectedForDisplay` must error when there is nothing to show — not `("", nil)`.

---

## DSPy File Map (typical project layout)

| Concern | Path |
|---------|------|
| Job runner | `internal/dspy/runner/job_runner.go` |
| Chained evaluator | `internal/dspy/chained_evaluator.go` |
| Evaluator factory | `internal/dspy/factory/evaluator_factory.go` |
| Criteria | `internal/evaluation/criteria/` |
| Orchestration | `internal/orchestration/loop.go`, `strategy.go` |
| Regenerate helpers | `internal/regenerate/` |
| Refinement policy | `internal/refinement/` |

---

## DSPy Portable Adoption Checklist

To reuse this pattern in a new dspy-go project:

1. Copy the **concepts** (runner, typed input, client/modules split, chained eval, orchestration).
2. Implement or vendor a **custom XML parser + validation + retry** stack (or document stock `WithXMLOutput` limits).
3. Define your own `internal/pipelines/<name>/` layout mirroring the table in the pipeline-jobs skill.
4. Load skills from `.github/agents/skills/dspy-*/SKILL.md` for implementation guidance.
