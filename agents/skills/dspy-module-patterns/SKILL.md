---
name: dspy-module-patterns
description: >-
  dspy-go module patterns for native Go apps: signatures, Predict and ChainOfThought,
  custom structured output interceptors, retry, LLM configuration, and module testing
  with mocks. Use when creating modules, enabling XML structured output, wiring
  interceptors, or choosing module types (Predict, ChainOfThought, ReAct, Parallel).
user-invocable: false
---

# DSPy module patterns (dspy-go)

## When to Load

Load when creating dspy-go modules, enabling XML structured output, wiring interceptors, or choosing module types (Predict, ChainOfThought, ReAct, Parallel).

**Cited by:** `.github/agents/golang-coder.agent.md`

DSPy-Go runs **in-process** as a Go library. Modules are the only supported path to LLM calls.

---

## Core rules

1. **Always use modules** — `modules.NewPredict`, `NewChainOfThought`, etc. with a signature.
2. **Signatures define contracts** — input/output fields with descriptions; attach behavior via `.WithInstruction()`.
3. **Configure LLM** — `core.SetDefaultLLM(llm)` or `module.SetLLM(llm)`; API keys from config/env, never hardcoded.
4. **Structured output on Predict** — for `ChainOfThought`, configure the inner `module.Predict`.
5. Use `factory.InterceptorSetup.EnableStructuredOutput(cot)` instead of only stock `WithXMLOutput` when a custom parser is active.

---

## Signature sketch

```go
signature := core.NewSignature(
    []core.InputField{
        {Field: core.NewField("question", core.WithDescription("Question to answer"))},
    },
    []core.OutputField{
        {Field: core.NewField("answer", core.WithDescription("Concise answer"))},
    },
).WithInstruction("Answer accurately and briefly.")
module := modules.NewChainOfThought(signature)
```

---

## Module types (when to use)

| Module | Use for |
|--------|---------|
| **Predict** | Single-shot generation or classification |
| **ChainOfThought** | Generators needing step-by-step reasoning (most pipeline generators) |
| **ReAct** | Tool-using agents with a tool registry |
| **Refine** | Iterative quality improvement inside one module |
| **Parallel** | Batch independent items concurrently |

---

## Structured output wiring

```go
// After creating ChainOfThought and setting LLM:
interceptorSetup.EnableStructuredOutput(cot)
```

Interceptor chain (typical):

1. Format — inject XML instructions from signature
2. Parse — custom XML → `map[string]any`
3. Validate — mandatory fields
4. Retry — on validation failure (budget from `interceptors.RetryConfig`)

### Stock dspy-go alternative (portable default)

```go
xmlConfig := interceptors.DefaultXMLConfig()
cot.Predict.WithXMLOutput(xmlConfig)
```

Use when a project does **not** ship a custom parser. Still expect top-level fields after parse; do not add nested `response` fallbacks.

---

## Module creation conventions

Apply **`WithXMLFormatting`** inside **Create\*** functions, not at call sites:

| Module kind | Where |
|-------------|--------|
| Generators | `CreateGeneratorModule` |
| Chained evaluator | `CreateChainedEvaluatorModule` |
| Consolidator | `CreateDefaultConsolidatorModule` |

Generators also receive `SharedInstructions.GeneratorObjectiveRecitation` via `CreateGeneratorModule`.

---

## Interceptor semantics

- **Do not** inject synthetic text into outputs to pass mandatory validation.
- **Do** let validation fail so retry runs; after exhaustion, fail clearly.
- Empty evaluator `feedback` is invalid, not "all criteria met."

---

## Testing

- Mock LLMs and external APIs; assert **parsed maps** and typed structs, not substrings of raw prompts.
- Parser changes: add table-driven tests for new XML shapes.
