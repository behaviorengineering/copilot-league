# Neurodivergent Formatting Patterns

Load when writing, editing, or structuring any documentation section — apply these rules to every paragraph, list, and heading produced.

## Table of Contents
1. [Neurodivergent Bold and Emphasis](#neurodivergent-bold-and-emphasis)
2. [Neurodivergent Paragraph Length](#neurodivergent-paragraph-length)
3. [Neurodivergent Sentence Structure](#neurodivergent-sentence-structure)
4. [Neurodivergent List Formatting](#neurodivergent-list-formatting)
5. [Neurodivergent Visual Breaks](#neurodivergent-visual-breaks)
6. [Neurodivergent Heading Scannability](#neurodivergent-heading-scannability)

---

## Neurodivergent Bold and Emphasis

### Bold for Key Terms

**Rules:**
- MUST bold the first occurrence of a key term, concept, or named component in a section
- MUST bold decision outcomes and critical constraints inline (e.g. **never**, **always**, **required**)
- NEVER bold decoratively — every bold instance must mark something a skimmer needs to see
- MUST bold coherent idea phrases (2–5 words), not isolated single words — the bold span should be the phrase a skimmer needs to read to understand the concept
- NEVER bold entire sentences or more than 5 consecutive words

PROHIBITED:
```markdown
<!-- WRONG — entire phrase bolded, no signal value -->
**We use GitOps because Jenkins should never access Kubernetes directly.**

<!-- WRONG — nothing bolded, key term buried -->
We use a dispatcher pattern. The dispatcher is the only pipeline that takes parameters.
```

CORRECT:
```markdown
We use **GitOps**: Jenkins updates manifests, ArgoCD handles deployment.

We use a **dispatcher pattern**. The dispatcher is the only pipeline that takes parameters.
```

---

### Italics for Technical Terms and Filenames

**Rules:**
- MUST italicise filenames, paths, and config keys on first mention in a section: *Jenkinsfile*, *config.yaml*, *pipeline.groovy*
- MUST italicise technical terms being defined or distinguished: *orchestration* vs *execution*
- NEVER italicise for decoration — italics signal "this is a specific technical thing"
- NEVER mix bold and italics on the same word unless both signals apply independently

---

## Neurodivergent Paragraph Length

### One Idea Per Paragraph

**Rules:**
- MUST limit each paragraph to one main idea
- MUST keep paragraphs to 1–3 sentences maximum
- NEVER write a paragraph longer than 4 lines of rendered text
- When a paragraph reaches 4+ sentences, split at the first natural topic boundary

PROHIBITED:
```markdown
<!-- WRONG — two ideas, wall of text -->
We use a dispatcher pattern where all pipeline invocations go through a single entry point.
This entry point validates parameters, resolves the target component, and delegates to the
component pipeline. Component pipelines are not directly invocable by users. This separation
means parameter validation logic lives in one place. When a new parameter is added, only the
dispatcher needs updating.
```

CORRECT:
```markdown
We use a **dispatcher pattern**: all invocations go through a single entry point that validates
parameters and delegates to the target component pipeline.

Component pipelines are not directly invocable by users. Parameter validation lives in one place —
adding a new parameter only requires updating the dispatcher.
```

---

## Neurodivergent Sentence Structure

### Short Sentences, Active Subject

**Rules:**
- MUST prefer sentences under 20 words; split at conjunctions when a sentence exceeds 25 words
- MUST place the subject and verb within the first 8 words of a sentence
- NEVER stack more than two subordinate clauses in one sentence
- NEVER open a sentence with a long prepositional phrase before the subject

PROHIBITED:
```markdown
<!-- WRONG — subject buried, clause stack -->
Because Jenkins needs to remain stateless and because cluster access requires credentials
that are difficult to rotate, we decided to adopt GitOps.
```

CORRECT:
```markdown
We adopted **GitOps** to keep Jenkins stateless. Cluster credentials are difficult to rotate,
so Jenkins never accesses Kubernetes directly.
```

---

## Neurodivergent List Formatting

### Parallel Structure in Lists

**Rules:**
- MUST start every bullet in a list with the same grammatical form (all verbs, all nouns, all noun phrases)
- MUST keep bullet text under 15 words; move detail to a following sentence or sub-bullet
- NEVER mix sentence-ending punctuation inconsistently within one list
- NEVER nest bullets more than 2 levels deep

PROHIBITED:
```markdown
<!-- WRONG — mixed grammatical form, inconsistent length -->
- Validates input parameters before dispatching
- The component pipeline handles the actual work
- Logging at every stage so failures are traceable
- We never use Groovy for business logic
```

CORRECT:
```markdown
- Validates input parameters before dispatching
- Delegates to the target component pipeline
- Logs start time and completion status at every stage
- Keeps business logic in bash scripts, not Groovy
```

---

## Neurodivergent Visual Breaks

### Whitespace and Horizontal Rules

**Rules:**
- MUST add a blank line between every paragraph — NEVER run paragraphs together
- MUST separate distinct concept blocks with `---` when they appear under the same H2 and are not sequential steps
- NEVER place two code blocks back-to-back without a sentence of prose between them
- NEVER place a heading immediately after another heading with no content between them

PROHIBITED:
```markdown
<!-- WRONG — headings stacked, no separator between concept blocks -->
## Configuration

### Identity
```yaml
name: my-app
```
### Runtime
```yaml
timeout: 30
```
```

CORRECT:
```markdown
## Configuration

### Identity

```yaml
name: my-app
```

The *name* field is the unique identifier used across all pipeline references.

---

### Runtime

```yaml
timeout: 30
```

Set *timeout* to the maximum expected stage duration in seconds.
```

---

## Neurodivergent Heading Scannability

### Headings That Describe, Not Label

**Rules:**
- MUST write headings as noun phrases that describe content, not category labels
- MUST ensure a reader scanning only the headings can reconstruct the document's structure
- NEVER use single-word headings (e.g. "Overview", "Details", "Notes")
- NEVER repeat the parent heading word in a child heading

PROHIBITED:
```markdown
<!-- WRONG — single word, no signal -->
## Overview
## Details
## Notes
```

CORRECT:
```markdown
## What the Dispatcher Pattern Does
## How Component Pipelines Are Structured
## Known Constraints and Edge Cases
```
