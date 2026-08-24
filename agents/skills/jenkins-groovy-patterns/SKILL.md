---
name: jenkins-groovy-patterns
description: 'Jenkins Groovy scripting constraints. Use when writing .groovy stage files, lib utilities, or any script {} block: @NonCPS annotation for Matcher/regex, CPS serialization issues, DSL step name collisions in return maps, static keyword prohibition in loaded scripts, IoC dependency injection pattern, inline sh extraction.'
user-invocable: false
---

# Jenkins Groovy Patterns

## When to Load

Load when writing or reviewing any `.groovy` file or `script {}` block in a Jenkinsfile.

**Cited by:** `.github/agents/jenkins-coder.agent.md`

## Core Constraints

**CONSTRAINT:** Inline `sh` commands in Jenkinsfiles MUST be extracted into named functions.

NEVER place multi-line or reusable `sh` commands directly in a stage body. Single-line one-off `sh` calls are permitted inline only when truly non-reusable and self-explanatory.

CORRECT:
```groovy
def buildImage(String tag) {
    sh "docker build -t ${tag} ."
}
stage('Build') {
    steps { script { buildImage(params.IMAGE_TAG) } }
}
```

PROHIBITED:
```groovy
stage('Build') {
    steps {
        script {
            sh """
                docker build -t ${params.IMAGE_TAG} .
                docker tag ${params.IMAGE_TAG} registry/${params.IMAGE_TAG}
            """
        }
    }
}
```

Enforcement: Any `sh` block exceeding one line or callable from multiple places MUST be extracted.

**CONSTRAINT:** NEVER use `static` in Jenkins loaded scripts.

`load`ed `.groovy` files have no class declaration — `static` causes a silent compilation failure (pipeline stops after checkout with no error).

CORRECT: `@groovy.transform.Field final List<String> MY_LIST = ['a', 'b']`
PROHIBITED: `static final List<String> MY_LIST = ['a', 'b']`  // silent load failure

**CONSTRAINT:** Every method using `=~`, `Matcher`, `.find()`, or `.group()` MUST have `@NonCPS`.

`Matcher` is not CPS-serializable. Using it in a plain CPS method corrupts the entire script's compiled class — ALL methods in the script fail with `NoSuchMethodError`, not just the regex method.

Rules:
- `@NonCPS` methods MUST be pure Groovy only — NO Jenkins steps (`sh`, `echo`, `withCredentials`, `node`, etc.)
- Use `.find()` + `.group(N)` for group capture — NOT `matcher[0][1]` (Matcher array indexing is also not CPS-serializable)
- `@NonCPS` methods may call other `@NonCPS` methods, but NOT CPS methods

CORRECT:
```groovy
@NonCPS
def _parseVersion(String tag) {
    def m = tag =~ /^(\d+\.\d+\.\d+)/
    if (m.find()) return m.group(1)   // ← .find() + .group(N) — correct inside @NonCPS
    return null
}
```

PROHIBITED:
```groovy
def _parseVersion(String tag) {   // ← missing @NonCPS → ALL methods in script fail
    def m = tag =~ /^(\d+\.\d+\.\d+)/
    return m[0][1]                 // ← Matcher array indexing also not CPS-serializable
}
```

Enforcement: Grep `*.groovy` files for `=~` — every enclosing method MUST have `@NonCPS`.

**CONSTRAINT:** Stage `return [...]` map keys MUST NOT match Jenkins Pipeline DSL step names.

CPS dispatches the call to Pipeline DSL instead of the script method → `NoSuchMethodError` or `IllegalArgumentException`.

Reserved names (NEVER use as map keys):
`build`, `error`, `notify`, `checkout`, `input`, `sh`, `echo`, `node`, `stage`, `parallel`, `timeout`, `retry`, `sleep`, `lock`, `stash`, `unstash`, `archiveArtifacts`, `junit`

CORRECT: `return [runBuild: this.&runBuild]`
PROHIBITED: `return [build: this.&build]`  // ← 'build' collides with Jenkins DSL → NoSuchMethodError

Enforcement: Check every `return [...]` map — compare keys against the list above.

**CONSTRAINT:** When a loaded-script call fails with `NoSuchMethodError` despite the method existing, wrap it in an executor closure to fix the CPS dispatch context.

Direct `module.method()` from `script {}` resolves in `WorkflowScript` CPS context — fails for certain method signatures. Wrapping inside `deps.executor.retryWithBackoff(deps.logger, 1, 0) { ... }` shifts to the executor's CPS context, resolving the dispatch.

> For full triage flow, safe patterns, refactoring playbook, and incident response template: load `.github/agents/references/jenkins-cps-dispatch.md`.

CORRECT:
```groovy
stage('Lint') {
    steps {
        script {
            def deps = loadDependencies()
            def module = load '.jenkins/stages/lint.groovy'
            deps.executor.retryWithBackoff(deps.logger, 1, 0) {
                module.runLint(deps.logger, deps.executor)
            }
        }
    }
}
```

PROHIBITED:
```groovy
stage('Lint') {
    steps {
        script {
            def deps = loadDependencies()
            def module = load '.jenkins/stages/lint.groovy'
            module.runLint(deps.logger, deps.executor)  // ← NoSuchMethodError from WorkflowScript context
        }
    }
}
```

**CONSTRAINT:** Stages MUST receive `logger` and `executor` via injection — NEVER load them internally.

The dispatcher loads dependencies once and injects into all stages (IoC pattern).

CORRECT (stage file — receives deps as parameters):
```groovy
def runBuild(logger, executor, String component, String buildNumber) {
    executor.withOperationLogging(logger, 'Build', component) {
        sh "bash ./.jenkins/scripts/build.sh ${component} ${buildNumber}"
        archiveArtifacts(artifacts: "dist/${component}/**", allowEmptyArchive: false)
    }
}
return [runBuild: this.&runBuild]
```

PROHIBITED (stage loads its own deps):
```groovy
def runBuild(String component) {
    def logger = load '.jenkins/lib/logger.groovy'  // ← NEVER — violates IoC
}
```

**CONSTRAINT:** Dispatcher loads dependencies once via a `loadDependencies()` helper and injects into all stages.

```groovy
// In Jenkinsfile
def loadDependencies() {
    return [
        logger:       load '.jenkins/lib/logger.groovy',
        executor:     load '.jenkins/lib/executor.groovy',
        dependencies: load '.jenkins/lib/dependencies.groovy'
    ]
}

stage('Build') {
    steps {
        script {
            def deps = loadDependencies()
            def module = load '.jenkins/stages/build.groovy'
            deps.executor.retryWithBackoff(deps.logger, 1, 0) {
                module.runBuild(deps.logger, deps.executor, env.COMPONENT_NAME, env.BUILD_NUMBER)
            }
        }
    }
}
```

**Library Content Rules:**
- Shared libraries MUST contain ONLY generic/reusable utilities
- Stage-specific logic MUST remain in individual stage files
- ALLOWED: `logger.info/warn/error/header()`, `executor.withOperationLogging()`, `executor.retry()`, `dependencies.imageExists()`
- PROHIBITED: Build, test, deploy, or security-scan logic in shared libraries

## Verification Checklist

- [ ] No multi-line/reusable `sh` blocks inline in stage body — extracted to named functions
- [ ] No `static` keyword in any `.groovy` file (use `@groovy.transform.Field` instead)
- [ ] All methods using `=~` have `@NonCPS`; use `.find()` + `.group(N)` not `matcher[0][1]`
- [ ] Stage `return [...]` keys checked against DSL reserved names — no collisions
- [ ] Loaded-script calls wrapped in executor closure when `NoSuchMethodError` occurs
- [ ] Stages receive `logger`, `executor` as parameters — do NOT call `load` internally
- [ ] Dispatcher has single `loadDependencies()` function injecting into all stages
- [ ] Shared library files contain only generic utilities (no stage-specific logic)
