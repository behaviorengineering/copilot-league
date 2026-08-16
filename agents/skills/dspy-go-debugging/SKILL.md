---
name: dspy-go-debugging
description: >-
  Debug dspy-go structured output failures: empty mandatory fields, validation vs
  parse mismatches, retry exhaustion, interceptor wiring, and execution tracing.
  Use when module runs fail validation, fields appear in raw logs but not in parsed
  output, or refinement loops stop unexpectedly.
user-invocable: false
---

# DSPy-Go debugging

Use this skill when a module **fails validation**, returns **unexpected nil fields**, or a **refinement loop** exits early.

---

## Decision tree

```
Error mentions "empty fields" or mandatory validation?
├─ Yes → Go to §1 Empty field (parse vs prompt)
└─ No → Error from LLM / timeout / retry exhausted?
    ├─ Retry exhausted after validation → §1 then §3 Retry
    ├─ LLM / API error → §4 LLM layer
    └─ Refinement / orchestration → §5 Orchestration
```

---

## 1. Empty mandatory field

**Symptom:** `empty fields: [field_name]` but raw trace shows content.

**Steps:**

1. List `available fields` from the error — is the key missing or present with empty value?
2. If key missing: signature field name ≠ XML tag name, or phase filter removed the field.
3. If key present, empty string: model sent empty tags or whitespace only.
4. If raw XML shows nested children inside a **plain string** field: parser ignored nested tags → fix `isArrayField` / prompt flat text / parser special-case.
5. Check `raw_response_preview` in validation logs.
6. Run or add a parser unit test with the failing XML snippet.

**Do not** fix by `strings.Contains` on raw output or reading `outputs["response"]`.

---

## 2. Interceptor wiring

Confirm the module path uses structured output:

- `ChainOfThought` → `EnableStructuredOutput` (or equivalent) on **inner Predict**.
- Factory `Setup*` methods called for evaluators/generators at registration.
- XML mode not partially enabled (stock + custom conflict).

**Quick check:** after `Process`, are output keys top-level field names or a single `response` string? Latter means interceptors not active.

---

## 3. Retry behavior

Validation failure should trigger `RetryModuleInterceptor` within configured budget.

- If retries fire but keep failing: prompt/parser mismatch, not transient LLM noise.
- If no retries: validation may be bypassed or error thrown before retry hook.
- After exhaustion: fail clearly — do not patch outputs with synthetic `feedback` or filler text.

---

## 4. LLM layer

- Verify API key, model ID, timeout on the provider config for this module.
- Check rate limits and token limits truncating XML mid-tag (often breaks parse).
- For long outputs: rationale or large fields **before** closing tags can truncate later siblings — reorder emit rules in prompt.

**Tracing:** `core.WithExecutionState(ctx)` and execution state steps for prompt/response per module id.

---

## 5. Orchestration / refinement

| Symptom | Likely cause |
|---------|----------------|
| `MaxVersionsReached` immediately | `ShouldSkipMaxVersions` / cap logic; check `Force` on regenerate |
| Score decreases, loop stops | Healing not configured or policy rejects |
| Per-item loop wrong length | `ItemCount` vs seed slice mismatch; re-sync indices in `LoadContext` |
| Partial regen overwrites all | Missing seed copy; must merge in `SaveVersion` |
| Nil version ID on success | Early-exit path returned `uuid.Nil` — use selection fallback helper |

---

## 6. Evaluator-specific

- Empty `feedback` → validation error (intentional).
- Consolidated feedback missing criterion → evaluator did not score that ID; check `CriterionIDs` alignment.
- Generator `previous_feedback` polluted → trace synthetic feedback injection (should not exist).

---

## 7. Minimal reproduction

1. Isolate XML snippet from `raw_response_preview`.
2. Write a parser unit test with that exact snippet.
3. Confirm whether the parser produces the expected map key/value.
4. Fix parser (add test) or fix prompt — never both without confirming which was wrong.

---

## Additional resources

- Module wiring: `agents/skills/dspy-module-patterns/SKILL.md`
- Job/evaluator alignment: `agents/skills/dspy-pipeline-jobs/SKILL.md`
