# DSPy XML Output — Reference

LOAD-WHEN: Adding or changing generator output fields, debugging parser behavior, aligning prompts with interceptor chains, or implementing phased output patterns.

---

## Stock dspy-go vs custom parser

| Aspect | Stock dspy-go `WithXMLOutput` | Custom stack |
|--------|--------------------------------|------------------------|
| Wiring | `module.Predict.WithXMLOutput(config)` | `EnableStructuredOutput` on `ChainOfThought` |
| Parser | dspy-go interceptors package | Custom XML parser (project-local) |
| Validation | App-specific or strict XML config | Custom validation interceptor + retry |
| Raw passthrough | Varies by config | `enablePredictRawXMLPassthrough` for custom parse |

When porting: keep the **invariants** (top-level parsed fields, no nested `response` fallback); swap package paths for your parser and factory.

---

## DSPy Phased Output Pattern

When a job emits different fields per phase (e.g. `composition_phase`):

| Phase | Validated fields | XML rule |
|-------|------------------|----------|
| `skim` | `rationale`, `description`, `tldr` | Only these three tags |
| `warmth` | `phase_plan`, `fluff` + locked prior phase | No `going_deeper` |
| `depth` | `phase_plan`, `going_deeper` + locked prior phases | — |

**Rules:**

- Filter signature for **both** format and parse with the same phase helper.
- Only send **non-empty** locked fields in inputs; empty keys mean "not written yet."
- Do not duplicate `rationale` in static `Outputs` when ChainOfThought prepends it (breaks XML).

---

## DSPy List-in-XML, String-in-Domain Pattern

Pattern: field is a **list in XML**, **single string** (often newline-joined) in domain code.

1. Mark field as array in parser (`isArrayField` or explicit name).
2. Model emits `<field><item>a</item><item>b</item></field>`.
3. Parser collects items; flush step may **join** to one string.
4. Client uses `ExtractRequiredStringField` or equivalent.

---

## DSPy JSON-inside-XML (avoid for new work)

**Do not** instruct the model to put JSON inside a tag for new jobs.

**Legacy exception:** some jobs use one tag with a JSON array string + `json.Unmarshal` in the client until migrated to repeated `<item>`.

---

## DSPy Parser Test Assertions

- Assert **parsed map** keys and types.
- Assert phase field name constants, not fragile substrings of full prompts.
- Parser package: table-driven tests for nested children, empty tags, whitespace.

---

## DSPy File Map (typical project layout)

| Area | Path |
|------|------|
| XML parser | `internal/dspy/structured_output/xml/parser.go` |
| Interceptors | `internal/dspy/structured_output/interceptor.go` |
| Validation | `internal/dspy/validation/validation_interceptor.go` |
| Post composition | `internal/dspy/validation/post_generator_validation.go` |
| Factory wiring | `internal/dspy/factory/interceptor_setup.go` |
| Shared XML rules | `internal/dspy/signature_helpers.go` |
| Per-job prompts | `internal/pipelines/<pipeline>/clients/*_modules.go` |
