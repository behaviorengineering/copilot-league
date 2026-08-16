---
name: dspy-structured-xml-output
description: >-
  Custom DSPy structured XML output: format/parse/validate pipeline, nested tags vs
  string fields, list/array/map fields, mandatory validation, phased output, and
  debugging empty fields. Use when adding or changing generator output fields,
  debugging mandatory field validation failures, bullet/list XML in signatures,
  aligning prompts with parser behavior, or deciding whether string/regex parsing
  is appropriate (usually it is not for runtime validation).
user-invocable: false
---

# DSPy structured XML output

## When to Load

Load when adding or changing generator output fields, debugging mandatory field validation failures, using bullet/list XML in signatures, aligning prompts with parser behavior, or deciding whether string/regex parsing is appropriate.

**Cited by:** `.github/agents/golang-coder.agent.md`

**Principle:** The LLM returns XML; a **custom parser** turns it into `map[string]any` before **validation** runs. If prompts and parser disagree, fields can look full in logs but parse as **empty** and fail validation.

**Portable pattern:** Projects adopting this approach replace or wrap stock dspy-go XML interceptors with the same **format → parse → validate → retry** chain. Stock dspy-go `WithXMLOutput` is a fallback reference only when custom interceptors are not used.

---

## Pipeline (always)

```
FormatInterceptor  →  LLM  →  ParseInterceptor  →  ValidationInterceptor  →  RetryModuleInterceptor  →  client/service
```

### Do

- Validate **map keys** from the signature via `ValidateMandatoryFields` or job-specific validators.
- Phase-aware jobs: filter **both** format instructions **and** parse signature with the same phase helper.
- Fix empty fields by aligning **prompt + XML template + parser + inputs**.

### Do not (runtime)

- `strings.Contains` on LLM output to decide if a field is present.
- Reading nested `response` maps or manual XML walking in services/CLI when interceptors are enabled.
- Regex on model prose as the **primary** extraction path.

### Narrow exceptions (document if you add more)

| Mechanism | When acceptable |
|-----------|-----------------|
| Raw recovery helper | **Fallback only** when parser dropped text inside nested tags under a plain string field; runs after parse, before validation. |
| Keyword filters on **evaluator feedback** text | Unstructured feedback; intentional, not field validation. |
| `strings.TrimSpace` on **already-parsed** values | Normal empty check, not parsing. |

---

## Parser mental model

| Situation | Typical result |
|-----------|----------------|
| **Plain string field** | Only **direct character data** under the field tag is captured. |
| **Nested child elements** under a plain string field | **Ignored** for that field (legacy dspy-go behavior). |
| **Array field** (`isArrayField` → true) | Repeated child elements → `[]interface{}`; some fields join to one string downstream. |
| **Map field** (`isMapField`) | Nested elements become keys/values. |

**Array detection:** Field description includes **"list of"** or **"array"**, or name matches array suffixes checked in `isArrayField`.

**Map detection:** Description contains **"map"** or **"dictionary"** — **not** "object".

---

## Mandatory field validation

- **Strings:** empty after `TrimSpace` → fails.
- **`[]interface{}`:** length `0` → fails.
- **Other non-nil values:** treated as present.

---

## Checklist: new or list-like output field

1. **Decide shape** — one string, list, or map; match what client and persistence expect.
2. **Align XML with parser** — nested tags require array/map treatment or explicit join logic in the parser.
3. **Update prompts** in `{job}_modules.go` — XML examples must match format instructions.
4. **Add parser tests** — table-driven tests for nested children, empty tags, whitespace.
5. **Wire interceptors** — structured output enabled on the module's `Predict` path.

---

## Debugging empty fields

1. Confirm **parsed** type: string vs `[]interface{}` vs missing key (`available fields: [...]` in error).
2. Inspect whether the model used **nested XML** inside a plain string field tag.
3. Check `isArrayField` / `isMapField` / special-case join logic in the parser.
4. Adjust parser (with tests) **or** tighten prompt to flat XML — keep both aligned.
5. Check logs for `raw_response_preview` on validation failure.

---

## Additional resources

- Parser field heuristics and phased composition: `.github/agents/references/dspy-xml-output.md`
- Module wiring: `.github/agents/skills/dspy-module-patterns/SKILL.md`
