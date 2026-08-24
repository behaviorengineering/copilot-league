# [Domain] Patterns

<!-- LOAD-WHEN trigger: one sentence telling agents exactly when to load this file.
     Be specific — vague triggers cause the file to be skipped.
     Examples:
       "Load when generating any Python model, service, client, or test file."
       "Load when generating any Jenkinsfile, stage groovy file, or pipeline script."
       "Load when generating any Dockerfile, pip install, or Artifactory authentication."
-->
Load when [specific condition — what task or file type requires these patterns].

## Table of Contents
<!-- List every H2 section. Use [domain]-prefixed headings throughout.
     Prefix ensures sections are scannable when multiple reference files are loaded. -->
1. [[Domain] Pattern Group 1](#[domain]-pattern-group-1)
2. [[Domain] Pattern Group 2](#[domain]-pattern-group-2)
3. [[Domain] Pattern Group 3](#[domain]-pattern-group-3)

---

## [Domain] Pattern Group 1

<!-- Section title: [Domain] + noun phrase describing the concern.
     Examples: "Python Models", "Jenkins Stage Patterns", "Artifactory Docker Registries"
     Keep groups cohesive — one concern per section. -->

### [Specific Pattern Name]

<!-- Pattern name: descriptive noun phrase, not a verb.
     Examples: "Standard field model", "List wrapper (RootModel)", "Registry existence check"
     Each ### is one independently usable pattern. -->

<!-- PURPOSE comment (optional, one line): what problem this pattern solves.
     Only include when the pattern name alone is ambiguous. -->

```[language]
<!-- CORRECT implementation — copy-paste ready, no placeholders unless unavoidable.
     Use realistic names from the project domain, not generic "Foo/Bar".
     Include imports. Show the complete minimal unit (class, function, block).
     If a placeholder is unavoidable, use angle-bracket notation: <registry-url> -->
```

**Rules:**
<!-- 2–5 machine-executable rules. Each rule is one sentence.
     Use MUST / NEVER / ALWAYS.
     Do NOT explain why — state only what to do or not do.
     Examples:
       - Return `model.model_dump(by_alias=True)` — never return the model directly
       - Call `response.raise_for_status()` before parsing
       - NEVER open a connection inside a repository -->
- [Rule 1]
- [Rule 2]

<!-- PROHIBITED block: include ONLY when the wrong approach is common or non-obvious.
     Skip if the correct pattern is self-evident. -->
PROHIBITED:
```[language]
# WRONG — [one-line reason]
[anti-pattern code]
```

---

## [Domain] Pattern Group 2

### [Specific Pattern Name]

```[language]
[correct implementation]
```

**Rules:**
- [Rule 1]
- [Rule 2]

---

## [Domain] Pattern Group 3

### [Specific Pattern Name]

```[language]
[correct implementation]
```

**Rules:**
- [Rule 1]

<!-- Add more ### patterns within this section as needed.
     Add more ## sections for distinct concerns. -->
