# Feature documents: one folder per feature

All documents of one feature live in one folder. Skills that write or read feature documents (`/feature-discovery`, `/create-prd`, `/prd-to-beads`, `/research`, `/wayfinder`) use this layout.

## Layout

```
<root>/<slug>/
  prd.md               # PRD, written by /create-prd
  tasks.md             # task draft, written by /prd-to-beads
  notes.md             # feature understanding, /feature-discovery without a wayfinder map
  tech.md              # technical facts, /feature-discovery without a wayfinder map
  research/<topic>.md  # research findings
  research/<topic>_bench.py  # scripts and benchmarks of that research
  reports/             # generated reports: acceptance runs and similar
```

- **`<root>`**: `docs/features/` by default. A project `CLAUDE.md` can name another features root. Then the folder is `<root>/<slug>/`. In such a project, find the folder by slug with a recursive search under that root.
- **`<slug>`**: kebab-case English, for example `export-csv`. The slug names the folder. File names inside the folder are fixed.

## What goes where

| File | Written by | Read by | Notes |
|------|------------|---------|-------|
| `notes.md` | `/feature-discovery` | `/create-prd` | Its frontmatter `status` tracks the notes + tech pair: `discovery-complete`, `discovery-blocked`, `prd-generated`. |
| `tech.md` | `/feature-discovery` | `/create-prd` | No status of its own. |
| `prd.md` | `/create-prd` | `/prd-to-beads` | |
| `tasks.md` | `/prd-to-beads` (Mode 1) | `/prd-to-beads` (Mode 2) | Keep it after the commit to beads. A Mode 2 re-run reads `committed_ids` from it. |
| `research/<topic>.md` | `/research` | any skill of the feature | Put the scripts and benchmarks of a research next to its findings, named `<topic>_<what>.<ext>`. |
| `reports/` | the skill or script that runs the check | the user | Generated output only. |

`notes.md` and `tech.md` exist only for a feature discovered without a wayfinder map. A feature with a map keeps its decisions in the map.

## Wayfinder maps

The slug of a map is chosen when the map is charted. The map's `## Notes` section records the folder in one line:

```
Папка: docs/features/<slug>/
```

With a project features root, the line names that root: `Папка: <root>/<slug>/`. Skills that work for a map find the feature folder from this line.

## Research outside a feature

Research that belongs to no feature and no map follows the existing convention of the repo.
