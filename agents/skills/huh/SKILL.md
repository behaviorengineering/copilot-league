---
name: huh
description: Reference for charm.land/huh/v2 — Go terminal form library
user-invocable: false
---

# Huh — Terminal Form Library

## When to Load

Load when working with `charm.land/huh/v2` — building interactive terminal forms, prompts, selects, or multi-step wizards in Go.

**Cited by:** `.github/agents/golang-coder.agent.md`

---

## Setup

MUST load `.github/agents/references/environment.md` first. Set `GOPROXY` and `GONOSUMCHECK=*` from that overlay before any `go get` or `go mod download`. NEVER use a public Go proxy in a corporate environment.

Prefer the consuming module's existing `charm.land/huh/v2` dependency. Clone GitHub into `tmp/` only as a fallback when the user asked for the example tree and GitHub is reachable. Do not invent an internal GitHub mirror.

Clone commands below are bash or WSL. On native Windows PowerShell, set GOPROXY then `go get charm.land/huh/v2` in the consuming module — do not assume bash `git clone` works in cmd.exe.

Fallback clone into the workspace tmp directory:

```bash
git clone https://github.com/charmbracelet/huh tmp/huh
cd tmp/huh
go mod download
```

Run the flagship example to verify everything works:

```bash
go run ./examples/burger
```

Other runnable examples:

```bash
go run ./examples/dynamic       # fields that show/hide based on other answers
go run ./examples/conditional   # group navigation based on values
go run ./examples/multiple-groups
go run ./examples/filepicker
go run ./examples/accessibility # screen-reader-friendly mode
```

Run tests:

```bash
go test ./...
go test -run TestResize ./...   # layout/resize tests
```

Debug locally with `dlv`:

```bash
dlv debug ./examples/burger
```

Set accessible mode (no TUI, plain prompts):

```bash
ACCESSIBLE=true go run ./examples/burger
```

---

## Code Navigation

### Core hierarchy

```
Form (form.go)
 └─ Group (group.go)          ← one "page" of fields
     └─ Field (field_*.go)    ← individual input components
```

`Form` drives the Bubble Tea program. `Group` holds fields shown together. Each field is a self-contained Bubble Tea `Model`.

### Key files

| File | Role |
|---|---|
| `form.go` | `Form` type — entry point, state machine (`StateNormal` / `StateCompleted` / `StateAborted`), `Run()` / `RunWithContext()` |
| `group.go` | `Group` type — wraps a `selector.Selector[Field]`, controls navigation between fields on a page, title/description |
| `field_input.go` | `Input` — single-line text, supports `Suggestions`, `Placeholder`, `Validate` |
| `field_text.go` | `Text` — multi-line textarea |
| `field_select.go` | `Select[T]` — filterable list picker; generic over comparable `T` |
| `field_multiselect.go` | `MultiSelect[T]` — multi-pick list with min/max limits |
| `field_confirm.go` | `Confirm` — yes/no boolean prompt |
| `field_note.go` | `Note` — non-interactive display block; use `Next(true)` to add a Continue button |
| `field_filepicker.go` | `FilePicker` — filesystem browser |
| `accessor.go` | `Accessor[T]` interface (`Get`/`Set`); `PointerAccessor[T]` binds field values to external `*T` variables |
| `eval.go` | `Eval[T]` — lazy value wrapper; backs dynamic titles/descriptions/options via `EvalFunc` |
| `theme.go` | `Theme` interface + `Styles` struct; built-in themes: `ThemeCharm`, `ThemeDracula`, `ThemeCatppuccin`, `ThemeBase` |
| `keymap.go` | Key bindings — override with `WithKeyMap` on `Form` or individual fields |
| `validate.go` | Validation helpers — `ValidateMaxLength`, `ValidateMinLength`, `ValidateNotEmpty` |
| `run.go` | `Run*` helpers and accessible-mode renderer |
| `spinner/` | Spinner integration — `spinner.New().Title("loading...").Run()` |
| `internal/selector/` | Cursor/focus management within a group |
| `examples/` | One directory per use-case — read these before any unfamiliar scenario |

### How the state machine works

`Form.Run()` boots a Bubble Tea program. The form moves from group to group via `NextGroup` / `PrevGroup` messages. When the last group completes, state transitions to `StateCompleted`. `ErrUserAborted` is returned when the user presses Escape/Ctrl-C.

### How dynamic fields work

Fields backed by `EvalFunc` re-evaluate their title/description/options/hidden state on every `Update` tick. Read `eval.go` + `field_select.go`'s `OptionsFunc` for the pattern. See `examples/dynamic` for a working demo.

---

## Common Patterns

### Minimal form — bind values via pointer

```go
var name string
var confirm bool

err := huh.NewForm(
    huh.NewGroup(
        huh.NewInput().
            Title("What's your name?").
            Value(&name),

        huh.NewConfirm().
            Title("Are you sure?").
            Value(&confirm),
    ),
).Run()

if errors.Is(err, huh.ErrUserAborted) {
    fmt.Println("cancelled")
    return
}
```

### Select with typed options

```go
type Env string

const (
    Prod    Env = "prod"
    Staging Env = "staging"
    Dev     Env = "dev"
)

var env Env

huh.NewSelect[Env]().
    Title("Target environment").
    Options(
        huh.NewOption("Production", Prod),
        huh.NewOption("Staging", Staging),
        huh.NewOption("Dev", Dev),
    ).
    Value(&env)
```

### Dynamic options (loaded at runtime)

```go
var project string

huh.NewSelect[string]().
    Title("Project").
    OptionsFunc(func() []huh.Option[string] {
        projects, _ := fetchProjects() // called on each render tick
        return huh.NewOptions(projects...)
    }, &project) // second arg is the dependency that triggers re-eval
```

### Validation

```go
huh.NewInput().
    Title("Port").
    Validate(func(s string) error {
        n, err := strconv.Atoi(s)
        if err != nil || n < 1 || n > 65535 {
            return fmt.Errorf("must be 1–65535")
        }
        return nil
    }).
    Value(&port)
```

### Multi-group wizard with note page

```go
huh.NewForm(
    huh.NewGroup(
        huh.NewNote().
            Title("Deploy wizard").
            Description("This will deploy to production.").
            Next(true).
            NextLabel("Continue"),
    ),
    huh.NewGroup(
        huh.NewSelect[string]().Title("Region").Options(...).Value(&region),
        huh.NewConfirm().Title("Enable rollback?").Value(&rollback),
    ),
).Run()
```

### Custom theme

```go
form := huh.NewForm(...).
    WithTheme(huh.ThemeDracula())

// Or build your own:
form.WithTheme(huh.ThemeFunc(func(isDark bool) *huh.Styles {
    s := huh.ThemeCharm().Theme(isDark)
    s.Focused.Title = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("99"))
    return s
}))
```

### Embed in a Bubble Tea app

```go
// Pass WithProgram to hand off key events to the parent program.
// See examples/bubbletea for the full model integration.
form := huh.NewForm(...).WithProgram(p)
```

### Run with timeout

```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

err := form.RunWithContext(ctx)
if errors.Is(err, huh.ErrTimeout) {
    fmt.Println("timed out")
}
```
