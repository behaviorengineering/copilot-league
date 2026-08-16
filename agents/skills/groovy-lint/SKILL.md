---
name: groovy-lint
description: 'Validate .groovy files and Jenkinsfiles locally. Step 1-3: npm-groovy-lint via container (syntax, style). Step 4: Jenkins pipeline-model-converter API (declarative structure). Use when asked to lint or validate any Jenkins pipeline file.'
user-invocable: false
---

# Groovy Lint (Container)

## When to Load

Load when asked to lint `.groovy` files or Jenkinsfiles locally.

MUST load [local-tools-container.md](../../references/local-tools-container.md) first. Run **Runtime Detection** and set `$AGENT_TOOLS` from **Path Prefix** before any container command.

## Scope

| Check | Tool | Catches |
|---|---|---|
| Groovy syntax errors | npm-groovy-lint (Steps 1-3) | Parse errors, undefined variables |
| Style violations | npm-groovy-lint (Steps 1-3) | CodeNarc rules |
| Declarative pipeline structure | Jenkins API (Step 4) | Invalid `pipeline {}` block, wrong directive placement |
| Jenkins DSL step availability | Not available locally | Requires runtime execution |
| CPS serialization errors | Not available locally | Requires runtime execution |

Run Steps 1-3 first. Run Step 4 for any `*.Jenkinsfile` using declarative syntax.

## Step 1 — Check if the Image Exists

Before building, check whether the image is already present:

```powershell
& $CONTAINER images --format "{{.Repository}}" | Select-String "groovy-lint"
```

```bash
$CONTAINER images --format '{{.Repository}}' | grep -F groovy-lint
```

- If output contains `groovy-lint`: skip to [Step 3 — Run the Tool](#step-3--run-the-tool)
- If no output: proceed to Step 2

## Step 2 — Build the Image

The `groovy-lint` image fetches the corporate CA cert from the package registry (no credentials needed for that step),
then installs `npm-groovy-lint` from the corporate npm mirror using BuildKit secrets.

Ensure `REGISTRY_USER` and `REGISTRY_TOKEN` are set in the shell before building.
Pass `--build-arg` values from `agents/references/environment.md` (`.github/agents/references/environment.md` in a consuming project).

```powershell
# PowerShell (Windows)
& $CONTAINER build @TLS_FLAG `
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> `
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> `
    --build-arg NPM_VIRTUAL_PATH=<NPM_VIRTUAL_PATH> `
    --secret id=username,env=REGISTRY_USER `
    --secret id=token,env=REGISTRY_TOKEN `
    -t groovy-lint "$AGENT_TOOLS/groovy-lint"
```
```bash
# bash (macOS / Linux)
$CONTAINER build "${TLS_FLAG[@]}" \
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
    --build-arg NPM_VIRTUAL_PATH=<NPM_VIRTUAL_PATH> \
    --secret id=username,env=REGISTRY_USER \
    --secret id=token,env=REGISTRY_TOKEN \
    -t groovy-lint "$AGENT_TOOLS/groovy-lint"
```

**Rules:**
- MUST run from the repository root (consuming project, or this library when developing it)
- MUST have `REGISTRY_USER` and `REGISTRY_TOKEN` set in the shell
- MUST NOT proceed to Step 3 if the build exits with a non-zero code

## Step 3 — Run the Tool

Run all commands from the repository root. The workspace mounts at `/workspace` inside the container.

**Groovy lint — all stage and library files:**
```powershell
# PowerShell (Windows)
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint `
    --path /workspace/.jenkins --files "**/*.groovy" --no-insight
```
```bash
# bash (macOS / Linux)
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint \
    --path /workspace/.jenkins --files '**/*.groovy' --no-insight
```

**Groovy lint — all Jenkinsfiles:**
```powershell
# PowerShell (Windows)
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint `
    --path /workspace/.jenkins/pipelines --files "**/*.Jenkinsfile" --no-insight
```
```bash
# bash (macOS / Linux)
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint \
    --path /workspace/.jenkins/pipelines --files '**/*.Jenkinsfile' --no-insight
```

**Groovy lint — auto-fix mode:**
```powershell
# PowerShell (Windows)
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint `
    --path /workspace/.jenkins --files "**/*.groovy" --fix --no-insight
```
```bash
# bash (macOS / Linux)
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint \
    --path /workspace/.jenkins --files '**/*.groovy' --fix --no-insight
```

**Rules:**
- MUST pass `--rm` — containers are disposable
- MUST use `/workspace/...` paths in tool arguments — the container sees the repo at `/workspace`
- ALWAYS pass `--no-insight` — suppresses telemetry prompts in non-interactive sessions

## Step 4 — Validate Declarative Pipeline Structure

Uses a local Jenkins container that exposes the `pipeline-model-converter` API. No authentication required — the container runs with the setup wizard disabled.

**Prerequisite — build the image (once):**

Requires internet access to the Jenkins update center for plugin download. Re-run only when the Dockerfile changes.

```powershell
# PowerShell (Windows)
& $CONTAINER build @TLS_FLAG -t jenkins-validator "$AGENT_TOOLS/jenkins-validator"
```
```bash
# bash (macOS / Linux)
$CONTAINER build "${TLS_FLAG[@]}" -t jenkins-validator "$AGENT_TOOLS/jenkins-validator"
```

**Start the container:**

```powershell
# PowerShell (Windows)
& $CONTAINER run -d --rm --name jenkins-validator -p 8080:8080 jenkins-validator

# Wait until /api/json is JSON (the boot splash page is also HTTP 200)
do {
    Start-Sleep -Seconds 3
    try {
        $body = (Invoke-WebRequest http://localhost:8080/api/json -UseBasicParsing).Content
        $ready = $body.TrimStart().StartsWith("{")
    } catch { $ready = $false }
} until ($ready)
Write-Host "Jenkins ready"
```
```bash
# bash (macOS / Linux)
$CONTAINER run -d --rm --name jenkins-validator -p 8080:8080 jenkins-validator
until curl -sf http://localhost:8080/api/json | grep -q '^{'; do sleep 3; done
echo "Jenkins ready"
```

**Validate a Jenkinsfile:**

```powershell
# PowerShell (Windows)
curl.exe -s -X POST http://localhost:8080/pipeline-model-converter/validate `
    -F "jenkinsfile=<.jenkins/pipelines/my-pipeline.Jenkinsfile"
```
```bash
# bash (macOS / Linux)
curl -s -X POST http://localhost:8080/pipeline-model-converter/validate \
    -F "jenkinsfile=<.jenkins/pipelines/my-pipeline.Jenkinsfile"
```

**Stop the container:**

```powershell
& $CONTAINER stop jenkins-validator
```

```bash
$CONTAINER stop jenkins-validator
```

**Rules:**
- MUST wait for Jenkins to be ready before posting — the container starts Jenkins asynchronously
- A valid response contains `"result": "success"` or `Jenkinsfile successfully validated.` — any other response is a structural error
- `curl -F` MUST use `jenkinsfile=<file` (form field contents). `jenkinsfile=@file` uploads a file part and the converter returns `No Jenkinsfile specified`
- Run validate commands from the repository root so file paths resolve correctly
- No `--insecure` needed — the local container uses plain HTTP on localhost
- This step validates structure only — it does NOT check that DSL steps exist in your Jenkins installation

## Fix Protocol — Signature Changes

**CONSTRAINT:** Any lint fix that changes a function or closure signature MUST be followed by a full caller audit before marking the fix complete.

Changing a signature (adding, removing, or renaming a parameter) invalidates every call site. The linter reports the violation on the definition but emits no further signal about stale callers — they fail silently at runtime.

### Caller Audit Steps

1. **Record the change.** State the old and new signature explicitly before touching callers.

   ```
   OLD: def withOperationLogging(logger, config, Closure body)
   NEW: def withOperationLogging(config, Closure body)
   ```

2. **Find all callers.** Search the entire `.jenkins/` tree for every occurrence of the function name.

   ```powershell
   # PowerShell (Windows)
   Get-ChildItem -Path .jenkins -Recurse -Include "*.groovy","*.Jenkinsfile" |
       Select-String -Pattern "withOperationLogging"
   ```
   ```bash
   # bash (macOS / Linux)
   grep -rn "withOperationLogging" .jenkins/
   ```

   Replace `withOperationLogging` with the actual function name that was changed.

3. **Audit each match.** For every call site, compare its argument list against the new signature.

   Candidate: [file path + line]
   Arguments match new signature: YES — proceed / NO — update required
   Decision: PASS | UPDATE

   CORRECT (matches new signature):
   ```groovy
   withOperationLogging(config) { ... }
   ```
   STALE (matches old signature — MUST update):
   ```groovy
   withOperationLogging(logger, config) { ... }  // ← extra arg, MUST remove
   ```

4. **Update all stale callers.** Fix every stale call site in the same commit as the definition change.

5. **Re-run lint.** Run Step 3 again across all modified files. Exit code 0 required before completing.

### Completion Gate

**MUST NOT** mark any signature-change fix complete until:
- [ ] Caller audit executed (Step 2 output reviewed — not skipped)
- [ ] Zero stale callers remain (each call site verified against new signature)
- [ ] Re-lint passes on all modified files (Step 3 exit code 0)

Violation: STOP. Run the caller audit. Update all stale callers. Re-lint.
