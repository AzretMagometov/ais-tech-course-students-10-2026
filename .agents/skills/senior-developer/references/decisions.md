# Architectural Decision Records (ADR)

Record every non-obvious architectural or technology decision in `decisions.md` at project root.

## When to Record
Record a decision when:
- Choosing between 2+ viable approaches
- Selecting a library/framework
- Defining API contracts or data models
- Deciding on error handling strategy
- Choosing between trade-offs (consistency vs availability, performance vs readability)

Do NOT record: obvious choices, boilerplate, conventions already in CLAUDE.md.

## ADR Format

One ADR is at most ~15 lines. Each part is 1–3 lines. The rationale goes into Альтернативы as "почему не X". Detail that does not fit belongs in the PRD, the research file or the code.

```markdown
## ADR-NNN: <title>

**Дата:** YYYY-MM-DD · **Статус:** Принято | Заменено ADR-NNN | Устарело

**Контекст.** <the problem and the constraints>

**Решение.** <what we chose>

**Альтернативы.** <X: почему не X>. <Y: почему не Y>.

**Последствия.** <what becomes easier, what becomes harder, risks>
```

Continue the numbering already used in the project (`ADR-NNN` or `D-NNN`).

## Example

```markdown
## ADR-001: PostgreSQL как основная БД

**Дата:** 2025-03-01 · **Статус:** Принято

**Контекст.** Нужно хранилище со сложными запросами и ACID.

**Решение.** PostgreSQL через SQLAlchemy, миграции в Alembic.

**Альтернативы.** MongoDB: слабее гарантии согласованности. MySQL: беднее поддержка JSON.

**Последствия.** Миграции видны в git. Любое изменение схемы требует миграции.
```

## Workflow
1. When facing a significant decision, write the ADR BEFORE implementing
2. Commit `decisions.md` with the related feature commit
3. Reference ADR in code comments where the decision manifests: `# See ADR-001`
4. When a decision is superseded, update status — never delete old ADRs
