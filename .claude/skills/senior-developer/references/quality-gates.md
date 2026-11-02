# Quality Gates

All gates must pass before commit. Fix issues inline — never suppress warnings without justification.

## Python
```bash
ruff check . --fix          # linter + auto-fix
ruff format .               # formatter
mypy .                      # type checking (strict mode preferred)
bandit -r src/              # security scan
pytest --cov=src --cov-report=term-missing
```

## Node / TypeScript
```bash
eslint . --fix
prettier --write .
tsc --noEmit                # type check
npm audit                   # dependency security
vitest run --coverage
```

## Go
```bash
go vet ./...
staticcheck ./...
golangci-lint run
go test ./... -cover
```

## Rust
```bash
cargo clippy -- -D warnings
cargo fmt
cargo audit
cargo test
```

## Universal Rules
- Zero linter errors on commit (warnings allowed only if documented)
- No `any` type in TypeScript without comment explaining why
- No bare `except:` or `catch (e) {}` without logging
- Security scanner must show 0 HIGH/CRITICAL findings
- No TODO / FIXME / XXX comments in committed code — out-of-scope work goes to a separate `bd` issue (see SKILL.md → TDD Cycle)

## CI Integration
Add to pre-commit hooks (`.pre-commit-config.yaml` / husky):
1. Linter
2. Formatter check
3. Type check
4. Tests (fast unit tests only, integration in CI pipeline)
