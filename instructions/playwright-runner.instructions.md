---
applyTo: "**/*playwright*,**/e2e/**,**/*.spec.ts"
description: "Use when asked to run Playwright, browse a page, click elements, fill forms, take screenshots, scrape content, or verify UI behaviour in the browser. Covers inline Python Playwright scripts using the consuming project's .venv."
---

# Playwright Runner

## Execution environment

Resolve the repo root, then use that project's `.venv` Python. Do not hardcode a project path.

```bash
ROOT=$(git rev-parse --show-toplevel)
```

**Windows (PowerShell):**
```powershell
$root = (git rev-parse --show-toplevel)
& "$root\.venv\Scripts\python.exe" -c "<inline script>"
```

PowerShell does not support relative paths (e.g. `..\..\`) as command prefixes — always use the absolute path to the venv Python binary on Windows.

**macOS / Linux:**
```bash
ROOT=$(git rev-parse --show-toplevel)
"$ROOT/.venv/bin/python" -c "<inline script>"
```

Use the bundled Chromium (no `executable_path` needed) and `headless=True` unless the user explicitly asks to see the browser.

If `.venv` is missing, STOP and ask the user to create it. Do not invent a second Python.

## First-time setup (browser binaries)

Playwright needs a separate step to download the Chromium binary. The package install alone is not enough.

```bash
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
# playwright is a project dependency — install it the way the consuming project already does
"$ROOT/.venv/bin/playwright" install chromium
```

Windows:

```powershell
$root = (git rev-parse --show-toplevel)
& "$root\.venv\Scripts\playwright.exe" install chromium
```

If on a corporate network with SSL inspection, fetch the CA then install Chromium.

Load `.github/agents/references/environment.md` (drop `.github/` in this library). Substitute `CORP_CA_CERT_URL`. If `SSL_CERT_FILE` is already set in the user environment, reuse it as `NODE_EXTRA_CA_CERTS` instead of downloading.

**macOS / Linux:**
```bash
ROOT=$(git rev-parse --show-toplevel)
curl --insecure -o /tmp/corp-ca.pem "$CORP_CA_CERT_URL"
export NODE_EXTRA_CA_CERTS=/tmp/corp-ca.pem
"$ROOT/.venv/bin/playwright" install chromium
```

**Windows (PowerShell):**
```powershell
$root = (git rev-parse --show-toplevel)
$pem = Join-Path $env:TEMP "corp-ca.pem"
Invoke-WebRequest -SkipCertificateCheck -Uri $env:CORP_CA_CERT_URL -OutFile $pem
$env:NODE_EXTRA_CA_CERTS = $pem
& "$root\.venv\Scripts\playwright.exe" install chromium
```

If the user hits SSL errors and `CORP_CA_CERT_URL` / `SSL_CERT_FILE` are unset, ask them:
> "What is the path to your corporate SSL certificate file (e.g. `.pem` or `.crt`)?"

Then use that path as the value for `NODE_EXTRA_CA_CERTS`. This is not a secret — it is a file path and safe to handle in the terminal.

This is a one-time step per machine. The binary lands in `~/.cache/ms-playwright/` (macOS/Linux) or `%LOCALAPPDATA%\ms-playwright\` (Windows).

## Script skeleton

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # --- task goes here ---

    browser.close()
```

## Translating user commands

| User says | Playwright action |
|-----------|------------------|
| "go to URL" | `page.goto(url, timeout=60000)` |
| "click X" | `page.click(selector)` |
| "fill field X with Y" | `page.fill(selector, value)` |
| "tell me what's on the page" | `print(page.title(), page.content())` |
| "take a screenshot" | `page.screenshot(path="screenshot.png")` |
| "wait for X to appear" | `page.wait_for_selector(selector)` |
| "new tab opened" | wrap click in `context.expect_page()` |
| "tell me the text of X" | `print(page.inner_text(selector))` |

## Reporting results

Always `print()` results so they appear in terminal output. Return:
- page title and URL after navigation
- element text / values when inspecting content
- screenshot file path when capturing

## Local app

If the request targets a local dev server:
1. Check if a server is already running on the URL the user named
2. If not, ask the user to start it first — do not start it automatically
