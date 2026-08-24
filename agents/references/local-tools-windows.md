# Local Tools — Windows Setup

Load when a user asks how to set up **Go** tools on Windows, or how `GONOSUMCHECK` works in Windows `cmd` / Makefile recipes.

MUST load [environment.md](./environment.md) first. `GOPROXY` below is the shipped placeholder — substitute the Value column when running or generating commands.

This library does not ship a Makefile. `make tools`, `make preflight-proxy`, and `make registry-auth-check` are **consuming-project** contracts. GOLANG-CODER expects the task repo to provide them.

Python quality MUST use the python-quality container. NEVER install or call ruff, mypy, radon, bandit, or detect-secrets on the Windows host. See [python-quality/SKILL.md](../skills/python-quality/SKILL.md).

## Table of Contents
1. [Go Tools (registry-backed)](#go-tools-registry-backed)
2. [Python quality (container only)](#python-quality-container-only)

---

## Go Tools (registry-backed)

### Prerequisites

Before installing any Go tool, `GOPROXY` and `GONOSUMCHECK` MUST be set. On Windows, `go env -w` persists to the GOENV file.

```powershell
go env -w GOPROXY="<GOPROXY>"
# GONOSUMCHECK cannot be persisted via go env -w — set in session or via Makefile
$env:GONOSUMCHECK = "*"
```

### Makefile Targets (consuming project)

If the consuming project ships these targets, use them instead of running `go install` manually — they set `GONOSUMCHECK` in each recipe:

```powershell
make preflight-proxy       # confirm GOPROXY is the corporate registry from environment.md
make registry-auth-check  # confirm credentials are valid
make tools                 # installs Go tooling with GONOSUMCHECK set
```

This library has no Makefile. Do not invent those targets here.

### Manual Install (Windows cmd/make shell)

POSIX env-prefix syntax (`GONOSUMCHECK=* go install ...`) does NOT work in Windows `cmd` or `make` shells.
MUST use `set "VAR=value" && command` on a single line:

```makefile
# Makefile recipe — Windows
set "GONOSUMCHECK=*" && go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
set "GONOSUMCHECK=*" && go install github.com/securego/gosec/v2/cmd/gosec@latest
set "GONOSUMCHECK=*" && go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
set "GONOSUMCHECK=*" && go install golang.org/x/vuln/cmd/govulncheck@latest
set "GONOSUMCHECK=*" && go install github.com/vektra/mockery/v2@latest
set "GONOSUMCHECK=*" && go install github.com/go-delve/delve/cmd/dlv@latest
set "GONOSUMCHECK=*" && go install github.com/air-verse/air@latest
set "GONOSUMCHECK=*" && go install golang.org/x/tools/gopls@latest
```

```powershell
# PowerShell — set then install
$env:GONOSUMCHECK = "*"
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

Tools land in `%USERPROFILE%\go\bin\`. Add this to PATH, or reference directly in Makefile:
```makefile
GOLANGCI_LINT := "$(USERPROFILE)\go\bin\golangci-lint.exe"
```

PROHIBITED:
```makefile
# WRONG — POSIX env-prefix, fails in Windows cmd/make
GONOSUMCHECK=* go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
```

**Rules:**
- MUST use `set "VAR=value" && command` in Makefile recipes targeting Windows
- MUST NOT assume `golangci-lint` is on PATH in Makefile — use absolute path `$(USERPROFILE)\go\bin\golangci-lint.exe`
- MUST set `GONOSUMCHECK=*` before every `go install` or `go get` in this corporate environment

---

## Python quality (container only)

**CONSTRAINT:** Python lint, format, mypy, radon, bandit, and detect-secrets MUST run inside the python-quality container. NEVER `uv tool install ruff` or `uv tool install mypy` on the Windows host. NEVER call those binaries from PATH.

Load [python-quality/SKILL.md](../skills/python-quality/SKILL.md) and [local-tools-container.md](./local-tools-container.md). Detect `$CONTAINER`, set `$AGENT_TOOLS`, build the image, then:

```powershell
& $CONTAINER run --rm -v "${PWD}:/workspace" python-quality lint --path /workspace/<file>
```
