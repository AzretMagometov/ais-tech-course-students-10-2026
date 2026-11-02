# Commits & Task Decomposition

## Conventional Commits Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Adding/updating tests |
| `refactor` | Code change without feature/fix |
| `chore` | Build, deps, config |
| `docs` | Documentation only |
| `perf` | Performance improvement |
| `ci` | CI/CD changes |

**Rules:**
- Description: imperative mood, lowercase, no period, max 72 chars
- Scope: module/component name (optional but preferred)
- Breaking changes: add `!` after type, `BREAKING CHANGE:` in footer
- Each commit must pass all quality gates (tests + linters)

**Examples:**
```
feat(auth): add JWT refresh token rotation
fix(api): handle empty response from upstream service
test(cart): add edge cases for zero-quantity items
chore(deps): upgrade fastapi to 0.115.0
```

## Task Decomposition
Before coding, decompose into atomic tasks:

1. **Understand** — read requirements, ask clarifying questions if ambiguous
2. **Design** — sketch API/data model, record decision if non-obvious (see decisions.md)
3. **Test setup** — write failing tests per module
4. **Implement** — one module at a time, commit after each passing test suite
5. **Integration** — wire modules, add integration tests
6. **Quality gate** — run all linters, full test suite
7. **Commit** — one logical change per commit

**Granularity:** Each commit should represent one logical change that can be reviewed independently. If commit message needs "and", split it.

## Using beads for tracking
```bash
bd create              # create task before starting
bd update <id> --status in_progress  # claim task
bd close <id>          # after the commit, from the subagent session (worktrees share the database)
```
