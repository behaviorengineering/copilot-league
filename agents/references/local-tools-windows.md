# Local Tools — Windows Setup

Load when a user asks how to set up Python, Go tools, install linters, or run quality checks locally on Windows.

MUST load [environment.md](./environment.md) first. `GOPROXY` below is the shipped placeholder — substitute the Value column when running or generating commands.

## Table of Contents
1. [Go Tools (registry-backed)](#go-tools-registry-backed)
2. [Python via uv](#python-via-uv)
3. [ruff](#ruff)
4. [mypy](#mypy)
5. [Lint Commands](#lint-commands)

---

## Go Tools (registry-backed)

### Prerequisites

Before installing any Go tool, `GOPROXY` and `GONOSUMCHECK` MUST be set. On Windows, `go env -w` persists to the GOENV file.

```powershell
go env -w GOPROXY="<GOPROXY>"
# GONOSUMCHECK cannot be persisted via go env -w — set in session or via Makefile
$env:GONOSUMCHECK = "*"
```

### Makefile Targets (preferred)

Use `make tools` instead of running `go install` manually — it sets `GONOSUMCHECK` correctly in each recipe:

```powershell
make preflight-proxy       # confirm GOPROXY is the corporate registry from environment.md
make artifactory-auth-check  # confirm credentials are valid
make tools                 # installs all 8 tools with GONOSUMCHECK set
```

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

## Python via uv

> Install instructions to be added — see Python + uv setup.

---

## ruff

```powershell
uv tool install ruff
```

Verify: `ruff --version`

---

## mypy

```powershell
uv tool install mypy
```

Verify: `mypy --version`

---

## Lint Commands

```powershell
# Lint
ruff check <file>

# Format check
ruff format --check <file>

# Type check (strict)
mypy --strict <file>
```
