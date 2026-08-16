# Jenkins Pipeline Patterns

Reference patterns for this project. Load when generating pipeline files.

MUST load [environment.md](./environment.md) first. Angle-bracket tokens (`<DOCKER_PULL_DOMAIN>`) are keys from that overlay — substitute the Value column when generating code.

## Table of Contents
1. [Jenkins Pipeline Structure](#jenkins-pipeline-structure)
2. [Jenkins Stage Patterns](#jenkins-stage-patterns)
3. [Jenkins Docker Image Patterns](#jenkins-docker-image-patterns)
4. [Jenkins Parallel Execution](#jenkins-parallel-execution)
5. [Jenkins Versioning](#jenkins-versioning)
6. [Jenkins Downstream Job Orchestration](#jenkins-downstream-job-orchestration)
7. [Jenkins Conditional Stages](#jenkins-conditional-stages)
8. [Jenkins Retry Patterns](#jenkins-retry-patterns)
9. [Jenkins Bash Script Patterns](#jenkins-bash-script-patterns)

---

## Jenkins Pipeline Structure

### CI Pipeline (Auto-Triggered with GitOps)

**Purpose:** Automated build, test, and GitOps deployment via ArgoCD on branch merges

**Pattern:** GitOps (PREFERRED) - Jenkins builds artifacts, ArgoCD handles deployment

**File:** `.jenkins/pipelines/ComponentName.CI.Jenkinsfile`

```groovy
// Docker config map — defined at top of Jenkinsfile, referenced everywhere
def DOCKER_CONFIG = [
    registry: [
        pullDomain: '<DOCKER_PULL_DOMAIN>',
        pullUrl:    'https://<DOCKER_PULL_DOMAIN>',
        pushDomain: '<DOCKER_PUSH_DOMAIN>',
        credentialsId: '<DOCKER_CREDS_ID>'
    ],
    jenkinsAgent: [
        label:      '<JENKINS_AGENT_LABEL>',
        dockerArgs: '-u root -e HOME=/root'  // root required for NFS workspace + tool resolution
    ],
    images: [
        ciRuntimeImageName:       'myapp-deps',
        appRuntimeImageNamePrefix: 'myapp'
    ]
]

// Load shared libs from .jenkins/lib/ — call at the top of every script {} block
def loadDependencies() {
    def logger      = load '.jenkins/lib/logger.groovy'
    def executor    = load '.jenkins/lib/executor.groovy'
    def dependencies = load '.jenkins/lib/dependencies.groovy'
    return [logger: logger, executor: executor, dependencies: dependencies]
}

pipeline {
    agent none  // REQUIRED: each stage defines its own agent to avoid Docker-in-Docker

    parameters {
        string(name: 'MODULE', defaultValue: 'mymodule', description: 'Component to build')
        booleanParam(name: 'PUSH_TO_REGISTRY', defaultValue: false,
            description: 'Push images (auto-enabled on master/main/develop)')
        string(name: 'UPSTREAM_PYTHON_IMAGE',
            defaultValue: '<DOCKER_PULL_DOMAIN>/python:3.14-bookworm',
            description: 'Bootstrap image for Calculate Image Tags stage')
    }

    environment {
        COMPONENT_NAME = "${params.MODULE}"
        REGISTRY        = credentials('<REGISTRY_CREDS_ID>')
        PIP_INDEX_URL   = "https://${REGISTRY_USR}:${REGISTRY_PSW}@<PACKAGE_REGISTRY_HOST>/<PIP_INDEX_PATH>"
        HTTP_PROXY      = '<HTTP_PROXY>'
        HTTPS_PROXY     = '<HTTP_PROXY>'
        NO_PROXY        = '<NO_PROXY>'
        SHOULD_PUSH     = "${(env.BRANCH_NAME ==~ /(master|main|develop)/) ? 'true' : params.PUSH_TO_REGISTRY}"
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        disableConcurrentBuilds(abortPrevious: true)
        copyArtifactPermission('*')  // required when any stage calls copyArtifacts
    }

    stages {
        // Bootstrap: use UPSTREAM_PYTHON_IMAGE — CI_RUNTIME_IMAGE doesn't exist yet
        stage('Calculate Image Tags') {
            agent {
                docker {
                    image params.UPSTREAM_PYTHON_IMAGE
                    args  DOCKER_CONFIG.jenkinsAgent.dockerArgs
                    label DOCKER_CONFIG.jenkinsAgent.label
                    registryUrl           DOCKER_CONFIG.registry.pullUrl
                    registryCredentialsId DOCKER_CONFIG.registry.credentialsId
                }
            }
            steps {
                script {
                    def deps = loadDependencies()
                    def module = load '.jenkins/stages/calculate-image-tags.groovy'
                    def tags = module.calculateImageTags(deps.logger, deps.executor,
                        deps.dependencies, DOCKER_CONFIG.registry.pullDomain,
                        DOCKER_CONFIG.images.ciRuntimeImageName, env.COMPONENT_NAME)
                    env.CI_RUNTIME_IMAGE = tags.ciRuntimeImage
                    env.APP_IMAGE_TAG    = tags.appImageTag
                    env.PEP440_VERSION   = tags.pep440Version
                }
            }
        }

        stage('Build, Test & Lint') {
            parallel {
                stage('Build') {
                    agent {
                        docker {
                            image env.CI_RUNTIME_IMAGE
                            args  DOCKER_CONFIG.jenkinsAgent.dockerArgs
                            label DOCKER_CONFIG.jenkinsAgent.label
                            registryUrl           DOCKER_CONFIG.registry.pullUrl
                            registryCredentialsId DOCKER_CONFIG.registry.credentialsId
                        }
                    }
                    options { timeout(time: 15, unit: 'MINUTES') }
                    steps {
                        script {
                            def deps = loadDependencies()
                            def module = load '.jenkins/stages/build.groovy'
                            deps.executor.retry(deps.logger, 2, 5) {
                                module.build(deps.logger, deps.executor,
                                    env.COMPONENT_NAME, env.BUILD_NUMBER, env.PEP440_VERSION)
                            }
                        }
                    }
                }
                stage('Test') {
                    when { expression { fileExists("src/${env.COMPONENT_NAME}/tests") } }
                    agent {
                        docker {
                            image env.CI_RUNTIME_IMAGE
                            args  DOCKER_CONFIG.jenkinsAgent.dockerArgs
                            label DOCKER_CONFIG.jenkinsAgent.label
                            registryUrl           DOCKER_CONFIG.registry.pullUrl
                            registryCredentialsId DOCKER_CONFIG.registry.credentialsId
                        }
                    }
                    options { timeout(time: 20, unit: 'MINUTES') }
                    steps {
                        script {
                            def deps = loadDependencies()
                            def module = load '.jenkins/stages/test.groovy'
                            deps.executor.retry(deps.logger, 2, 5) {
                                module.test(deps.logger, deps.executor, env.COMPONENT_NAME)
                            }
                        }
                    }
                }
            }
        }

        stage('Publish & Package') {
            when { expression { env.SHOULD_PUSH == 'true' } }
            // Label agent (not Docker) — copyArtifacts/unstash cannot run inside Docker on NFS
            agent { label DOCKER_CONFIG.jenkinsAgent.label }
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                script {
                    def deps = loadDependencies()
                    deps.executor.cleanRootOwnedDir(env.CI_RUNTIME_IMAGE, 'dist')
                    deps.executor.copyBuildArtifacts(deps.logger, env.COMPONENT_NAME, env.BUILD_NUMBER)
                    def module = load '.jenkins/stages/publish-wheel.groovy'
                    deps.executor.retry(deps.logger, 3, 15) {
                        module.publish(deps.logger, deps.executor,
                            env.CI_RUNTIME_IMAGE, env.COMPONENT_NAME, env.BUILD_NUMBER)
                    }
                }
            }
        }
    }

    post {
        success {
            node(DOCKER_CONFIG.jenkinsAgent.label) {
                script { loadDependencies().logger.info("Pipeline succeeded — Build: ${env.BUILD_NUMBER}") }
            }
        }
        failure {
            node(DOCKER_CONFIG.jenkinsAgent.label) {
                script { loadDependencies().logger.error("Pipeline failed — Build: ${env.BUILD_NUMBER}") }
            }
        }
    }
}
```

### Release Pipeline (Manual Promotion)

**Purpose:** Manual promotion of validated builds through test → prod with approval gates

**File:** `.jenkins/pipelines/ComponentName.Release.Jenkinsfile`

```groovy
pipeline {
    agent { label 'deploy-agent' }
    
    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['test', 'prod'],
            description: 'Target environment for deployment'
        )
        string(
            name: 'BUILD_VERSION',
            description: 'Build version to promote (e.g., build-123)'
        )
    }
    
    options {
        timeout(time: 25, unit: 'HOURS')  // Allows 24hr approval window
    }
    
    stages {
        stage('Validate Parameters') {
            steps {
                script {
                    echo "[${new Date()}] [INFO] Validating deployment parameters"
                    echo "[${new Date()}] [INFO] Environment: ${params.ENVIRONMENT}"
                    echo "[${new Date()}] [INFO] Build Version: ${params.BUILD_VERSION}"
                    
                    if (!params.BUILD_VERSION) {
                        error "[ERROR] BUILD_VERSION parameter is required"
                    }
                }
            }
        }
        
        stage('Deploy to Test') {
            when {
                expression { params.ENVIRONMENT == 'test' }
            }
            options {
                timeout(time: 15, unit: 'MINUTES')
            }
            steps {
                script {
                    echo "[${new Date()}] [INFO] Deploying version ${params.BUILD_VERSION} to Test"
                    load '.jenkins/stages/deploy-test.groovy'
                    echo "[${new Date()}] [INFO] Test deployment completed"
                }
            }
        }
        
        stage('Production Approval Gate') {
            when {
                expression { params.ENVIRONMENT == 'prod' }
            }
            steps {
                script {
                    echo "[${new Date()}] [WARN] Production deployment requested - approval required"
                }
                timeout(time: 24, unit: 'HOURS') {
                    input(
                        message: "Approve production deployment of ${params.BUILD_VERSION}?",
                        ok: 'Deploy to Production',
                        submitter: 'deployment-approvers'
                    )
                }
                script {
                    echo "[${new Date()}] [INFO] Production deployment approved"
                }
            }
        }
        
        stage('Deploy to Production') {
            when {
                expression { params.ENVIRONMENT == 'prod' }
            }
            options {
                timeout(time: 20, unit: 'MINUTES')
            }
            steps {
                script {
                    echo "[${new Date()}] [INFO] Deploying version ${params.BUILD_VERSION} to Production"
                    load '.jenkins/stages/deploy-prod.groovy'
                    echo "[${new Date()}] [INFO] Production deployment completed"
                }
            }
        }
    }
    
    post {
        success {
            echo "[${new Date()}] [INFO] Deployment to ${params.ENVIRONMENT} succeeded"
        }
        failure {
            echo "[${new Date()}] [ERROR] Deployment to ${params.ENVIRONMENT} failed"
        }
    }
}
```

---

## Jenkins Stage Patterns

### Build Stage

**Purpose:** Reusable build stage for artifact creation

**File:** `.jenkins/stages/build.groovy`

```groovy
// .jenkins/stages/build.groovy
// Returns object with build method
// Uses dependency injection - receives logger and executor as parameters

// Build-specific function: Execute build script and archive artifacts
def buildArtifact(params) {
    sh "bash ./.jenkins/scripts/build.sh ${params.component} ${params.buildNumber} ${params.version}"
    archiveArtifacts(
        artifacts: "dist/${params.component}/**",
        allowEmptyArchive: false
    )
}

// Public API method - receives injected dependencies
def build(logger, executor, String component, String buildNumber, String version) {
    logger.info("Build configuration:")
    logger.info("  Component:      ${component}")
    logger.info("  Build number:   ${buildNumber}")
    logger.info("  Version:        ${version}")
    
    executor.withOperationLogging(logger, 'Build', component) {
        buildArtifact([component: component, buildNumber: buildNumber, version: version])
    }
}

return [build: this.&build]
```

**Usage in dispatcher:**
```groovy
// In ComponentName.CI.Jenkinsfile
stage('Build') {
    steps {
        script {
            def module = load '.jenkins/stages/build.groovy'
            module.build(component: env.COMPONENT_NAME, buildNumber: env.BUILD_NUMBER)
        }
    }
}
```

### Deploy Stage

**Purpose:** Universal deployment stage for all environments

**File:** `.jenkins/stages/deploy.groovy`

```groovy
// .jenkins/stages/deploy.groovy
// Returns object with deploy method
// Uses dependency injection - receives logger and executor as parameters

// Deploy-specific validation: different requirements per environment
def validateDeployment(params, env) {
    def required = ['component']
    required.each { field ->
        if (!params[field]) error "Missing required parameter: ${field}"
    }
    
    def allowed = ['qa', 'dev', 'test', 'prod']
    if (!allowed.contains(env)) {
        error "Invalid environment: ${env}. Allowed: ${allowed.join(', ')}"
    }
    
    // Production/Test require buildVersion, QA/Dev use buildNumber
    if (env in ['prod', 'test'] && !params.buildVersion) {
        error "Missing required parameter: buildVersion"
    } else if (env in ['qa', 'dev'] && !params.buildNumber) {
        error "Missing required parameter: buildNumber"
    }
}

// Deploy-specific function: Execute deployment and verification
def executeDeployment(env, params) {
    def version = params.buildVersion ?: params.buildNumber
    sh "bash ./.jenkins/scripts/deploy.sh ${env} ${params.component} ${version}"
    sh "bash ./.jenkins/scripts/verify-deployment.sh ${env} ${params.component}"
    
    // Production-specific: tag the release
    if (env == 'prod' && params.buildVersion) {
        def tag = "${params.component}-${params.buildVersion}-prod"
        sh "git tag ${tag} && git push origin ${tag}"
    }
}

// Public API method - receives injected dependencies
def deploy(logger, executor, String environment, Map params = [:]) {
    def config = [component: 'automation'] + params
    validateDeployment(config, environment)
    
    executor.withOperationLogging(logger, "${environment.toUpperCase()} deployment", config.component) {
        executeDeployment(environment, config)
    }
}

return [deploy: this.&deploy]
```

### SonarQube Stage

**Purpose:** Reusable SonarQube code quality analysis stage

**File:** `.jenkins/stages/sonar.groovy`

```groovy
// .jenkins/stages/sonar.groovy
// Returns object with scan method
// Note: withSonarQubeEnv wrapper is applied at dispatcher level (IoC pattern)

// SonarQube-specific function: Execute scanner via script
def runScan(scannerHome) {
    sh "bash ./.jenkins/scripts/sonar.sh '${scannerHome}'"
}

// Public API method
def scan(logger, executor, scannerHome) {
    executor.withOperationLogging(logger, 'SonarQube Analysis', 'project') {
        runScan(scannerHome)
    }
}

return [scan: this.&scan]
```

**Usage in dispatcher:**
```groovy
// In ComponentName.CI.Jenkinsfile
stage('SonarQube Analysis') {
    steps {
        script {
            def scannerHome = tool 'SONARSCANNER_4.2'
            withSonarQubeEnv('Enterprise SonarQube') {
                def deps = loadDependencies()
                def module = load '.jenkins/stages/sonar.groovy'
                module.scan(deps.logger, deps.executor, scannerHome)
            }
        }
    }
}
```

**Key Patterns:**
- **Tool Injection:** `tool 'SONARSCANNER_4.2'` retrieves configured tool path
- **Environment Wrapper:** `withSonarQubeEnv` injects server config at dispatcher level
- **IoC Compliance:** Stage has NO knowledge of SonarQube server configuration
- **Script Portability:** Scanner path passed as argument, script works locally
- **Branch Detection:** Uses Jenkins environment variables (BRANCH_NAME, GIT_BRANCH)

### ArgoCD Wait Stage

**Purpose:** Wait for ArgoCD to sync and report healthy deployment (GitOps pattern)

**File:** `.jenkins/stages/wait-for-argocd.groovy`

```groovy
// .jenkins/stages/wait-for-argocd.groovy
// Returns object with waitForSync method
// Note: ArgoCD CLI must be available on agent or installed in Docker image
// Uses dependency injection - receives logger and executor as parameters

// ArgoCD-specific function: Wait for sync and health check
def waitForHealthy(appName, timeout) {
    sh "bash ./.jenkins/scripts/wait-for-argocd.sh '${appName}' '${timeout}'"
}

// Public API method - receives injected dependencies
def waitForSync(logger, executor, String appName, String timeout = '300') {
    if (!appName) error "Missing required parameter: appName"
    if (!timeout) error "Missing required parameter: timeout"
    
    executor.withOperationLogging(logger, "ArgoCD sync wait", appName) {
        waitForHealthy(appName, timeout)
    }
}

return [waitForSync: this.&waitForSync]
```

**Usage in dispatcher:**
```groovy
// In ComponentName.CI.Jenkinsfile
stage('Wait for ArgoCD Deployment') {
    when { branch 'master' }
    steps {
        script {
            withCredentials([string(credentialsId: 'argocd-auth-token', variable: 'ARGOCD_AUTH_TOKEN')]) {
                env.ARGOCD_SERVER = '<ARGOCD_SERVER>'
                def module = load '.jenkins/stages/wait-for-argocd.groovy'
                module.waitForSync(
                    appName: "post-creator-${env.COMPONENT_NAME}",
                    timeout: '600'  // 10 minutes
                )
            }
        }
    }
}
```

**Key Patterns:**
- **GitOps Decoupling:** Jenkins builds artifacts, ArgoCD handles deployment
- **Health Verification:** Waits for both sync completion and health check
- **Credential Injection:** ArgoCD token provided via Jenkins credentials at dispatcher level
- **Timeout Protection:** Configurable timeout prevents indefinite waits
- **Status Visibility:** Logs sync and health status every interval for debugging

---

## Jenkins Docker Image Patterns

### Registry Existence Check (manifest inspect)

**Purpose:** Lightweight check for image existence without downloading it. Used to implement cache-hit / cache-miss logic before triggering an expensive build.

```groovy
// In a stage groovy file
def imageExistsInRegistry(String image) {
    return sh(
        script: "docker manifest inspect '${image}' > /dev/null 2>&1",
        returnStatus: true
    ) == 0
}

def ensureImage(logger, executor, String image) {
    executor.withOperationLogging(logger, 'Ensure Image', image) {
        if (imageExistsInRegistry(image)) {
            logger.info("Image already exists in registry — cache hit, nothing to build")
            return
        }
        logger.info("Image not found — building")
        sh "bash ./.jenkins/scripts/build-image.sh '${image}'"
    }
}
```

**Key Patterns:**
- `docker manifest inspect` hits only the registry API — no image pull
- `returnStatus: true` converts non-zero exit to `false` without failing the step
- Cache-hit path returns immediately, skipping all downstream build work
- Wrap with `executor.retry()` — manifest inspect is a network operation

PROHIBITED:
```groovy
// WRONG — pulls entire image just to check existence
def exists = sh(script: "docker pull ${image}", returnStatus: true) == 0
```

### App-Deps Layered Image Cache

**Purpose:** Pre-bake runtime dependencies into a hash-tagged base image keyed on `uv.lock + pyproject.toml`. Cache hit (most builds) skips all package downloads. Cache miss (lock file changed) builds once and subsequent builds reuse it.

**Hash calculation** (`dependencies.groovy`):
```groovy
def getAppDepsHash(String component) {
    def hash = sh(
        script: "bash ./.jenkins/scripts/lib/get-app-deps-hash.sh '${component}'",
        returnStdout: true
    ).trim()
    return hash  // first 12 chars of sha256 over uv.lock + pyproject.toml
}
```

**Stage pattern:**
```groovy
def ensureAppDeps(logger, executor, String appDepsImage, String pythonBaseImage,
                  String component, String dockerfilePath) {
    executor.withOperationLogging(logger, 'Ensure App Deps Image', appDepsImage) {
        if (imageExistsInRegistry(appDepsImage)) {
            logger.info("Image already exists — cache hit, nothing to build")
            return
        }
        def wheelFile = findWheelFile(component)  // error if missing
        sh """bash ./.jenkins/scripts/build-app-deps-image.sh \
            '${appDepsImage}' '${pythonBaseImage}' '${wheelFile}' \
            '${dockerfilePath}' '${component}'
        """
    }
}
```

**Image tag structure:**
```
<registry>/<app>-<component>-app-deps:<appDepsHash>    ← Debian
<registry>/<app>-<component>-app-deps-rhel:<appDepsHash>  ← RHEL
```

**Key Patterns:**
- Hash over `src/<component>/uv.lock` + `src/<component>/pyproject.toml` only — not CI tooling deps
- Wheel must be pre-fetched by the dispatcher before calling `ensureAppDeps` (parallel-safe)
- `imageExistsInRegistry` guards the expensive build — most builds return in ~2s
- Separate images per OS variant (Debian / RHEL) but same hash tag

---

## Jenkins Parallel Execution

### Shared-Node Parallel with `script { parallel(...) }`

**Purpose:** Run multiple closures in parallel on the same allocated node when declarative `parallel` is forbidden by Jenkins (i.e., when the stage also has an `agent` directive).

```groovy
stage('Build Application Images') {
    agent {
        label DOCKER_CONFIG.jenkinsAgent.label
    }
    options { timeout(time: 30, unit: 'MINUTES') }
    steps {
        script {
            def deps = loadDependencies()
            // Pre-fetch shared artifacts ONCE before parallel — prevents race condition
            // where both closures call cleanRootOwnedDir + copyBuildArtifacts simultaneously.
            deps.executor.cleanRootOwnedDir(env.CI_RUNTIME_IMAGE, 'dist')
            deps.executor.copyBuildArtifacts(deps.logger, env.COMPONENT_NAME, env.BUILD_NUMBER)

            def module = load '.jenkins/stages/docker-app-image.groovy'
            withCredentials([usernamePassword(
                credentialsId: DOCKER_CONFIG.registry.credentialsId,
                usernameVariable: 'DOCKER_USER',
                passwordVariable: 'DOCKER_PASS'
            )]) {
                // NOTE: script { parallel(...) } used instead of declarative parallel
                // because Jenkins forbids 'agent' and 'parallel' on the same stage.
                parallel(
                    'Debian': {
                        deps.executor.retry(deps.logger, 3, 15) {
                            module.buildImage(deps.logger, deps.executor, /* debian args */)
                        }
                    },
                    'RHEL': {
                        deps.executor.retry(deps.logger, 3, 15) {
                            module.buildImage(deps.logger, deps.executor, /* rhel args */)
                        }
                    }
                )
            }
        }
    }
}
```

**Key Patterns:**
- Clean `dist/` entirely (not just `dist/<component>/`) before `copyBuildArtifacts` — root-owned parent blocks writes
- `withCredentials` at dispatcher level, OUTSIDE `parallel()` — credentials are inherited by all closures
- Each parallel closure independently retried — a Debian failure does not skip RHEL
- `cleanRootOwnedDir` uses `docker run --rm` to remove root-owned files the host user cannot delete

PROHIBITED:
```groovy
stage('Build') {
    agent { label 'host' }
    parallel {              // ← compile error: agent + parallel on same stage
        stage('Debian') { ... }
    }
}
```

---

## Jenkins Versioning

### Docker Tag Sanitization

**Purpose:** Normalize branch names to Docker-tag-safe strings (Docker tags: lowercase alphanumeric, `.`, `-`, `_`, max 128 chars).

```groovy
def sanitizeBranchName(String branchName) {
    return branchName
        .toLowerCase()
        .replaceAll('[^a-z0-9._-]', '-')  // replace slashes and invalid chars with dash
        .replaceAll('-+', '-')             // collapse consecutive dashes
        .replaceAll('^-|-$', '')           // strip leading/trailing dashes
        .take(64)                          // leave room for date.buildNumber suffix
}
```

### App Image Tag (date.branch.buildNumber)

**Purpose:** Produce a human-readable, sortable, unique image tag per build.

```groovy
def calculateAppImageTag(String branchName, String buildNumber) {
    def date = new Date().format('yyyyMMdd')
    def sanitizedBranch = sanitizeBranchName(branchName ?: 'unknown')
    return "${date}.${sanitizedBranch}.${buildNumber}"
    // e.g. 20260402.feature-my-thing.366
}
```

### PEP 440 Wheel Version (no `+` local segment)

**Purpose:** Produce a PEP 440-compliant version for Python wheels that is safe for `copyArtifacts` Ant glob matching.

**CRITICAL:** Do NOT include a `+` local segment (e.g. `+branch`). Jenkins URL-encodes `+` → `%2B` in filenames, which breaks Ant glob patterns in `copyArtifacts`.

```groovy
def calculatePep440Version(String buildNumber) {
    // Format: YEAR.MONTH.DAY.buildNumber (M/d skips zero-padding)
    // Example: 2026.3.25.366
    def date = new Date()
    return "${date.format('yyyy')}.${date.format('M')}.${date.format('d')}.${buildNumber}"
}
```

PROHIBITED:
```groovy
// WRONG — '+' becomes '%2B' in wheel filenames → copyArtifacts glob fails
return "${date}.${buildNumber}+${branchName}"
```

### Tag Override Parameter Pattern

**Purpose:** Allow manual override of any hash-based image tag while keeping auto-calculation as the default. Applied to every hash-tagged image in the pipeline.

```groovy
// Parameter declaration (one per image)
string(
    name: 'CI_RUNTIME_IMAGE_TAG_OVERRIDE',
    defaultValue: '',
    description: 'Override CI runtime image tag (leave empty to use hash-based tag)'
)

// Apply override with ternary (empty string = use calculated value)
env.CI_RUNTIME_IMAGE_TAG = params.CI_RUNTIME_IMAGE_TAG_OVERRIDE ?: tags.ciRuntimeImageTag
env.CI_RUNTIME_IMAGE = "${DOCKER_CONFIG.registry.pullDomain}/${imageName}:${env.CI_RUNTIME_IMAGE_TAG}"
```

**Key Patterns:**
- Default is `''` (not a real value) — Groovy `?:` treats empty string as falsy
- Override is applied AFTER hash calculation, so the hash is always computed (useful for logging)
- Naming convention: `<IMAGE_PURPOSE>_TAG_OVERRIDE` for all overrideable images

---

## Jenkins Downstream Job Orchestration

### Triggered Downstream Build with URL Capture

**Purpose:** Trigger a downstream Jenkins job, capture its URL for error context before deciding to fail, and propagate failure with a meaningful message.

```groovy
def triggerDownstreamJob(String jobName, List jobParams, logger) {
    // propagate: false lets us capture the build URL before deciding to fail
    def run = build job: jobName, wait: true, propagate: false, parameters: jobParams

    if (run.result != 'SUCCESS') {
        logger.error("${jobName} #${run.number} ${run.result} — see: ${run.absoluteUrl}console")
        error "${jobName} #${run.number} ${run.result}"
    }
    return run
}

// Caller (in a stage groovy file)
def ensureCIRuntime(logger, executor, String imageName, String imageTag,
                    String jobName, String upstreamImage, String imageTagOverride = '') {
    executor.withOperationLogging(logger, 'Ensure CI Runtime Image', imageTag) {
        def params = [string(name: 'UPSTREAM_PYTHON_IMAGE', value: upstreamImage)]
        if (imageTagOverride) {
            params.add(string(name: 'IMAGE_TAG', value: imageTagOverride))
        }
        def run = triggerDownstreamJob(jobName, params, logger)
        logger.info("CI Runtime Image ready — build: ${run.absoluteUrl}")
    }
}
```

**Key Patterns:**
- `propagate: false` prevents Jenkins from auto-failing — gives control to capture context first
- Log `run.absoluteUrl` + `run.number` so the failure is traceable without searching
- Conditional parameter injection: only add override params when they carry a non-empty value
- Wrap with `executor.retry()` — downstream job trigger is a network operation

PROHIBITED:
```groovy
// WRONG — propagate: true (default) fails immediately, losing the build URL
build job: jobName, wait: true, parameters: params
```

---

## Jenkins Conditional Stages

### Directory-Existence Guard (`fileExists`)

**Purpose:** Skip a stage entirely when its input directory does not exist — useful for optional components in a monorepo where not every module has tests, docs, etc.

```groovy
stage('Test') {
    when {
        expression { fileExists("src/${env.COMPONENT_NAME}/tests") }
    }
    options { timeout(time: 20, unit: 'MINUTES') }
    steps {
        script {
            def deps = loadDependencies()
            def module = load '.jenkins/stages/test.groovy'
            deps.executor.retry(deps.logger, 2, 5) {
                module.test(deps.logger, deps.executor, env.COMPONENT_NAME)
            }
        }
    }
}
```

**Key Patterns:**
- `fileExists()` is evaluated at stage runtime, not pipeline parse time — `env.*` interpolation works
- Use for any optional stage whose input may legitimately be absent (tests, docs, migrations)
- Combine with `SHOULD_PUSH` branch detection for publish/deploy gates (see below)

### Branch-Based Push Gate (`SHOULD_PUSH`)

**Purpose:** Auto-enable registry push on integration branches; allow manual override via parameter for other branches.

```groovy
// In pipeline environment block
environment {
    // Push automatically on master/main/develop; parameter controls feature branches
    SHOULD_PUSH = "${(env.BRANCH_NAME ==~ /(master|main|develop)/) ? 'true' : params.PUSH_TO_REGISTRY}"
}

// Parameter (paired with environment var)
booleanParam(
    name: 'PUSH_TO_REGISTRY',
    defaultValue: false,
    description: 'Push images to registry (auto-determined by branch if not explicitly set)'
)

// Gate in publish/deploy stages
stage('Publish & Package') {
    when { expression { env.SHOULD_PUSH == 'true' } }
    // ...
}
```

**Key Patterns:**
- Regex match `==~` on branch name — covers both `master` and `main` patterns
- `SHOULD_PUSH` is a string `'true'`/`'false'` (Jenkins env vars are always strings)
- Parameter default is `false` — feature branches do NOT push unless explicitly triggered
- Single source of truth: all publish/deploy `when` conditions reference the same env var

---

## Jenkins Retry Patterns

### Exponential Backoff with `executor.retry()`

**Purpose:** Wrap any network-dependent operation so transient failures (registry 503, registry timeouts, proxy errors) recover automatically without requiring a manual re-run.

**Signature:** `executor.retry(logger, maxAttempts, initialDelaySeconds, closure)`

**Formula:** `delay = initialDelay × 2^(attempt-1)`
- Example (15s initial): attempt 1 → 15s, attempt 2 → 30s, attempt 3 → 60s

### Delay Guidelines by Operation Type

| Operation | Attempts | Initial Delay | Rationale |
|-----------|----------|---------------|-----------|
| Registry queries (`manifest inspect`, `imageExists`) | 3 | 5-10s | Quick API call — short delay sufficient |
| Image builds (Docker build, push) | 3 | 15-20s | Large downloads — allow time for recovery |
| Security scans (CVE database downloads) | 3 | 15s | Scan DB downloads are slow to retry |
| Package installs (pip, npm from corporate registry) | 3 | 15s | Registry token endpoint can be slow |
| Downstream job triggers (`build job: ...`) | 3 | 15-20s | Job queue contention needs buffer |

### Common Failure Scenarios Addressed

- Registry returns `503 Service Unavailable` when OAuth token endpoint is overloaded
- Docker registry connection timeouts during manifest queries
- Pip install failures with `ProxyError: Cannot connect to proxy` (registry temporarily down)
- Security scanner CVE database download interruptions
- Base image pull failures during Docker build

### Usage Pattern

```groovy
// Registry query — 3 attempts, 10s initial delay
def imageExists = false
deps.executor.retry(deps.logger, 3, 10) {
    imageExists = module.imageExistsInRegistry(imageName)
}

// Image build — 3 attempts, 15s initial delay
deps.executor.retry(deps.logger, 3, 15) {
    module.buildImage(deps.logger, deps.executor, imageArgs)
}

// Downstream job trigger — 3 attempts, 20s initial delay
deps.executor.retry(deps.logger, 3, 20) {
    build job: 'BuildPython314', wait: true
}
```

PROHIBITED:
```groovy
// WRONG — direct network call without retry
module.imageExistsInRegistry(imageName)       // fails on transient 503
module.buildImage(deps.logger, deps.executor) // fails on base image pull timeout
build job: 'BuildPython314', wait: true       // fails on job queue timeout
```

---

## Jenkins Bash Script Patterns

### Shared Library Structure (`.jenkins/scripts/lib/common.sh`)

**Purpose:** Eliminate duplicated logging, error handling, and validation across all bash scripts in `.jenkins/scripts/`.

**Rules:**
- Location: `.jenkins/scripts/lib/common.sh`
- MUST source library as first action after `set` declarations
- Library MUST contain ONLY generic/reusable functions
- Script-specific logic MUST remain in individual scripts
- NEVER add script-specific functions to the shared library

Generic functions (ALLOWED in lib):
- `log_info()`, `log_warn()`, `log_error()`, `log_debug()`, `log_header()` — structured logging with timestamps
- `setup_error_trap()`, `setup_exit_trap()` — standard error handling
- `require_args()`, `require_command()` — input validation

Utility functions (add only if used in 3+ scripts):
- `ensure_directory()` — only if it adds logging/error handling over `mkdir -p`
- `install_packages()`, `show_version()`, `show_environment()`

Script-specific functions (PROHIBITED in lib — keep in individual scripts):
- `create_build_metadata()` → `build.sh` only
- `push_to_registry()` → `publish.sh` only
- `update_helm_values()` → `update-manifests.sh` only
- `check_argocd_health()` → `wait-for-argocd.sh` only

### Script Structure Pattern

```bash
#!/bin/bash
set -euo pipefail

# Load shared utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

# Script-specific function (local — NOT in lib)
create_build_metadata() {
    local dist_dir=$1
    local build_number=$2
    log_info "Creating build metadata in ${dist_dir}"
    echo "${build_number}" > "${dist_dir}/BUILD_NUMBER"
    echo "$(date -Iseconds)" > "${dist_dir}/BUILD_TIMESTAMP"
    echo "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" > "${dist_dir}/GIT_COMMIT"
}

# Main logic — shared functions for cross-cutting concerns
log_header "Building ${COMPONENT}"
show_environment
install_packages invoke build
create_build_metadata "${DIST_DIR}" "${BUILD_NUMBER}"
```

PROHIBITED:
```bash
#!/bin/bash
# WRONG — duplicated logging, no shared lib
set -euo pipefail
trap 'echo "[$(date)] [ERROR] Failed at line $LINENO" >&2' ERR

echo "[$(date)] [INFO] ========================================"
echo "[$(date)] [INFO] Building component"
echo "[$(date)] [INFO] ========================================"

if ! pip install --no-cache-dir invoke; then
    echo "[$(date)] [ERROR] Failed to install packages" >&2
    exit 1
fi
```
