---
description: "Use when asked to run Playwright, browse a page, click elements, fill forms, take screenshots, scrape content, or verify UI behaviour in the browser. Covers how to execute Playwright inline scripts using the repo's venv."
---

# Playwright Runner

## Execution environment

Detect the OS before running. Use the appropriate venv Python binary:

**Windows:**
```
cd C:\path\to\post_creator_2\src\orchestrator
C:\path\to\post_creator_2\.venv\Scripts\python.exe -c "<inline script>"
```

Note: PowerShell does not support relative paths (e.g. `..\..\`) as command prefixes — always use the absolute path to the venv Python binary on Windows. Replace `C:\path\to\post_creator_2` with your actual repo root (e.g. use `git rev-parse --show-toplevel` to find it).

**macOS / Linux:**
```
cd /path/to/post_creator_2/src/orchestrator
../../.venv/bin/python -c "<inline script>"
```

To find the repo root on macOS, use `git rev-parse --show-toplevel` if the path is unknown.

Use the bundled Chromium (no `executable_path` needed) and `headless=True` unless the user explicitly asks to see the browser.

## First-time setup (browser binaries)

Playwright needs a separate step to download the Chromium binary. The package install alone is not enough.

**With invoke (submodule present):**
```
invoke env.setup-browsers
```

**Without invoke (manual):**
```bash
# 1. Install dependencies (playwright is already in pyproject.toml)
uv sync

# 2. Download Chromium
playwright install chromium
```

If on a corporate network with SSL inspection, set the cert before step 2.

On a properly configured corporate machine, `SSL_CERT_FILE` is already set as a user env var (from the UV setup guide). Reuse it directly:

- macOS/Linux: `NODE_EXTRA_CA_CERTS=$SSL_CERT_FILE playwright install chromium`
- Windows: `$env:NODE_EXTRA_CA_CERTS = $env:SSL_CERT_FILE; playwright install chromium`

If the user hits SSL errors and `SSL_CERT_FILE` is not set, ask them:
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

If the user's request targets the post_creator app:
1. Check if a dev server is already running on `http://localhost:<port>`
2. If not, ask the user to start it first — do not attempt to start it automatically
