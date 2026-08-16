# Jenkins CPS Dispatch Patterns

Load when diagnosing `NoSuchMethodError` for project helper methods, or when writing loaded-script calls inside nested closure contexts (`script`, `dir`, `parallel`, `retry`, post blocks).

## Table of Contents
1. [Jenkins CPS Dispatch Failure Mode](#jenkins-cps-dispatch-failure-mode)
2. [Jenkins CPS Safe Patterns](#jenkins-cps-safe-patterns)
3. [Jenkins CPS Triage Procedure](#jenkins-cps-triage-procedure)
4. [Jenkins CPS Refactoring Playbook](#jenkins-cps-refactoring-playbook)
5. [Jenkins CPS Incident Response](#jenkins-cps-incident-response)
6. [Jenkins CPS Agent Rules](#jenkins-cps-agent-rules)

---

## Jenkins CPS Dispatch Failure Mode

### What CPS Dispatch Misrouting Is

A CPS dispatch failure is a method resolution context problem, not a missing plugin or missing file problem. The pipeline resolves a loaded-script helper name against the Workflow DSL step resolver instead of the loaded script object, producing `NoSuchMethodError` followed by a long list of available DSL steps and symbols.

**Rules:**
- NEVER diagnose as a missing plugin when `NoSuchMethodError` names a project helper method
- NEVER diagnose as a missing file when the helper is present in the repository and loaded
- ALWAYS treat `NoSuchMethodError` for a project helper name as CPS dispatch misrouting until proven otherwise

### High-Risk Closure Shapes

These shapes cause dispatch misrouting for loaded-script method calls:

```groovy
// RISKY — loaded helper called inside nested script/dir/retry
stage('Build') {
    steps {
        script {
            dir('.output') {
                retry(2) {
                    deps.executor.prepareOutputDir('dist')  // ← dispatch misrouted to DSL
                }
            }
        }
    }
}

// RISKY — loaded helper called from parallel Docker branch
parallel(
    build: {
        node('linux') {
            docker.image('myapp').inside {
                deps.executor.runBuild(...)  // ← dispatch misrouted to DSL
            }
        }
    }
)

// RISKY — loaded helper called from post block after inter-node transition
post {
    always {
        script {
            deps.notifier.notifyBitbucket(...)  // ← CPS context shifted at inter-node boundary
        }
    }
}
```

**Rules:**
- NEVER call loaded-script methods from inside `dir()`, nested `retry()`, `parallel` branches, or `post` blocks without verifying dispatch is stable
- ALWAYS prefer local WorkflowScript helpers or direct DSL + `sh` in these shapes

---

## Jenkins CPS Safe Patterns

### Local WorkflowScript Helpers

Define helpers at the top of the Jenkinsfile for file prep and artifact operations inside stage closures. Local helpers resolve in Jenkinsfile context and avoid loaded-script dispatch risk.

```groovy
// Define at top of Jenkinsfile — resolved in WorkflowScript context
def prepareOutputDir(String dir) {
    sh "mkdir -p '${dir}'"
}

def archiveOutput(String pattern, Boolean allowEmpty = false) {
    sh "bash ./.jenkins/scripts/prep-archive-files.sh '${pattern}' || true"
    archiveArtifacts artifacts: pattern, allowEmptyArchive: allowEmpty, fingerprint: false
}

// Usage inside nested closure — safe
stage('Build') {
    steps {
        script {
            dir('.output') {
                prepareOutputDir('dist')      // ← local helper, no dispatch risk
                sh "bash ./.jenkins/scripts/build.sh"
                archiveOutput('dist/**/*.whl')
            }
        }
    }
}
```

**Rules:**
- MUST use local WorkflowScript helpers for file prep and artifact operations inside nested closures
- MUST keep local helpers small and purpose-specific
- NEVER use local helpers to wrap loaded-script calls — that adds closure depth without fixing dispatch

### Shell-First Business Logic

```groovy
// Business logic lives in versioned scripts, called via sh
stage('Test') {
    steps {
        script {
            sh "bash ./.jenkins/scripts/run-tests.sh ${params.MODULE}"
            junit 'reports/**/*.xml'
        }
    }
}
```

**Rules:**
- MUST execute build/test/security logic through versioned `sh` scripts, not loaded Groovy helpers
- NEVER move orchestration DSL steps (`junit`, `archiveArtifacts`, `retry`, `stage`) into shell scripts
- Jenkinsfile MUST remain orchestration-only; scripts carry domain behavior

### Safe Decision Rule

```groovy
// Decision flow for any new helper call:
// 1. Can it be expressed with Jenkins DSL + sh? → Keep local in Jenkinsfile
// 2. Is it complex domain logic? → Move to bash/Python script, call via sh
// 3. Is it a loaded Groovy method? → Call only in low-risk context with proven stable dispatch
```

**Rules:**
- ALWAYS apply this decision order before introducing any new helper call inside a stage closure
- NEVER add loaded-script calls in nested closure shapes without verifying dispatch stability first

### Non-Fatal Post Notifications

```groovy
post {
    always {
        script {
            try {
                deps.notifier.notifyBitbucket(currentBuild.result)
            } catch (Exception e) {
                echo "WARNING: Notification failed — ${e.message}"
            }
        }
    }
}
```

**Rules:**
- MUST guard post-action notification calls with try/catch
- NEVER let notification failures overwrite primary build result unless policy explicitly requires hard-fail
- ALWAYS log the failure as a warning so it remains searchable

PROHIBITED:
```groovy
// WRONG — notification failure masks build result
post {
    always {
        script {
            deps.notifier.notifyBitbucket(currentBuild.result)  // ← unguarded, can fail build
        }
    }
}
```

---

## Jenkins CPS Triage Procedure

### Fast Triage Flow

```
1. Find the FIRST NoSuchMethodError in time order — not the last
2. Capture: method name + WorkflowScript:<line> from stack trace
3. Open that line in the Jenkinsfile
4. Check: is the call targeting a loaded script/helper?
5. Check: is the call inside nested closures (script, dir, parallel, retry, post)?
6. If YES to both → CPS dispatch misrouting confirmed
```

### Signals That Confirm This Diagnosis

- Stage work executes successfully before failing at a helper method boundary
- The same helper name works in one stage but fails in another
- Retrying does not change the error shape
- Error message lists Jenkins DSL steps and symbols after the method name

### False Leads to Ignore

- Plugin installation issues (unless a true Jenkins step is missing)
- Missing files in the repository (when the helper is present and loaded)
- Test/lint tool failures that occur after the first CPS dispatch error (these are cascades, not causes)

**Rules:**
- ALWAYS identify the first `NoSuchMethodError` in time order — downstream cascades are not the cause
- NEVER conflate downstream failures with the first causal failure
- NEVER recommend `retry` as the primary fix for deterministic method-resolution errors — retry fixes transient errors, not dispatch misrouting

---

## Jenkins CPS Refactoring Playbook

### Iterative First-Failure Patching

```
1. Capture first failing method name + WorkflowScript:<line>
2. Open the line and classify the call:
   - local DSL/step call
   - loaded Groovy helper call  ← this is the failure type
   - shell/script call
3. Replace the loaded helper call with:
   - local Jenkinsfile helper (def prepareOutputDir(...))
   - direct DSL + sh sequence inline
4. Replay and wait for the next first failure
5. Repeat until all failing call paths are converted
```

**Rules:**
- MUST refactor by surface area (first-failure call boundary), NOT by stage name
- NEVER batch speculative rewrites — patch the first remaining failing call each replay
- MUST preserve behavior parity during refactoring:
  - preserve `retry` counts and timeout boundaries
  - preserve `junit` publication and unstable semantics
  - preserve artifact naming and archive patterns
- MUST consolidate local helpers only AFTER stabilization — get green first, deduplicate second

PROHIBITED:
```groovy
// WRONG — batch rewrite of all stages before confirming dispatch paths
// Failures move between call boundaries during replay; broad rewrites
// introduce regressions before the root path is confirmed.
```

---

## Jenkins CPS Incident Response

### Incident Report Template

```text
Incident: Jenkins CPS dispatch misrouting

Pipeline run:
- Job/build: <job-name> #<build-number>
- Branch/ref: <branch-or-pr>
- Jenkinsfile revision: <commit>
- Submodule revision (if used): <commit>

First failing error:
- Method: <missing-method-name>
- Location: WorkflowScript:<line>
- Message excerpt: No such DSL method '<method>' found among steps [...]

Context at failure:
- Stage: <stage-name>
- Closure shape: <script/dir/parallel/retry/post>
- Call type: <loaded-helper/local-helper/sh>

Patch applied:
- Commit: <commit>
- Change summary: <what was replaced and with what>

Replay outcome:
- Result: <passed/failed>
- Next first failure (if failed): <method + WorkflowScript line>
- Notes: <any non-fatal warnings>
```

### Minimum Evidence to Record

1. First failing method before patch (`method + WorkflowScript line`)
2. Commit that addressed it
3. First replay result after patch
4. Next first failure (or confirmation of green run)

### Escalation Rule

If three sequential first-failure patches do not reduce or move the failure signature, pause and run a broader architecture review before further tactical edits.

### Closure Rule

Close incident only when first-failure signature is eliminated and no new helper-name `NoSuchMethodError` appears in replay.

---

## Jenkins CPS Agent Rules

### Default Operating Rules

```
1. NoSuchMethodError naming a project helper → assume CPS dispatch misrouting first
2. Locate and patch the first failing call path in time order; do not batch speculative rewrites
3. Prefer local WorkflowScript helpers + Jenkins DSL for stage-local file and archive tasks
4. Prefer sh execution of versioned scripts for build/test/security logic
5. Avoid new loaded-script helper calls inside nested closure contexts
6. Keep post-notification paths warning-only unless policy explicitly requires hard-fail
```

### Required Response Behavior During Incidents

```
- Include failing method name + WorkflowScript:<line> in diagnosis
- State whether trace may come from stale submodule/branch revision
- Propose smallest safe patch that preserves stage semantics
- Request replay; ask for next first failure only
```

**Rules:**
- NEVER recommend `retry` as the primary fix for deterministic method-resolution errors
- NEVER assume helper method existence in source guarantees runtime resolvability under CPS
- NEVER conflate downstream failures with the first causal failure
- ALWAYS state the failing method name and WorkflowScript line in any diagnosis response
