---
name: python-quality
description: 'Run local Python quality audits via the python-quality container: ruff, mypy, radon, bandit, detect-secrets. Use when linting, formatting, or security-scanning Python during coding. Does not run Jenkins CI.'
user-invocable: false
---

# Python Quality (Container)

## When to Load

Load when asked to lint, format, type-check, or security-scan Python locally.

**Cited by:** `.github/agents/python-coder.agent.md`

MUST load [local-tools-container.md](../../references/local-tools-container.md) first. Run **Runtime Detection** and set `$AGENT_TOOLS` from **Path Prefix** before any container command.

This image is **not** `FROM local-agent-tool-base`. Public and corp both start from `python:3.12-bookworm`. Do not build the base first for python-quality.

This skill is a **quality audit**. NEVER start Jenkins. NEVER run `invoke ci.*`. NEVER clone jenkins-python-ci.

## Scope

| Check | Task | Tool |
|---|---|---|
| Lint + types | `lint` | ruff check, ruff format `--check`, mypy `--strict`, radon |
| Auto-fix | `format` | ruff check `--fix`, ruff format |
| Code security | `sec.code` | bandit (fail on HIGH/MEDIUM) |
| Secrets | `sec.secrets` | detect-secrets |

Jenkins pipelines may run the same tools. That is out of scope here.

## Step 1 — Check if the Image Exists

```powershell
& $CONTAINER images --format "{{.Repository}}" | Select-String "python-quality"
```

```bash
$CONTAINER images --format '{{.Repository}}' | grep -F python-quality
```

- If output contains `python-quality`: skip to [Step 3 — Run the Tool](#step-3--run-the-tool)
- If no output: proceed to Step 2

## Step 2 — Build the Image

Pass `--build-arg` values from `.github/agents/references/environment.md` (drop `.github/` in this library).

**Public** (GitHub CI, public PyPI — no secrets):

```powershell
& $CONTAINER build @TLS_FLAG --target public -t python-quality "$AGENT_TOOLS/python-quality"
```

```bash
$CONTAINER build "${TLS_FLAG[@]}" --target public -t python-quality "$AGENT_TOOLS/python-quality"
```

**Corp** (default last stage). Ensure `REGISTRY_USER` and `REGISTRY_TOKEN` are set.

```powershell
# PowerShell (Windows)
& $CONTAINER build @TLS_FLAG `
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> `
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> `
    --build-arg PIP_INDEX_PATH=<PIP_INDEX_PATH> `
    --secret id=username,env=REGISTRY_USER `
    --secret id=token,env=REGISTRY_TOKEN `
    -t python-quality "$AGENT_TOOLS/python-quality"
```

```bash
# bash (macOS / Linux)
$CONTAINER build "${TLS_FLAG[@]}" \
    --build-arg PACKAGE_REGISTRY_HOST=<PACKAGE_REGISTRY_HOST> \
    --build-arg CORP_CA_CERT_URL=<CORP_CA_CERT_URL> \
    --build-arg PIP_INDEX_PATH=<PIP_INDEX_PATH> \
    --secret id=username,env=REGISTRY_USER \
    --secret id=token,env=REGISTRY_TOKEN \
    -t python-quality "$AGENT_TOOLS/python-quality"
```

**Rules:**
- MUST run from the repository root
- Corp MUST have `REGISTRY_USER` and `REGISTRY_TOKEN` set. Public (`--target public`) does not.
- MUST NOT proceed to Step 3 if the build exits non-zero
- NEVER build `local-agent-tool-base` for this image

## Step 3 — Run the Tool

Run from the repository root. The workspace mounts at `/workspace`. Tool `--path` arguments MUST use `/workspace/...` or a path relative to `/workspace`.

Project-root `ruff.toml` / `mypy.ini` override image defaults when present.

**Lint (ruff + mypy + radon):**
```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" python-quality lint --path /workspace/<file>
```
```bash
$CONTAINER run --rm -v "$(pwd):/workspace" python-quality lint --path /workspace/<file>
```

**Format (auto-fix):**
```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" python-quality format --path /workspace/<file>
```
```bash
$CONTAINER run --rm -v "$(pwd):/workspace" python-quality format --path /workspace/<file>
```

**Bandit:**
```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" python-quality sec.code --path /workspace/<file>
```
```bash
$CONTAINER run --rm -v "$(pwd):/workspace" python-quality sec.code --path /workspace/<file>
```

**detect-secrets:**
```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" python-quality sec.secrets --path /workspace/<file>
```
```bash
$CONTAINER run --rm -v "$(pwd):/workspace" python-quality sec.secrets --path /workspace/<file>
```

**Rules:**
- MUST pass `--rm`
- MUST mount the workspace as `/workspace`
- MUST use the container — NEVER call ruff, mypy, radon, bandit, or detect-secrets on the host
- NEVER run pytest, `sec.deps`, or Jenkins from this skill
