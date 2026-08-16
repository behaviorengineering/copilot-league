---
name: jenkins-gitops-stages
description: 'Jenkins dispatcher pattern and GitOps stage structure. Use when writing CI Jenkinsfiles, Release Jenkinsfiles, or .groovy stage files: dispatcher simplicity rules, GitOps CI stage order, stage single-responsibility, stage return maps, workspace prerequisites, copyArtifacts/unstash on label agents only, dist/ root-owned directory cleanup, network retry with exponential backoff.'
user-invocable: false
---

# Jenkins GitOps Stages

## When to Load

Load when writing any Jenkinsfile (CI or Release) or `.groovy` stage files.

For pipeline and stage code templates, load `.github/agents/references/jenkins-patterns.md`.

## Core Constraints

**CONSTRAINT:** Dispatcher Jenkinsfiles MUST contain ONLY routing logic — no business logic.

Allowed: `params.*`, `env.BRANCH_NAME`, `when {}`, `load`, simple `if/else` routing.
PROHIBITED: business rules, loops, data transformations, complex string parsing.

**CONSTRAINT:** CI pipelines MUST follow GitOps stage order.

```
clone → validate → calculate-image-tags → build → test → security-scan → publish → update-manifests → [wait-for-argocd]
```

Stage gating rules:
- `publish`, `update-manifests`: `when { expression { env.SHOULD_PUSH == 'true' } }`
- `wait-for-argocd`: optional, master/main only

Stage naming: MUST be self-documenting (e.g., `Build Application`, `Test Unit`). MUST NOT mix concerns (e.g., `Build and Test` is PROHIBITED).

**CONSTRAINT:** Each stage file MUST have single responsibility — one action only.

| Stage file | Action |
|---|---|
| `build.groovy` | Artifact/image creation ONLY |
| `test.groovy` | Test execution ONLY |
| `publish.groovy` | Push to registry ONLY |
| `update-manifests.groovy` | Update manifest repo ONLY |
| `wait-for-argocd.groovy` | ArgoCD health check ONLY |
| `security.groovy` | Security scanning ONLY |
| `sonar.groovy` | SonarQube analysis ONLY |

**CONSTRAINT:** Stages MUST return named method maps. Names MUST NOT collide with Jenkins DSL steps (see `jenkins-groovy-patterns` skill). Methods receive `logger`, `executor` via injection.

```groovy
// .jenkins/stages/build.groovy
def runBuild(logger, executor, String component, String buildNumber) {
    executor.withOperationLogging(logger, 'Build', component) {
        sh "bash ./.jenkins/scripts/build.sh ${component} ${buildNumber}"
        archiveArtifacts(artifacts: "dist/${component}/**", allowEmptyArchive: false)
    }
}
return [runBuild: this.&runBuild]
```

**CONSTRAINT:** Credentials and tool environments MUST be injected at dispatcher level — stages contain ZERO credential/environment management code.

```groovy
// Dispatcher — owns withCredentials and tool env wrappers
stage('SonarQube Analysis') {
    steps {
        script {
            def scannerHome = tool 'SONARSCANNER_4.2'
            withSonarQubeEnv('Enterprise SonarQube') {
                def deps = loadDependencies()
                def module = load '.jenkins/stages/sonar.groovy'
                deps.executor.retryWithBackoff(deps.logger, 1, 0) {
                    module.runScan(deps.logger, deps.executor, scannerHome)
                }
            }
        }
    }
}
```

**CONSTRAINT:** Stages MUST own their own workspace prerequisites (self-contained for sequential execution).

Artifact retrieval belongs INSIDE the stage groovy file — NOT the dispatcher.

EXCEPTION: When multiple parallel closures share a workspace, the dispatcher MUST pre-fetch before `parallel()` to avoid race conditions (two closures independently calling `copyArtifacts` race each other).

CORRECT (sequential stage):
```groovy
// inside publish.groovy — stage owns its prerequisite check
def wheelExists = sh(script: "ls dist/${component}/*.whl 2>/dev/null", returnStatus: true) == 0
if (!wheelExists) {
    copyArtifacts(projectName: env.JOB_NAME, selector: specific(buildNumber),
        filter: "dist/${component}/*.whl", fingerprintArtifacts: false)
}
```

PROHIBITED (dispatcher prepares workspace for a single sequential stage):
```groovy
// Dispatcher — WRONG
sh "rm -rf dist/${env.COMPONENT_NAME}/*.whl"
copyArtifacts(projectName: env.JOB_NAME, ...)
def module = load '.jenkins/stages/publish.groovy'
module.runPublish(...)
```

**CONSTRAINT:** `copyArtifacts`, `stash`, and `unstash` MUST run on `label` agents — NEVER Docker agents.

Docker containers run as uid 0; NFS workspace uses `root_squash` (uid 0 → nobody). `unstash` calls `chown()` on every extracted file — rejected by NFS → 5-minute hang then `IOException`. `copyArtifacts` fails inside Docker agents (no NFS mount available).

Enforcement: Any stage calling `copyArtifacts`/`unstash`/`stash` MUST use `agent { label DOCKER_CONFIG.jenkinsAgent.label }`.

CORRECT:
```groovy
stage('Publish & Package') {
    agent { label DOCKER_CONFIG.jenkinsAgent.label }  // ← label agent: NFS accessible
    steps { script { unstash 'my-artifact' } }
}
```

PROHIBITED:
```groovy
stage('Publish & Package') {
    agent { docker { image env.CI_RUNTIME_IMAGE } }   // ← Docker agent: unstash hangs ~5min
    steps { script { unstash 'my-artifact' } }         // IOException: Failed to extract
}
```

**CONSTRAINT:** MUST clean entire `dist/` before `copyArtifacts` on a label agent when prior Docker stages ran.

Prior Docker stages run as root — `dist/` is root-owned. Label agent (Jenkins host user) cannot write into it. Cleaning only `dist/<component>/` is INSUFFICIENT — the root-owned parent `dist/` still blocks the write.

CORRECT: `deps.executor.cleanRootOwnedDir(env.CI_RUNTIME_IMAGE, 'dist')` // entire dist/
PROHIBITED: `deps.executor.cleanRootOwnedDir(env.CI_RUNTIME_IMAGE, "dist/${env.COMPONENT_NAME}")` // root parent remains

**CONSTRAINT:** Network-dependent operations MUST use retry with exponential backoff.

Operations requiring retry: registry queries, image builds, pip installs, security scans, external API calls.

```groovy
// Registry query: 3 attempts, 10s initial delay
deps.executor.retry(deps.logger, 3, 10) {
    imageExists = module.checkImage(python314Image)
}
// Image build: 3 attempts, 15-20s initial delay (large downloads)
deps.executor.retry(deps.logger, 3, 15) {
    module.runDockerBuild(component, version)
}
```

For delay values by operation type, load `.github/agents/references/jenkins-patterns.md` § Jenkins Retry Patterns.

**CONSTRAINT:** Release Jenkinsfile MUST have an approval gate before production deployment.

```groovy
stage('Approval Gate') {
    when { expression { params.ENVIRONMENT == 'prod' } }
    steps {
        timeout(time: 24, unit: 'HOURS') {
            input message: 'Approve production deployment?', ok: 'Deploy',
                  submitter: 'deployment-approvers'
        }
    }
}
```

## Verification Checklist

- [ ] Dispatcher contains ONLY routing logic (≤3 lines beyond if/when/load)
- [ ] CI pipeline has all GitOps stages in correct order with correct `when` gating
- [ ] Each stage file has single responsibility (one action only)
- [ ] Stage `return [...]` keys don't collide with DSL reserved names (see jenkins-groovy-patterns)
- [ ] Stages are self-contained for sequential execution (own their prerequisites)
- [ ] `copyArtifacts`/`stash`/`unstash` on label agents only — never Docker agents
- [ ] Entire `dist/` cleaned (not component-scoped) before `copyArtifacts` on label agent
- [ ] All network operations wrapped with `deps.executor.retry()`
- [ ] Release pipeline has approval gate with `submitter` restriction before production
- [ ] Quality checks (test, security, sonar) run in parallel with `failFast`
