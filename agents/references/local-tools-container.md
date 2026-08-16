# Container Tool Runner

Load when an agent needs to run a dev tool (linter, formatter, validator) via container instead of a native install.

MUST load [environment.md](./environment.md) first. Pass its Value column as `--build-arg`. Dockerfiles have no ARG defaults for registry host or path.

## Table of Contents
1. [Runtime Detection](#runtime-detection)
2. [Path Prefix](#path-prefix)
3. [Prerequisites](#prerequisites)
4. [Directory Layout](#directory-layout)
5. [Corporate Base Image](#corporate-base-image)
6. [Pull a Public Image](#pull-a-public-image)
7. [Build a Custom Image](#build-a-custom-image)
8. [Run a Tool Against the Workspace](#run-a-tool-against-the-workspace)
9. [Rules](#rules)

---

## Runtime Detection

**Probe the daemon before any container command.** Prefer **Podman**. Fall back to **Docker** when Podman is missing or not running.

`command -v` and `Get-Command` only prove the binary exists. `info` proves the engine is up.

```powershell
# PowerShell (Windows)
$CONTAINER = $null
if (Get-Command podman -ErrorAction SilentlyContinue) {
    podman info *>$null
    if ($LASTEXITCODE -eq 0) { $CONTAINER = "podman" }
}
if (-not $CONTAINER -and (Get-Command docker -ErrorAction SilentlyContinue)) {
    docker info *>$null
    if ($LASTEXITCODE -eq 0) { $CONTAINER = "docker" }
}
if (-not $CONTAINER) {
    throw "Neither Podman nor Docker is running. Start Podman Desktop or Docker Desktop."
}
$TLS_FLAG = @()
if ($CONTAINER -eq "podman") { $TLS_FLAG = @("--tls-verify=false") }
```

```bash
# bash (macOS / Linux)
if podman info >/dev/null 2>&1; then
  CONTAINER=podman
elif docker info >/dev/null 2>&1; then
  CONTAINER=docker
else
  echo "Neither Podman nor Docker is running. Start Podman Desktop or Docker Desktop." >&2
  exit 1
fi
TLS_FLAG=()
if [ "$CONTAINER" = podman ]; then
  TLS_FLAG=(--tls-verify=false)
fi
```

All later commands in this file use `$CONTAINER` and `$TLS_FLAG` from this step.

**Rules:**
- MUST run detection before `pull`, `build`, `run`, `images`, `inspect`, or `stop`
- MUST prefer Podman when `podman info` succeeds
- MUST fall back to Docker when Podman is absent or its daemon is down
- MUST pass `--tls-verify=false` only when the runtime is Podman
- NEVER pass `--tls-verify=false` to Docker. Docker rejects that flag
- NEVER treat a binary on PATH as a running engine
- NEVER hardcode `podman` or `docker` in a command after detection has set `$CONTAINER`

PROHIBITED:
```powershell
# WRONG — skips detection; fails on machines with Docker only
podman build --tls-verify=false -t groovy-lint "$AGENT_TOOLS/groovy-lint"
```

```powershell
# WRONG — Docker does not accept --tls-verify
docker build --tls-verify=false -t groovy-lint "$AGENT_TOOLS/groovy-lint"
```

---

## Path Prefix

Tool Dockerfiles live under `agent-tools/` **inside this library**. The path from your shell depends on where you are working.

| Working directory | `$AGENT_TOOLS` value |
|---|---|
| Consuming project root (library is the `.github` submodule) | `.github/agent-tools` |
| This library's repository root (developing the library) | `agent-tools` |

```powershell
# PowerShell — consuming project (default in agent docs)
$AGENT_TOOLS = ".github/agent-tools"
# Library repo: $AGENT_TOOLS = "agent-tools"
```

```bash
# bash — consuming project (default in agent docs)
AGENT_TOOLS=.github/agent-tools
# Library repo: AGENT_TOOLS=agent-tools
```

**Rules:**
- MUST set `$AGENT_TOOLS` before any `build` that points at a Dockerfile under `agent-tools/`
- MUST use `$AGENT_TOOLS/<tool>` in build paths — NEVER hardcode only one of the two prefixes
- Agent references that say `.github/agents/...` assume the consuming-project layout. When editing this library, drop the `.github/` prefix

---

## Prerequisites

**Podman Desktop** or **Docker Desktop** must be installed. The engine chosen in [Runtime Detection](#runtime-detection) must be running.

Verify: the detection snippet above sets `$CONTAINER` without throwing or exiting.

---

## Directory Layout

Each tool is a subdirectory of `$AGENT_TOOLS`:

```
agent-tools/                 # library root; at .github/agent-tools/ in a consuming project
    base/
        Dockerfile          # Corp-only base — certs, apt mirror. No public stage.
    groovy-lint/
        Dockerfile          # public + corp on node:lts-slim (not FROM base)
    jenkins-validator/
        Dockerfile          # Hub jenkins/jenkins:lts-jdk17 — needs updates.jenkins.io
    python-quality/
        Dockerfile          # public + corp on python:3.12-bookworm (not FROM base)
```

Which images need `local-agent-tool-base`:

| Image | Public (`--target public`) | Corp (default last stage) |
|---|---|---|
| `python-quality` | No — `python:3.12-bookworm` | No — `python:3.12-bookworm` + CA + corp pip |
| `groovy-lint` | No — `node:lts-slim` | No — `node:lts-slim` + corp apt/npm |
| `jenkins-validator` | Single stage, Hub Jenkins | No corp stage |
| `base` | No public stage | This image |

**Rules:**
- No current tool image waits on `local-agent-tool-base`. python-quality corp and groovy-lint corp each fetch the CA themselves. Keep building and smoking the base image as the CA/apt primitive for future debian-based tools.
- MUST name the base image `local-agent-tool-base` when you build it.
- MUST fetch certs inside the image that needs them. NEVER copy cert files into the build context.
- jenkins-validator pulls `jenkins/jenkins:lts-jdk17` and downloads plugins from `updates.jenkins.io`. It has no corp stage. A network that blocks Hub or the update center cannot build or boot it.

---

## Corporate Base Image

The base image fetches corporate CA certs from the package registry and replaces default apt sources with the internal mirror. No current tool image builds `FROM local-agent-tool-base`. python-quality corp and groovy-lint corp start from `python:3.12-bookworm` / `node:lts-slim` and apply the CA bootstrap themselves. jenkins-validator does not use this base.

GitHub Actions corp smokes use Artifactory-shaped path placeholders from this library's `environment.md`. Nexus orgs still pass `--build-arg` from their filled `environment.md` — CI does not ship a Nexus Caddy double.

MUST load `environment.md` and pass its values as `--build-arg`. Dockerfiles have no ARG defaults for registry host or path — those shapes are vendor-specific (Artifactory vs Nexus). A Nexus org MUST pass Nexus Values (`PACKAGE_REGISTRY_HOST`, `DEBIAN_REPO_PATH` = `repository/<repo>`).

**`$AGENT_TOOLS/base/Dockerfile`:**
```dockerfile
ARG BASE_IMAGE=debian:bookworm-slim
FROM ${BASE_IMAGE}

ARG PACKAGE_REGISTRY_HOST
ARG CORP_CA_CERT_URL
ARG DEBIAN_REPO_PATH

# Step 1: Fetch corporate CA cert from the package registry
# --insecure is required here because the cert is not yet trusted by the image
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl --insecure -o /usr/local/share/ca-certificates/corp-ca.crt \
       "${CORP_CA_CERT_URL}" \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Replace default Debian apt sources with the corporate apt mirror
RUN rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources \
    && echo "# Disabled — using corporate apt mirror" > /etc/apt/sources.list

# Step 3: Install packages from the corporate apt mirror.
# Credentials are in the deb URL. sources.list is created and deleted in the same RUN,
# so the token never persists in a layer. Token value comes only from --mount=type=secret.
RUN --mount=type=secret,id=username \
    --mount=type=secret,id=token \
    USERNAME=$(cat /run/secrets/username | cut -d@ -f1) && \
    TOKEN=$(cat /run/secrets/token) && \
    echo "deb https://${USERNAME}:${TOKEN}@${PACKAGE_REGISTRY_HOST}/${DEBIAN_REPO_PATH} bookworm main" \
        > /etc/apt/sources.list.d/registry.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ make git \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/apt/sources.list.d/registry.list

# Step 4: Set CA bundle env vars for runtime tool use
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

Build the base image, passing credentials as secrets and org values as build-args from `environment.md`:
```powershell
# PowerShell (Windows)
& $CONTAINER build @TLS_FLAG `
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> `
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> `
    --build-arg DEBIAN_REPO_PATH=<DEBIAN_REPO_PATH> `
    --secret id=username,env=REGISTRY_USER `
    --secret id=token,env=REGISTRY_TOKEN `
    -t local-agent-tool-base "$AGENT_TOOLS/base"
```

```bash
# bash (macOS / Linux)
$CONTAINER build "${TLS_FLAG[@]}" \
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
    --build-arg DEBIAN_REPO_PATH=<DEBIAN_REPO_PATH> \
    --secret id=username,env=REGISTRY_USER \
    --secret id=token,env=REGISTRY_TOKEN \
    -t local-agent-tool-base "$AGENT_TOOLS/base"
```

**Rules:**
- MUST use `--mount=type=secret` for registry credentials — NEVER pass them as `ARG` or `ENV` (secrets baked into ARG/ENV appear in `$CONTAINER inspect` and image history)
- MUST use `curl --insecure` for the initial cert fetch only — certs are not yet trusted at that point
- MUST put secrets in the deb URL only inside the same RUN that deletes `registry.list` — they MUST NOT persist in the image layer
- After the CA is in the trust store, later apt MUST verify TLS
- MUST rebuild `local-agent-tool-base` whenever the cert URL changes, then rebuild any image that still uses it
- Replace all `<placeholder>` values with actual values for the environment before use

---

## Pull a Public Image

```powershell
& $CONTAINER pull @TLS_FLAG <image>:<tag>
```

**Rules:**
- MUST include `$TLS_FLAG` on pull. It is `--tls-verify=false` for Podman and empty for Docker
- MUST specify a tag — NEVER pull `latest` for tool images used in reproducible workflows

Example:
```powershell
& $CONTAINER pull @TLS_FLAG node:lts-slim
```

---

## Build a Custom Image

```powershell
& $CONTAINER build @TLS_FLAG -t <image-name> <dockerfile-dir>
```

**Rules:**
- MUST include `$TLS_FLAG` on build. Base image pulls during build go through the same proxy
- MUST tag with a descriptive name (`groovy-lint`, `ruff`, etc.) — not a generic name
- Build runs once; re-run only when the Dockerfile changes

Example (public groovy-lint, no secrets). Corp build: copy the exact command from [groovy-lint/SKILL.md](../skills/groovy-lint/SKILL.md) (build-args + BuildKit secrets).
```powershell
& $CONTAINER build @TLS_FLAG --target public -t groovy-lint "$AGENT_TOOLS/groovy-lint"
```

---

## Run a Tool Against the Workspace

```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" <image-name> [tool args]
```

**Rules:**
- MUST pass `--rm` — containers are disposable; NEVER leave them running after the command exits
- MUST mount the workspace as `/workspace` — tool path arguments MUST use `/workspace/...`
- MUST run from the repository root so `${PWD}` resolves to the project directory

Example:
```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" groovy-lint --path /workspace/.jenkins --files "**/*.groovy"
```

---

## Rules

- MUST detect the runtime before any container command. Prefer Podman, fall back to Docker
- MUST set `$AGENT_TOOLS` for the current working directory (see [Path Prefix](#path-prefix))
- MUST pass `--tls-verify=false` only for Podman pull and build. NEVER pass it to Docker
- NEVER install tools natively if a container alternative exists — containers are OS-agnostic and require no PATH management
- MUST rebuild the image when the Dockerfile changes — stale images silently run old tool versions
