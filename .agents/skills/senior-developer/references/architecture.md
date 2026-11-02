# Architecture Principles

## Modular, Independent Architecture

Each module must be:
- **Self-contained**: owns its data, logic, and tests
- **Dependency-injected**: I/O and third-party services are injected, never referenced in place. Everything else follows the seam test below
- **Interface-driven**: communicate through defined contracts (interfaces/protocols/schemas). The contract covers invariants, ordering constraints and error modes, not only the type signature
- **Independently testable**: unit-testable without spinning up the full system

```
src/
  module_a/
    __init__.py
    service.py      # business logic
    repository.py   # data access
    models.py       # data types
    tests/
      test_service.py
      test_repository.py
  module_b/
    ...
```

## Module Design

The **codebase-design** skill holds the vocabulary and the design method: module, interface, depth, seam, adapter. Use it if available. Otherwise apply the module checks below without requiring another skill.

Two checks apply whenever you split or merge modules:

- **Deletion test**: a module you cannot delete in one piece is not a module. Delete it mentally. Complexity vanishes → the module was a pass-through. Complexity reappears across its callers → it earned its keep.
- **Seam test**: one adapter is a hypothetical seam, two adapters is a real one. Add a port only when something varies across it. Production plus a test stand-in counts as two. A single-adapter seam is indirection.

## Environment Separation

**Always maintain two environments:**

| Aspect | Test/Dev | Production |
|--------|----------|------------|
| Config | `.env.test` / `.env.dev` | `.env.prod` / secrets manager |
| Database | Local/docker, ephemeral | Managed, persistent |
| External APIs | Mocked / sandbox endpoints | Real endpoints |
| Logging | DEBUG level, verbose | WARN/ERROR only |
| Migrations | Applied automatically in test | Manual approval |

**Rules:**
- Never hardcode environment-specific values — use env vars
- Test environment must be resettable to known state before each test suite
- Production config never in codebase — use secrets manager (Vault, AWS SSM, etc.)
- Feature flags for gradual rollout

## Dependency Management — Latest Compatible Versions

Before adding any library:
1. Read official documentation for the relevant version; use Context7 MCP if available.
2. Check latest version: `pip3 index versions <pkg>` / `npm view <pkg> versions`
3. Verify compatibility with existing stack
4. Pin to exact version in lock file (`poetry.lock`, `package-lock.json`, `Cargo.lock`)

**Update policy:** Dependencies updated when:
- Security vulnerability found (immediate)
- New project started (use latest)
- Major feature needed (targeted upgrade)

## SOLID in Practice

YAGNI beats foresight: a seam nothing varies across is indirection, not extensibility. Add the abstraction when the second variant arrives, not in anticipation of it.

- **S**: One reason to change per class/module
- **O**: With one case, edit the existing code. A second variant appears → extend instead of branching
- **L**: Subclasses honor parent contracts
- **I**: Small, focused interfaces over large ones
- **D**: Inject a dependency that passes the seam test above. I/O (database, HTTP, third-party service) always passes it: production adapter plus test stand-in. An in-process helper does not. Call it directly
