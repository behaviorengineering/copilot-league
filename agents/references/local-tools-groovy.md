# Groovy Local Tools — Container Setup

Load when a user asks how to set up local Groovy linting, run npm-groovy-lint, or validate Jenkinsfiles locally.

MUST load [local-tools-container.md](./local-tools-container.md) first. Run **Runtime Detection** and set `$AGENT_TOOLS` from **Path Prefix** before any container command. MUST load [environment.md](./environment.md) and pass its values as `--build-arg` when building the image.

## Table of Contents
- [Groovy Local Tools — Container Setup](#groovy-local-tools--container-setup)
  - [Table of Contents](#table-of-contents)
  - [Dockerfile](#dockerfile)
  - [Build the Image](#build-the-image)
  - [Lint Commands](#lint-commands)

---

## Dockerfile

Place this file at `agent-tools/groovy-lint/Dockerfile` in this library (`$AGENT_TOOLS/groovy-lint/Dockerfile` from the shell).

```dockerfile
FROM local-agent-tool-base
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm default-jdk \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g npm-groovy-lint
ENTRYPOINT ["npm-groovy-lint"]
```

**Rules:**
- `local-agent-tool-base` MUST be built first — see `local-tools-container.md` for base image setup
- `local-agent-tool-base` provides the corporate certs, proxy env vars, and apt mirror — NEVER duplicate those here
- `default-jdk` is required — npm-groovy-lint calls a JVM internally via the CodeNarc analyzer
- `nodejs` and `npm` install from the corporate apt mirror configured in `local-agent-tool-base`
- NEVER use an Alpine base for this image — `default-jdk` is not available in Alpine's package index

---

## Build the Image

Run once from the repository root. Re-run only when the Dockerfile changes.

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

Verify: `$CONTAINER images` shows `groovy-lint` in the list.

---

## Lint Commands

Run all commands from the repository root.

```powershell
# PowerShell (Windows)

# Lint all stage and library files
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint --path /workspace/.jenkins --files "**/*.groovy" --no-insight

# Lint all Jenkinsfiles
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint --path /workspace/.jenkins/pipelines --files "**/*.Jenkinsfile" --no-insight

# Auto-fix mode (apply safe fixes)
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint --path /workspace/.jenkins --files "**/*.groovy" --fix --no-insight
```

```bash
# bash (macOS / Linux)

# Lint all stage and library files
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint --path /workspace/.jenkins --files '**/*.groovy' --no-insight

# Lint all Jenkinsfiles
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint --path /workspace/.jenkins/pipelines --files '**/*.Jenkinsfile' --no-insight

# Auto-fix mode (apply safe fixes)
$CONTAINER run --rm -v "$(pwd):/workspace" groovy-lint --path /workspace/.jenkins --files '**/*.groovy' --fix --no-insight
```

**Rules:**
- ALWAYS pass `--no-insight` to suppress telemetry prompts in non-interactive sessions
- MUST run from repository root — `${PWD}` (PowerShell) or `$(pwd)` (bash) must resolve to the project root
- MUST use `/workspace/...` paths in tool arguments — the container sees the repo at `/workspace`
