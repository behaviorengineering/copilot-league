---
name: jenkins-bash-scripts
description: 'Bash script structure for CI/CD pipelines. Use when writing .sh scripts under .jenkins/scripts/: common.sh shared library sourcing, script portability, explicit bash invocation from Jenkinsfiles, argument validation, error trapping. Also applies to Python project CI scripts.'
user-invocable: false
---

# Jenkins Bash Scripts

## When to Load

Load when writing or reviewing `.sh` scripts under `.jenkins/scripts/` or any project CI script.

For bash script code templates and patterns, load `.github/agents/references/jenkins-patterns.md` § Jenkins Bash Script Patterns.

## Core Constraints

**CONSTRAINT:** All `.sh` scripts MUST source the shared library at `.jenkins/scripts/lib/common.sh`.

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
```

**CONSTRAINT:** `common.sh` MUST contain ONLY generic/reusable functions — script-specific logic stays in individual scripts.

ALLOWED in `common.sh`:
- `log_info()`, `log_warn()`, `log_error()`, `log_debug()`, `log_header()` — structured logging
- `setup_error_trap()`, `setup_exit_trap()` — error handling
- `require_args()`, `require_command()` — argument and dependency validation

Utility functions (EVALUATE CAREFULLY — only add if they provide real value over direct bash):
- `ensure_directory()` — consider if `mkdir -p` is clearer
- `install_packages()`, `show_version()` — may be too opinionated

PROHIBITED in `common.sh` (keep in individual scripts):
- `create_build_metadata()` → `build.sh` only
- `push_to_registry()` → `publish.sh` only
- `update_helm_values()` → `update-manifests.sh` only
- `check_argocd_health()` → `wait-for-argocd.sh` only
- Any function used by only one script

**CONSTRAINT:** Scripts MUST be portable — runnable on developer machines outside Jenkins.

Verification:
- `bash ./script.sh <args>` on dev machine: PASS
- Script requires Jenkins plugins or Jenkins-specific env vars to run: FAIL
- Script runs identically in CI container and locally: PASS

**CONSTRAINT:** Scripts MUST be invoked from Jenkinsfiles with explicit `bash` — NOT `./script.sh`.

`./script.sh` requires the executable bit to be set in git, which may not persist across clones or in containers.

CORRECT: `sh "bash ./.jenkins/scripts/build.sh ${component} ${buildNumber}"`
PROHIBITED: `sh "./.jenkins/scripts/build.sh ${component} ${buildNumber}"`

**CONSTRAINT:** Scripts MUST validate required arguments before proceeding.

```bash
require_args 3 "$#" "Usage: $0 <component> <build_number> <version>"
COMPONENT="$1"
BUILD_NUMBER="$2"
VERSION="$3"
```

**CONSTRAINT:** All log output MUST use `log_*` functions from `common.sh` — NEVER raw `echo` for structured output.

```bash
log_header "Building ${COMPONENT}"
log_info "Build number: ${BUILD_NUMBER}"
log_info "Version: ${VERSION}"
```

PROHIBITED (duplicated logging setup in every script):
```bash
# WRONG — duplicated in every script
trap 'echo "[$(date)] [ERROR] Failed at line $LINENO" >&2' ERR
echo "[$(date)] [INFO] ========================================"
echo "[$(date)] [INFO] Building component"
```

## Verification Checklist

- [ ] All scripts source `"${SCRIPT_DIR}/lib/common.sh"` at start
- [ ] `common.sh` contains only generic functions (no single-script logic)
- [ ] Scripts runnable with `bash ./script.sh <args>` on developer machine
- [ ] Jenkinsfile invokes scripts with `bash ./path` not `./path`
- [ ] Scripts validate required args at start via `require_args`
- [ ] Log output uses `log_*` functions from `common.sh`
- [ ] No duplicated logging boilerplate across scripts
