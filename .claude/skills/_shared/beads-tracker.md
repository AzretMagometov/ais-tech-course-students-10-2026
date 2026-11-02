# Reading an existing Wayfinder map

This reference applies only when the user supplies an existing map. Wayfinder is not included in this package.
Use the notes + tech.md input for the four-skill course workflow.

Check `bd --version` and `bd prime` in the target project. Read command flags with `bd <command> --help`.
Do not initialize a database or change a map to generate a PRD.

## Wayfinding operations

A map is an epic labelled `wayfinder:map`. Its description contains the concept and a feature folder line.
Child decision issues contain the questions and recorded answers.

- Read a map: `bd show <map-id> --json`.
- Read a question: `bd show <issue-id> --json`.
- Read its comments: `bd comments <issue-id>`.
- Find closed maps: `bd list -t epic -l wayfinder:map --status closed --flat`.

If the database or map is unavailable, report it. Do not invent decisions from memory.
