# TDD

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_ it does it. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists. These tests survive refactors because they don't care about internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify through external means (like querying a database directly instead of using the interface). Warning sign: your test breaks when you refactor, but behavior hasn't changed. If you rename an internal function and tests fail, those tests were testing implementation.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is "horizontal slicing" — treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior
- Tests become insensitive to real changes — they pass when behavior breaks, fail when behavior is fine
- You outrun your headlights, committing to test structure before understanding the implementation

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat. Each test responds to what you learned from the previous cycle.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

## Cycle: RED → GREEN → REFACTOR

### RED: Write failing test first
- Define exact behavior via test (unit, integration, or e2e)
- Test MUST fail before any implementation code
- Forbidden: writing implementation before test exists

### GREEN: Minimal complete implementation
- Write the minimum code to make tests pass
- No TODOs, no stubs, no `pass`, no `raise NotImplementedError`
- No placeholder comments like `# TODO: implement this`
- No mock implementations that only satisfy tests without real logic
- All edge cases handled — input validation, error states, empty collections

### REFACTOR: Clean without changing behavior
- Run all tests after refactor — must still pass
- Apply architecture principles (see [architecture.md](architecture.md))
- Look at [refactor candidates](refactoring.md): extract duplication, deepen modules (**codebase-design** skill), apply SOLID
- **Never refactor while RED.** Get to GREEN first.

## Planning a TDD Session

Use the project's domain glossary so that test names and interface vocabulary match the project's language; respect ADRs in the area you're touching.

Before writing any code:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm with user which behaviors to test (prioritize)
- [ ] Identify opportunities for deep modules (small interface, deep implementation)
- [ ] Design the interfaces for testability. Use **codebase-design** if available, otherwise the checks in architecture.md
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

**You can't test everything.** Confirm with the user exactly which behaviors matter most. Focus testing effort on critical paths and complex logic, not every possible edge case.

## Test Structure

```
tests/
  unit/        # Pure function logic, no I/O
  integration/ # Module boundaries, real DB/HTTP (test env)
  e2e/         # User-facing flows
```

## Coverage Requirements

- New code: aim for 80%+ branch coverage
- Critical paths (auth, payments, data mutations): 100%
- Run coverage before every commit

## Stack-Specific Tools

| Stack | Test Runner | Coverage |
|-------|-------------|----------|
| Python | pytest | pytest-cov |
| Node/TS | vitest / jest | built-in |
| Go | go test | go tool cover |
| Rust | cargo test | cargo-tarpaulin |

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## Anti-Patterns (never do)

- Writing tests after implementation
- Tests that always pass (no real assertion)
- Tautological tests: the expected value is recomputed the way the code computes it, so the assertion passes whatever the code does (see [tests.md](tests.md))
- Mocking away the thing being tested
- Skipping tests with `.skip` / `@pytest.mark.skip` without a tracked issue
- Horizontal slicing (all tests first, then all implementation)
