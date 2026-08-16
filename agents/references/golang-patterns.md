# Go Patterns

Load when generating, reviewing, or refactoring any Go (`.go`) file.

## Table of Contents
1. [Go Resource Management Patterns](#go-resource-management-patterns)
2. [Go Error Handling Patterns](#go-error-handling-patterns)
3. [Go Nil Safety Patterns](#go-nil-safety-patterns)
4. [Go Context Patterns](#go-context-patterns)
5. [Go Dependency Injection Patterns](#go-dependency-injection-patterns)
6. [Go Architecture Patterns](#go-architecture-patterns)
7. [Go Interface Design Patterns](#go-interface-design-patterns)
8. [Go SOLID Principles Patterns](#go-solid-principles-patterns)
9. [Go Testing Patterns](#go-testing-patterns)
10. [Go Performance Patterns](#go-performance-patterns)
11. [Go Import Organization](#go-import-organization)

---

## Go Resource Management Patterns

### HTTP response body

```go
resp, err := client.Do(req)
if err != nil {
    return fmt.Errorf("request failed: %w", err)
}
defer resp.Body.Close()

var result MyResponse
if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
    return fmt.Errorf("failed to decode response: %w", err)
}
```

**Rules:**
- MUST call `defer resp.Body.Close()` on the line immediately after the error check
- NEVER read `resp.Body` without a preceding defer close

### Context with timeout

```go
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()

if err := client.SendMessage(ctx, agentID, msgs); err != nil {
    return fmt.Errorf("failed to send message: %w", err)
}
```

**Rules:**
- MUST defer `cancel()` immediately after `WithTimeout`/`WithCancel`/`WithDeadline`
- NEVER create a cancellable context without a deferred cancel

### Database transaction

```go
tx, err := db.Begin(ctx)
if err != nil {
    return fmt.Errorf("failed to begin transaction: %w", err)
}
defer tx.Rollback(ctx) // no-op if Commit succeeds

// ... operations ...

if err := tx.Commit(ctx); err != nil {
    return fmt.Errorf("failed to commit transaction: %w", err)
}
```

**Rules:**
- MUST defer `tx.Rollback(ctx)` immediately after `Begin`
- NEVER begin a transaction without a deferred rollback
- Commit cancels the deferred rollback automatically

### File resource

```go
file, err := os.Open(filePath)
if err != nil {
    return fmt.Errorf("failed to open file: %w", err)
}
defer file.Close()
```

**Rules:**
- MUST defer `Close()` on the line immediately after the error check

---

## Go Error Handling Patterns

### Wrap external error with domain context

```go
resp, err := client.doRequest(ctx, "GET", "/v1/agents", nil)
if err != nil {
    return fmt.Errorf("failed to list agents: %w", err)
}
```

**Rules:**
- MUST wrap with `fmt.Errorf("…: %w", err)` — NEVER return `err` bare from an external call
- Message MUST name the operation that failed

### State persistence error — must be returned

```go
if err := contextService.AddTranslationVersion(ctx, evalContext, version, translation); err != nil {
    logger.WithError(err).Error("Failed to persist evaluation results to shared context.")
    return fmt.Errorf("evaluation succeeded but failed to persist results: %w", err)
}
```

**Rules:**
- MUST return the error — NEVER log-only when persistence fails
- Log the error first for observability, then return it
- Continuing after a persistence failure causes state inconsistency and infinite loops

### Defer cleanup with acceptable log-only

```go
defer func() {
    if err := file.Close(); err != nil {
        logger.WithError(err).Warn("Failed to close file in defer.")
    }
}()
```

**Rules:**
- Log-only is acceptable ONLY inside `defer` blocks where returning is not possible
- NEVER use log-only outside of defer

---

## Go Nil Safety Patterns

### Constructor with nil guards

```go
func NewService(client ClientInterface, logger *logrus.Logger) *Service {
    if client == nil {
        panic("client cannot be nil")
    }
    if logger == nil {
        panic("logger cannot be nil")
    }
    return &Service{client: client, logger: logger}
}
```

**Rules:**
- MUST panic on nil for every required dependency in the constructor
- NEVER defer nil checks to the call site

### Nil pointer check before dereference

```go
func Process(config *Config) error {
    if config == nil {
        return errors.New("config cannot be nil")
    }
    timeout := config.Timeout // safe
    _ = timeout
    return nil
}
```

**Rules:**
- MUST check pointer for nil before any attribute access
- Return an error (not panic) for nil inputs at public API boundaries

---

## Go Context Patterns

### Cancellation check before expensive operation

```go
func Process(ctx context.Context) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    default:
    }
    return client.SendMessage(ctx, agentID, msgs)
}
```

**Rules:**
- MUST check `ctx.Done()` before any expensive or blocking operation
- MUST propagate `ctx` to all callees — NEVER substitute `context.Background()`

### Long-running loop with cancellation

```go
func (s *Service) LongRunningTask(ctx context.Context) error {
    ticker := time.NewTicker(1 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-ticker.C:
            if err := s.doWork(ctx); err != nil {
                return fmt.Errorf("work iteration failed: %w", err)
            }
        }
    }
}
```

**Rules:**
- MUST select on `ctx.Done()` in every loop that may block
- MUST defer `ticker.Stop()` immediately after `NewTicker`

---

## Go Dependency Injection Patterns

### Constructor injection

```go
type Service struct {
    db     DatabaseClient
    logger *logrus.Logger
    cache  Cache[string]
}

func NewService(db DatabaseClient, logger *logrus.Logger, cache Cache[string]) *Service {
    if db == nil {
        panic("db cannot be nil")
    }
    if logger == nil {
        panic("logger cannot be nil")
    }
    return &Service{db: db, logger: logger, cache: cache}
}
```

**Rules:**
- MUST inject ALL dependencies via constructor — NEVER instantiate inside the struct
- MUST use interfaces for all external dependencies (not concrete types)

### Service factory

```go
type ServiceFactory struct {
    dbClient DatabaseClient
    logger   *logrus.Logger
}

func NewServiceFactory(db DatabaseClient, logger *logrus.Logger) *ServiceFactory {
    if db == nil {
        panic("db cannot be nil")
    }
    return &ServiceFactory{dbClient: db, logger: logger}
}

func (f *ServiceFactory) CreateUserService() *UserService {
    return NewUserService(f.dbClient, f.logger)
}

func (f *ServiceFactory) CreateOrderService() *OrderService {
    return NewOrderService(f.dbClient, f.logger)
}
```

**Rules:**
- MUST validate factory dependencies in `NewServiceFactory`, not in each `Create*` method
- Each `Create*` method MUST delegate to the service's own constructor

### Global registry (cross-cutting concerns only)

```go
var (
    Logger   *logrus.Logger
    Config   *config.Config
    DBClient DatabaseClient
)

func InitServices(cfg *config.Config) error {
    Config = cfg
    Logger = observability.InitLoggerFromConfig(cfg.Logging, "")

    var err error
    DBClient, err = database.NewClient(context.Background(), cfg.Database.URL, Logger)
    if err != nil {
        return fmt.Errorf("failed to initialise database: %w", err)
    }
    return nil
}
```

**Rules:**
- Global registry is ONLY for cross-cutting concerns: Logger, Config, DBClient
- MUST initialise in a single `InitServices` function — NEVER scattered across commands
- Initialisation order MUST be: Env → Config → Logger → Database → Services

PROHIBITED:
```go
// WRONG — direct instantiation inside business logic
func (s *Service) ProcessOrder() error {
    db := database.NewClient() // ← bypasses DI
    log := logrus.New()        // ← bypasses DI
}
```

---

## Go Architecture Patterns

### CLI→Service→Client layering

```go
// Layer 1: CLI — delegates only, no business logic.
func (c *Command) Execute(ctx context.Context) error {
    return c.service.SetupAgents(ctx)
}

// Layer 2: Service — business logic, uses injected client.
func (s *Service) SetupAgents(ctx context.Context) error {
    resource, err := s.apiClient.Create(ctx, config)
    if err != nil {
        return fmt.Errorf("failed to create agent resource: %w", err)
    }
    // ... business logic ...
    return nil
}

// Layer 3: Client — external API calls only, in internal/clients/<service>/.
func (c *APIClient) Create(ctx context.Context, cfg AgentConfig) (*Resource, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/v1/agents", body)
    if err != nil {
        return nil, fmt.Errorf("failed to build create request: %w", err)
    }
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("create agent request failed: %w", err)
    }
    defer resp.Body.Close()
    // ...
}
```

**Rules:**
- CLI MUST only call service methods — NEVER contain business logic or HTTP calls
- Services MUST only call injected client interfaces — NEVER call `http` directly
- HTTP calls MUST live exclusively in `internal/clients/<service>/`

### Centralised initialisation

```go
func initConfig() {
    if err := godotenv.Load(); err != nil {
        // continue — .env is optional in production
    }

    cfg, err := config.Load()
    if err != nil {
        Logger = observability.InitDefaultLogger()
        Logger.Warnf("Failed to load configuration: %v", err)
        Config = &config.Config{}
        return
    }

    Config = cfg
    Logger = observability.InitLoggerFromConfig(cfg.Logging, logLevel)
}
```

**Rules:**
- MUST have a single init entry point — NEVER load config/logger in multiple commands
- Initialisation order: Env → Config → Logger → Database → Services

---

## Go Interface Design Patterns

### Segregated repositories (ISP)

```go
type SayingRepository interface {
    Create(ctx context.Context, s *Saying) error
    GetByID(ctx context.Context, id uuid.UUID) (*Saying, error)
    Update(ctx context.Context, s *Saying) error
    Delete(ctx context.Context, id uuid.UUID) error
}

type TranslationRepository interface {
    Create(ctx context.Context, t *Translation) error
    GetByID(ctx context.Context, id uuid.UUID) (*Translation, error)
    Update(ctx context.Context, t *Translation) error
    Delete(ctx context.Context, id uuid.UUID) error
}

// Service depends only on what it uses.
type TranslationService struct {
    sayings      SayingRepository
    translations TranslationRepository
}
```

**Rules:**
- MUST split interfaces by client responsibility — one interface per concern
- Maximum 5–6 methods per interface
- Services MUST declare only the interfaces they actually use

### Generic cache interface

```go
type Cache[T any] interface {
    Get(key string) (T, bool)
    Set(key string, value T) error
    Delete(key string) error
}
```

**Rules:**
- Use generics for reusable infrastructure interfaces
- NEVER use `interface{}` where a type parameter solves the problem

---

## Go SOLID Principles Patterns

### SRP — single responsibility

```go
// WRONG — one struct doing three jobs.
type UserService struct{ db *sql.DB }
func (s *UserService) CreateUser(u *User) error       { /* ... */ }
func (s *UserService) SendWelcomeEmail(u *User) error { /* ... */ }
func (s *UserService) GenerateReport(u *User) error   { /* ... */ }

// CORRECT — each struct has one job.
type UserRepository struct{ db *sql.DB }
func (r *UserRepository) Create(u *User) error        { /* ... */ }

type EmailService struct{ smtp SMTPClient }
func (s *EmailService) SendWelcome(u *User) error     { /* ... */ }

type ReportService struct{ repo *UserRepository }
func (s *ReportService) Generate(u *User) error       { /* ... */ }
```

### OCP — open for extension, closed for modification

```go
// WRONG — adding a payment method requires modifying existing code.
func (p *Processor) Process(kind string, amount float64) error {
    switch kind {
    case "credit":
        return p.processCredit(amount)
    case "paypal":
        return p.processPayPal(amount)
    }
    return errors.New("unsupported")
}

// CORRECT — new processors added without touching existing code.
type PaymentProcessor interface {
    Process(amount float64) error
}

type CreditCardProcessor struct{}
func (p *CreditCardProcessor) Process(amount float64) error { /* ... */ }

type StripeProcessor struct{} // new — zero changes to existing code
func (p *StripeProcessor) Process(amount float64) error     { /* ... */ }
```

### DIP — depend on abstractions

```go
// WRONG — concrete types hard-coded.
type UserService struct {
    db    *sql.DB
    log   *logrus.Logger
    cache *redis.Client
}

// CORRECT — interfaces injected.
type DatabaseClient interface {
    Query(ctx context.Context, sql string, args ...any) ([]Row, error)
}

type UserService struct {
    db     DatabaseClient
    logger *logrus.Logger
    cache  Cache[string]
}

func NewUserService(db DatabaseClient, logger *logrus.Logger, cache Cache[string]) *UserService {
    if db == nil {
        panic("db cannot be nil")
    }
    return &UserService{db: db, logger: logger, cache: cache}
}
```

---

## Go Testing Patterns

### DI-based unit test with mocks

```go
type MockDatabaseClient struct {
    QueryFn func(ctx context.Context, sql string, args ...any) ([]Row, error)
}

func (m *MockDatabaseClient) Query(ctx context.Context, sql string, args ...any) ([]Row, error) {
    return m.QueryFn(ctx, sql, args...)
}

func TestService_ProcessData(t *testing.T) {
    mockDB := &MockDatabaseClient{
        QueryFn: func(ctx context.Context, sql string, args ...any) ([]Row, error) {
            return []Row{{Data: "test"}}, nil
        },
    }
    logger := logrus.New()
    svc := NewService(mockDB, logger)

    err := svc.ProcessData(context.Background(), []byte("test"))
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}
```

**Rules:**
- MUST use injected interfaces so mocks can replace real dependencies
- NEVER call real external services in unit tests
- Test function names MUST follow `Test<Type>_<Method>_<Scenario>` pattern

### Test helpers for setup/teardown

```go
func setupTestDB(t *testing.T) DatabaseClient {
    t.Helper()
    db, err := database.NewTestClient(context.Background())
    if err != nil {
        t.Fatalf("failed to set up test database: %v", err)
    }
    t.Cleanup(func() { db.Close() })
    return db
}
```

**Rules:**
- MUST call `t.Helper()` in all test helper functions
- MUST use `t.Cleanup` instead of `defer` for teardown in helpers

---

## Go Performance Patterns

### Pre-allocated slice

```go
items := make([]Item, 0, len(input)) // ← capacity known upfront
for _, v := range input {
    items = append(items, Item{Value: v})
}
```

**Rules:**
- MUST pre-allocate with `make([]T, 0, n)` when final size is known
- NEVER grow a slice one element at a time when total count is predictable

### Batch fetch instead of N+1

```go
// CORRECT — one query, map for lookup.
agents, err := client.ListAgents(ctx)
if err != nil {
    return fmt.Errorf("failed to list agents: %w", err)
}
agentMap := make(map[string]*Agent, len(agents))
for _, a := range agents {
    agentMap[a.ID] = a
}
for _, id := range agentIDs {
    agent := agentMap[id]
    process(agent)
}
```

PROHIBITED:
```go
// WRONG — N+1: one query per ID
for _, id := range agentIDs {
    agent, _ := client.GetAgent(ctx, id) // ← repeated round-trips
    process(agent)
}
```

### Large struct by pointer

```go
// CORRECT — pointer avoids copying.
func process(s *Saying) { /* ... */ }
```

PROHIBITED:
```go
// WRONG — value copy of large struct
func process(s Saying) { /* ... */ }
```

**Rules:**
- MUST pass structs with 3+ fields by pointer
- MUST return structs with 3+ fields as pointer

### Lazy singleton with sync.Once

```go
var (
    dbClient DatabaseClient
    dbOnce   sync.Once
)

func GetDBClient(ctx context.Context, cfg *config.Config) DatabaseClient {
    dbOnce.Do(func() {
        var err error
        dbClient, err = database.NewClient(ctx, cfg.Database.URL, Logger)
        if err != nil {
            Logger.Fatalf("Failed to connect to database: %v", err)
        }
    })
    return dbClient
}
```

**Rules:**
- Use `sync.Once` only for expensive resources initialised once per process lifetime
- NEVER use `sync.Once` for per-request resources

---

## Go Import Organization

### Standard grouping

```go
import (
    // Standard library.
    "context"
    "fmt"
    "time"

    // Third-party.
    "github.com/google/uuid"
    "github.com/sirupsen/logrus"
    "github.com/spf13/cobra"

    // Internal.
    "myapp/internal/config"
    "myapp/internal/database"
    "myapp/internal/observability"
)
```

**Rules:**
- MUST group imports in order: stdlib → third-party → internal, separated by blank lines
- NEVER mix groups or omit blank line separators
- Run `goimports -w .` or `gofmt -w .` to enforce automatically
- NEVER leave unused imports — run `go mod tidy` after refactoring
