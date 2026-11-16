# AGENTS.md

AAD-docs is a Django app that reads flat documentation files from `<app>/docs/` and serves them as a visual, bilingual site. The project is in its design phase: the repository holds documentation and a few tools, and no package code until milestone M1a.

## Read first

- [docs/00-map.md](docs/00-map.md): where every document is.
- [docs/PLAN.md](docs/PLAN.md): milestones, roadmap and open decisions.
- [docs/HOW-DOCS-WORK.md](docs/HOW-DOCS-WORK.md): the documentation standard. Follow it for any page you write.
- [aad_docs/docs/07-decisions/](aad_docs/docs/07-decisions/): why things are built this way.

## Checks

Run before every commit and chain it with `&&` before `git push`, so a failed check stops the push:

```bash
tools/setup.sh   # once: installs the dependencies listed in docs/08-operations.md
tools/check.sh   # links, CSV columns, JSON and YAML syntax, and Mermaid diagrams
```

The requirements are listed in [08-operations.md](docs/08-operations.md#agent-tooling). `docs_check` replaces these checks at milestone M4.

## Conventions

- Technical documents, code, comments and commit messages are in English. Spanish pages are `name.es.md` next to the English source.
- Commit messages: `type(area): summary`, with `docs`, `feat`, `fix`, `chore` or `test` as the type.
- One owner per fact: link to the owner instead of copying it. The `06-reference/` tables are written by hand only until their owner exists in code ([0012](aad_docs/docs/07-decisions/0012-reference-tables-from-their-owner.md)).
- Do not edit generated files listed in `.generated.yml`; rerun their command.

## Decisions

A decision page has a `**Status:**` line. Only the owner moves a decision from `Proposed` to `Accepted`: change it when the owner says so, never on your own reading. A verdict the owner saves with Approve in the repository canvas counts as the owner saying so; apply it as the `pending-decisions-canvas` skill describes. Decisions that wait for the owner are listed under "Open decisions" in the plan.

## Skills

Skills live in `.claude/skills/`:

| Skill | Use |
|---|---|
| `repo-docs-canvas` | Publish the repository documentation as one navigable page |
| `pending-decisions-canvas` | Show the decisions that wait for the owner in the warning color on that page |

## Scope

Work only in this repository. Do not publish, share or delete anything outside it unless the owner asks.
