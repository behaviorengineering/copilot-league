---
name: jenkins-pipeline-structure
description: 'Jenkins pipeline structure constraints. Use when writing or reviewing Jenkinsfiles: declarative syntax, agent hierarchy, Docker-in-Docker prevention, agent+parallel compile error, timeout controls, SHOULD_PUSH logic, post block patterns (node label, unstable/aborted completeness, returnStatus, inter-node CPS serialization), Calculate Image Tags bootstrap.'
user-invocable: false
---

# Jenkins Pipeline Structure

## When to Load

Load when writing or reviewing any `*.Jenkinsfile` or `pipeline { }` block.

**Cited by:** `.github/agents/jenkins-coder.agent.md`

MUST load `.github/agents/references/environment.md` before emitting registry hosts or credential IDs. `UPSTREAM_*_IMAGE` defaults use `DOCKER_PULL_DOMAIN` from that overlay.

## Core Constraints

**CONSTRAINT:** All pipelines MUST use declarative syntax — NOT scripted.

- Pipeline block starts with `pipeline {`
- `script {}` blocks ONLY when declarative cannot express the logic
- Scripted pipeline syntax is PROHIBITED as primary structure

**CONSTRAINT:** Use `agent none` at pipeline level when ANY stage uses a Docker agent.

CRITICAL: Top-level agent + stage Docker agent = Docker-in-Docker failure. The stage tries to run Docker inside the container created by the top-level agent.

CORRECT:
```groovy
pipeline {
    agent none
    stages {
        stage('Build') {
            agent { docker { image env.CI_RUNTIME_IMAGE ... } }
            steps { sh 'bash ./.jenkins/scripts/build.sh' }
        }
    }
}
```

PROHIBITED:
```groovy
pipeline {
    agent { label 'linux-agent' }   // ← creates a container
    stages {
        stage('Build') {
            agent { docker { ... } }  // ← Docker inside container → FAIL
        }
    }
}
```

Exception: If ALL stages use the same non-Docker label agent, a top-level agent is permitted.

**CONSTRAINT:** A stage MUST NOT have both `agent` and `parallel` at the same level.

Jenkins declarative compile error: `"agent" is not allowed in stage "X" as it contains parallel or matrix stages`

When same-node parallel is required, use `script { parallel(...) }` inside `steps {}`.

CORRECT:
```groovy
stage('Build Images') {
    agent { label 'docker-host' }
    options { timeout(time: 30, unit: 'MINUTES') }
    steps {
        script {
            // NOTE: script { parallel(...) } — Jenkins forbids agent + declarative parallel.
            // Both closures run on the same allocated node.
            parallel(
                'Debian': { sh 'bash .jenkins/scripts/build.sh debian' },
                'RHEL':   { sh 'bash .jenkins/scripts/build.sh rhel' }
            )
        }
    }
}
```

PROHIBITED:
```groovy
stage('Build Images') {
    agent { label 'docker-host' }  // ← agent here
    parallel {                      // ← parallel here → COMPILE ERROR
        stage('Debian') { ... }
    }
}
```

Decision rule:
- Same node + clean UI → `script { parallel(...) }` (PREFERRED)
- Same node + sub-stage UI visibility needed → `stages > stage > parallel` (adds redundant middle stage)
- Different nodes acceptable → standard declarative `parallel` with per-stage agents

**CONSTRAINT:** Timeout controls MUST be explicit at pipeline level and on stages >5 min.

```groovy
pipeline {
    options { timeout(time: 1, unit: 'HOURS') }
    stages {
        stage('Build') {
            options { timeout(time: 15, unit: 'MINUTES') }
            steps { ... }
        }
    }
}
```

**CONSTRAINT:** When `copyArtifacts` is used, `options` MUST include both `disableConcurrentBuilds` and `copyArtifactPermission('*')`.

```groovy
options {
    timeout(time: 1, unit: 'HOURS')
    disableConcurrentBuilds(abortPrevious: true)  // prevents queue buildup on feature branches
    copyArtifactPermission('*')                   // REQUIRED: allows cross-stage artifact copying
}
```

Verification:
- `copyArtifacts` used AND `copyArtifactPermission('*')` present: PASS
- `copyArtifacts` without `copyArtifactPermission`: FAIL (runtime permission denied)

**CONSTRAINT:** Push-to-registry behavior MUST auto-detect from branch with parameter override.

```groovy
environment {
    SHOULD_PUSH = "${(env.BRANCH_NAME ==~ /(master|main|develop)/) ? 'true' : params.PUSH_TO_REGISTRY}"
}
```

Paired parameter:
```groovy
booleanParam(name: 'PUSH_TO_REGISTRY', defaultValue: false,
    description: 'Push images to registry (auto-determined by branch)')
```

Stage gate: `when { expression { env.SHOULD_PUSH == 'true' } }`

**CONSTRAINT:** Post blocks MUST use `node(label)` — NEVER Docker agents. MUST include all four states.

`failure {}` fires ONLY on FAILURE. When any stage uses `catchError(buildResult: 'UNSTABLE')`, test failures produce UNSTABLE — neither `success` nor `failure` fires → PR status spins permanently.
`aborted {}` handles manual cancellations — without it, cancelled builds also leave PR status spinning.
Bitbucket Build Status API has no UNSTABLE state — map UNSTABLE and ABORTED → Bitbucket `FAILED`.

CORRECT:
```groovy
post {
    success  { node(label) { script { notifyBitbucket('SUCCESSFUL', 'CI passed') } } }
    failure  { node(label) { script { notifyBitbucket('FAILED', 'CI failed') } } }
    unstable { node(label) { script { notifyBitbucket('FAILED', 'CI unstable — test failures') } } }
    aborted  { node(label) { script { notifyBitbucket('FAILED', 'CI aborted') } } }
}
```

PROHIBITED:
```groovy
post {
    success { ... }
    failure { ... }
    // ← Missing unstable/aborted — PR status spins on test failure or cancellation
}
```

**CONSTRAINT:** Non-fatal `sh` calls MUST use `returnStatus: true` — NEVER `try { sh ... } catch`.

Jenkins marks a `sh` step red the moment it exits non-zero, BEFORE `catch` runs. The stage visually appears failed even when the exception is suppressed.

CORRECT: `def rc = sh(script: 'docker run --rm ...', returnStatus: true)`
PROHIBITED: `try { sh 'docker run ...' } catch (Exception ignored) { }`

Enforcement: Search for `try {` wrapping a `sh` step — replace with `returnStatus: true`.

**CONSTRAINT:** Script-level variables DO NOT survive inter-node CPS serialization.

Each `post {}` `node()` block allocates a fresh node. Variables set in a prior stage or node are null.
Pattern: `checkout scm` → `load(configFile)` at the start of every `node()` block that needs config.

CORRECT:
```groovy
post {
    success {
        node(label) {
            script {
                checkout scm
                def cfg = load(fileExists('.jenkins-config.groovy') ? '.jenkins-config.groovy' : 'fallback.groovy')
                notifyBitbucket(cfg.credentials.id)
            }
        }
    }
}
```

PROHIBITED:
```groovy
post {
    success {
        node(label) {
            script {
                // PROJECT_CONFIG set earlier — null after node boundary crossing
                notifyBitbucket(PROJECT_CONFIG.credentials.id)  // NullPointerException
            }
        }
    }
}
```

**CONSTRAINT:** `Calculate Image Tags` stage MUST use `params.UPSTREAM_*_IMAGE` as Docker agent — NOT `env.CI_RUNTIME_IMAGE`.

The CI runtime image tag is the OUTPUT of this stage — it does not exist yet when the agent starts.

```groovy
stage('Calculate Image Tags') {
    agent {
        docker {
            image params.UPSTREAM_PYTHON_IMAGE   // ← known param, not env.CI_RUNTIME_IMAGE
            args  DOCKER_CONFIG.jenkinsAgent.dockerArgs
            label DOCKER_CONFIG.jenkinsAgent.label
            registryUrl           DOCKER_CONFIG.registry.pullUrl
            registryCredentialsId DOCKER_CONFIG.registry.credentialsId
        }
    }
}
```

Paired parameter:
```groovy
string(name: 'UPSTREAM_PYTHON_IMAGE',
    defaultValue: '<DOCKER_PULL_DOMAIN>/python:3.12-bookworm',
    description: 'Bootstrap image for Calculate Image Tags stage')
```

Verification:
- Agent uses `params.UPSTREAM_PYTHON_IMAGE`: PASS
- Agent uses `env.CI_RUNTIME_IMAGE`: FAIL (pull failure — image doesn't exist yet)

## Verification Checklist

- [ ] `agent none` at pipeline level when any stage uses Docker
- [ ] No `agent` + `parallel` on same stage (compile error)
- [ ] Pipeline-level timeout present
- [ ] Stage-level timeouts on all stages >5 min
- [ ] `disableConcurrentBuilds` + `copyArtifactPermission` present when `copyArtifacts` used
- [ ] `SHOULD_PUSH` env var with branch regex + `PUSH_TO_REGISTRY` parameter override
- [ ] Post blocks use `node(label)` not Docker agents
- [ ] Post block has all four states: `success`, `failure`, `unstable`, `aborted`
- [ ] Non-fatal `sh` uses `returnStatus: true` not `try/catch`
- [ ] Post `node()` blocks reload config via `checkout scm` + `load()` — not script-level vars
- [ ] Calculate Image Tags agent uses parameter, not `env.CI_RUNTIME_IMAGE`
