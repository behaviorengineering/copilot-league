---
name: scout
description: Reference for github.com/felixgeelhaar/scout — Go CDP browser automation library
user-invocable: false
---

# Scout — Browser Automation Library

## When to Load

Load when working with `github.com/felixgeelhaar/scout` — browser automation, web scraping, CDP scripting, the `agent` package (AI-friendly Session API), or the MCP server binary.

**Cited by:** `.github/agents/golang-coder.agent.md`

---

## Setup

MUST load `.github/agents/references/environment.md` first. Set `GOPROXY` and `GONOSUMCHECK=*` from that overlay before any `go get` or `go mod download`. NEVER use a public Go proxy in a corporate environment.

Prefer the consuming module's existing `github.com/felixgeelhaar/scout` dependency. Clone GitHub into `tmp/` only as a fallback when the user asked for the example tree and GitHub is reachable. Do not invent an internal GitHub mirror.

Clone commands below are bash or WSL. On native Windows PowerShell, set GOPROXY then `go get github.com/felixgeelhaar/scout` in the consuming module — do not assume bash `git clone` works in cmd.exe.

Fallback clone into the workspace tmp directory:

```bash
git clone https://github.com/felixgeelhaar/scout tmp/scout
cd tmp/scout
go mod download
```

Build and verify:

```bash
go build ./...
go vet ./...
golangci-lint run --timeout 2m . ./cmd/... ./middleware/... ./internal/...
```

Run tests (Chrome required for integration tests):

```bash
go test -short ./...                               # unit tests only — no Chrome needed
go test ./...                                      # all tests (unit + integration)
go test -run TestIntegration -timeout 120s ./...   # integration suite only
go test -v -race -timeout 300s ./agent/...         # agent package with race detector
```

Run the MCP server:

```bash
go run ./cmd/scout
```

Run the AG-UI conversational browser (requires LLM API key):

```bash
go run ./cmd/scout ui serve --provider=ollama --model=mistral   # local LLM
go run ./cmd/scout ui serve --provider=claude                    # needs ANTHROPIC_API_KEY
cd ui && npm install && npm run dev                               # Vue frontend at :3000
# Corp: set npm registry from environment.md (PACKAGE_REGISTRY_HOST + NPM_VIRTUAL_PATH) before npm install. NEVER registry.npmjs.org.
```

Debug a single integration test with `dlv`:

```bash
dlv test ./... -- -test.run TestIntegrationClick -test.v
```

Enable the eval MCP tool (disabled by default — arbitrary code execution risk):

```bash
SCOUT_ENABLE_EVAL=1 go run ./cmd/scout
```

---

## Code Navigation

### Three API layers

```
browse package (root)          ← Gin-like, developer-facing
 ├─ Engine                     engine.go    — browser lifecycle, task registry
 ├─ Context                    context.go   — per-task state, middleware chain, Set/Get
 ├─ Group                      group.go     — named task collections with shared middleware
 ├─ Page                       page.go      — CDP page wrapper (Navigate, QuerySelector, etc.)
 └─ Selection / SelectionAll   selection.go — DOM element wrappers

agent package                  ← Session-based, AI/structured-output-facing
 └─ Session                    agent/session.go — mutex-safe, JSON-serializable responses

internal/agui package          ← AG-UI protocol HTTP server (scout ui serve)
 └─ SSE + Vue frontend bridge
```

### Key files — browse package

| File | Role |
|---|---|
| `browse.go` | Package doc, `Browser` interface, `New()` / `Default()` constructors, `HandlerFunc` / `HandlersChain` types |
| `engine.go` | `Engine` — `Launch()`, `Task()`, `Run()`, `Use()` (global middleware), `Group()` |
| `context.go` | `Context` — `Next()`, `Abort()`, `Set()`/`Get()`, `GoContext()`, `SaveIndex()`/`RestoreIndex()` for retry replay |
| `group.go` | `Group` — `Task()`, `Use()`, sub-`Group()` with inherited middleware |
| `page.go` | `Page` — `Navigate()`, `QuerySelector()`, `QuerySelectorAll()`, `WaitLoad()`, `WaitForSelector()`, `Close()` |
| `selection.go` | `Selection` — `Click()`, `Input()`, `Text()`, `Attribute()`, `MustClick()` etc. |
| `selection_all.go` | `SelectionAll` — slice of `Selection`, `Each()`, `First()`, `Count()` |
| `lifecycle.go` | Task state machine: `pending → running → success/failed/retrying` using `statekit` |
| `middleware.go` | `Logger()`, `Recovery()` middleware constructors |
| `middleware/` | Resilience middleware: `Retry`, `Timeout`, `CircuitBreaker`, `Bulkhead` |
| `recorder.go` | Action recorder / playbook replay |
| `options.go` | `Option` funcs: `WithHeadless`, `WithRemoteCDP`, `WithAllowPrivateIPs`, `WithProxy` |
| `urlvalidator.go` | Blocks non-http(s) schemes and private IPs by default |
| `errors.go` | Sentinel errors: `ErrAlreadyLaunched`, `ErrPageNotFound`, `ErrSelectorNotFound` |

### Key files — agent package

| File | Role |
|---|---|
| `agent/session.go` | `Session` — mutex-safe wrapper; `Navigate`, `Click`, `Type`, `Observe`, `Screenshot`, `Extract` |
| `agent/selector.go` | `resolveSelector` — Playwright-style (`:text('...')`) → JS lookup; `suggestSelectorsInternal` on failure |
| `agent/history.go` | Ring buffer of last 20 actions, appended on Navigate/Click/Type |
| `agent/readiness.go` | `scoreReadiness()` — 0–100 score (readyState, images, skeletons, spinners) |
| `agent/cookies.go` | Cookie banner dismissal — 30+ CSS selectors + text-pattern fallback |
| `agent/batch.go` | `ExecuteBatch` — acquires mutex once, runs multiple actions sequentially |
| `agent/vision.go` | `HybridObserve` — screenshot + bounding boxes; `FindByCoordinates` hit test |
| `agent/trace.go` | `StartTrace`/`StopTrace` — per-action before/after screenshots exported as zip |
| `agent/screencast.go` | `StartScreenRecording`/`StopScreenRecording` — polled `captureScreenshot` → ffmpeg |
| `agent/nlselect.go` | `SelectByPrompt` — JS fuzzy text matching against interactive elements |
| `agent/iframe.go` | `SwitchToFrame` / `SwitchToMainFrame` via isolated world |
| `agent/vitals.go` | `WebVitals` — LCP/CLS/INP via PerformanceObserver |

### Key internal packages

| Package | Role |
|---|---|
| `internal/cdp/` | Raw CDP WebSocket connection — `Dial`, `CallSessionCtx`, `dispatchEvent` |
| `internal/launcher/` | Chrome process launcher |
| `internal/wait/` | `ForLoad()` / `ForSelector()` polling implementations |

### Critical internal contracts (read before modifying)

- `Page.getRootNodeID()` caches DOM root and is invalidated by `Navigate()` (sets to 0) — halves CDP round-trips.
- `agent.Session` holds `sync.Mutex`; all public methods lock it. Internal helpers (`ensurePage`, `observeInternal`, `pageResult`) are called **with the lock already held** — they must not re-lock.
- Resilience middleware uses `c.SaveIndex()`/`c.RestoreIndex()` to replay the handler chain on retry. `RestoreIndex` clears `errors` and `aborted` but **preserves `keys`** — data set by prior handlers survives retries.
- MCP server uses lazy session creation — browser starts on first tool use, not at startup.

---

## Common Patterns

### Basic browse task (Gin-like API)

```go
engine := browse.Default(browse.WithHeadless(true))
if err := engine.Launch(); err != nil {
    log.Fatal(err)
}
defer engine.Close()

engine.Task("search", func(c *browse.Context) {
    c.MustNavigate("https://example.com")
    c.El("input[name=q]").MustInput("hello world")
    c.El("button[type=submit]").MustClick()
    c.MustWaitLoad()
    fmt.Println(c.El("h3").MustText())
})

if err := engine.Run("search"); err != nil {
    log.Fatal(err)
}
```

### Middleware on a group

```go
engine := browse.New(browse.WithHeadless(true))
engine.MustLaunch()
defer engine.Close()

auth := engine.Group("authenticated", func(c *browse.Context) {
    // runs before every task in this group
    c.MustNavigate("https://example.com/login")
    c.El("#user").MustInput(os.Getenv("USER"))
    c.El("#pass").MustInput(os.Getenv("PASS"))
    c.El("button[type=submit]").MustClick()
    c.Next() // proceed to actual task handler
})

auth.Task("dashboard", func(c *browse.Context) {
    c.MustNavigate("https://example.com/dashboard")
    fmt.Println(c.El(".welcome").MustText())
})
```

### Pass data between middleware and handler via context keys

```go
engine.Use(func(c *browse.Context) {
    c.Set("requestID", uuid.New().String())
    c.Next()
})

engine.Task("work", func(c *browse.Context) {
    id, _ := c.Get("requestID")
    fmt.Println("request:", id)
})
```

### Resilience middleware (retry + timeout)

```go
import "github.com/felixgeelhaar/scout/middleware"

engine.Use(
    middleware.Timeout(10*time.Second),
    middleware.Retry(3, time.Second),
)
```

### Connect to an existing Chrome (remote CDP)

```go
engine := browse.New(browse.WithRemoteCDP("ws://localhost:9222/json"))
engine.MustLaunch()
defer engine.Close()
```

### Agent Session API (AI/structured output)

```go
import "github.com/felixgeelhaar/scout/agent"

sess, err := agent.NewSession(browse.WithHeadless(false))
if err != nil {
    log.Fatal(err)
}
defer sess.Close()

result, err := sess.Navigate("https://example.com")
// result is JSON-serializable with URL, title, status

obs, err := sess.Observe()
// obs.Elements lists interactive elements with selectors and cost hints

err = sess.Click("#submit-button")
extracted, err := sess.Extract("main article")
```

### Agent batch actions (single mutex acquisition)

```go
results, err := sess.ExecuteBatch([]agent.Action{
    {Type: "navigate", Target: "https://example.com"},
    {Type: "click",    Target: "#accept-cookies"},
    {Type: "type",     Target: "#search", Value: "golang"},
})
```

### Natural language element selection

```go
// Falls back from resolveSelector when input looks like natural language.
err = sess.Click("the blue submit button")
```

### Record and replay a playbook

```go
engine.StartRecordingPlaybook("checkout")

engine.Task("checkout", func(c *browse.Context) {
    c.MustNavigate("https://shop.example.com/cart")
    c.El(".checkout-btn").MustClick()
})
engine.Run("checkout")

playbook := engine.StopRecordingPlaybook()
// Save playbook and replay later with engine.RunPlaybook(playbook)
```

### Test middleware without a real browser

```go
called := false
handler := func(c *browse.Context) { called = true }
c := browse.NewTestContext("test-task", browse.HandlersChain{handler})
c.Next()
// assert called == true
```
