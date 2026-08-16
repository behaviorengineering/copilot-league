---
name: dspy-pipeline-jobs
description: >-
  Generalized DSPy pipeline job pattern: JobRunner, per-job clients and modules,
  typed inputs, chained evaluators with criteria, consolidation, versioned tables,
  refinement loops, and per-item regeneration. Use when adding a pipeline or job,
  wiring evaluators, implementing generate-evaluate-refine flows, or aligning
  existing code to the client-module pattern.
user-invocable: false
---

# DSPy pipeline jobs

## When to Load

Load when adding a DSPy pipeline or job, wiring evaluators, implementing generate-evaluate-refine flows, or aligning existing code to the client-module pattern.

**Cited by:** `.github/agents/golang-coder.agent.md`

**Principle:** Each **job** is a generator with typed input, module definitions, client wrapper, evaluator chain, own versioned storage, and orchestrated refinement. Shared glue lives in `internal/dspy/runner` and `internal/orchestration`.

---

## Layout (per pipeline)

| Piece | Location |
|-------|----------|
| Runner | `internal/dspy/runner` — `JobRunner`, `Generate`, `EvaluateWorkflow` |
| Types | `internal/pipelines/<p>/clients/types.go` — `XInput` + `ToMap()` + `GetVersion()` |
| Client | `{job}_client.go` — holds `*runner.JobRunner` |
| Modules | `{job}_modules.go` — signatures, prompts, evaluator config only |
| Eval shared | `evaluation_shared.go` or `evaluation_modules.go` |
| Register | `register.go` — generators + evaluation workflows |
| DB | `internal/pipelines/<p>/database/` — **one table per job** |
| Service | `internal/pipelines/<p>/services/{job}/` — orchestration, persistence |

**Naming:** singular job name — `topic_client.go`, `TopicInput`, not `topics_*`.

---

## Add a job to an existing pipeline

1. `types.go` — `XInput` with `ToMap()` / `GetVersion()`.
2. `x_client.go` — `GenerateX` → `r.Generate`; `EvaluateX` → `BuildEvaluationInputs` + `r.EvaluateWorkflow`.
3. `x_modules.go` — generator config + `ChainedEvaluatorConfig` with `CriterionIDs`.
4. `constants.go` — job key, step names.
5. `register.go` — register generator and evaluation workflow.
6. Database — versioned table + `CreateVersionAndSupersedeOlder`.
7. Container — build client, inject into service.
8. Service — call client; persist to **this job's table only**.

---

## Evaluators (required per generator job)

**Flow:** chained evaluators (feedback analysis → score) → **consolidation**.

| Item | Notes |
|------|-------|
| Signature | `dspy.DefaultChainedEvaluatorSignature()` |
| Config | `dspy.ChainedEvaluatorConfig` with `CriterionIDs` |
| Factory | `CreateChainedEvaluatorsFromConfig` |
| Score prompt | Built from criterion IDs via `EvaluatorScorePromptBuilder` |
| Consolidator | `dspy.NewConsolidatorPromptBuilder().WithSuffix(...).Build()` |

**Rules:**

- Same `CriterionIDs` in config, score prompt, and human review for that job.
- Empty `feedback` fails validation → retry; no synthetic filler.
- Evaluator inner map keys must match what `ToMap()` and generator output provide.

**User-facing prose jobs:** include `CriterionIDAntiFluffCompliance` when copy is shown in CLI or downstream UX. Skip for pure structural extractors (timestamps, IDs).

---

## Refinement orchestration

**Do not** implement inline generate → evaluate → recurse in services.

| Loop type | When | API |
|-----------|------|-----|
| Single-entity | One output unit per version | `RunRefinementLoop` + `RefinementStrategy` |
| Per-item | Multiple items, one save at end | `RunPerItemRefinementLoop` or `RunPerItemRefinementLoopWithIndices` |

Implement `RefinementStrategy`: `LoadContext`, `GenerateAndEvaluate`, `SaveVersion`, `ContextID`.

**Regeneration:** explicit options type (`Force`, `Message`) where the pipeline defines it.

**Healing:** on score regression, attempt self-healing before stop (`maxHealingAttempts >= 1`).

### Per-item partial regeneration

1. Load selected version as baseline.
2. Seed unselected indices from baseline slice.
3. Run loop with subset indices only.
4. `SaveVersion` once with full merged slice.

---

## Structured output in jobs

- Apply `WithXMLFormatting` in module **Create\*** paths (see `.github/agents/skills/dspy-module-patterns/SKILL.md`).
- One XML tag per field; lists via `<item>`; no JSON blobs for new jobs.
- Client maps parsed `map[string]any` to typed structs — no second parse unless legacy.

---

## Checklist

- [ ] One versioned table per job
- [ ] `CreateVersionAndSupersedeOlder` on new versions
- [ ] Chained evaluator + criteria + registered workflow
- [ ] `BuildEvaluationInputs` in `Evaluate*`
- [ ] `RunRefinementLoop` / per-item variant — no inline recursion
- [ ] Early-exit returns concrete version ID, not `uuid.Nil`
- [ ] Structured output + parser tests for new list/map fields
- [ ] Rationale via shared helpers, not duplicated prose

---

## Additional resources

- Evaluator tables, anti-fluff, CLI preview rules: `.github/agents/references/dspy-pipeline-jobs.md`
- XML/parser: `.github/agents/skills/dspy-structured-xml-output/SKILL.md`
