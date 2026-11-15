# Changelog

## Unreleased

- Added the project plan (`docs/PLAN.md`).
- Added the technical documentation, written in the AAD-docs standard: root node in `docs/`, app node in `aad_docs/docs/`.
- Added the recommendation to combine the file-based documentation with django-tree-queries in a future delivery (plan M6, decision 0009).
- Added the address scheme: every app, page and model gets an address under `/docs/` taken from its metadata (architecture, decision 0010).
- Added `.mdx` pages: Markdown plus a closed list of tags that embed a table, a flow or a model (decision 0011, guide `embed-a-piece.mdx`, reference `mdx-tags.csv`).
- Added the guideline to write each document for its reader (`HOW-DOCS-WORK.md`).
- Revised the plan after review: M1a (package, demo, tests) before M1; language selection and the Spanish header handling move to M1; the reference tables are generated at M3; the order of closing M4 is set.
- Renamed `04-code-map.md` to `04-read-the-code.md`: it produced the same address as `code-map.yml`. D008 now reports any two files of a folder with the same slug.
- Added decision 0012: each reference table is generated from its owner in Python.
- Documented the rules of the reader: loading a node by path, safe import, raw HTML off, a closed list of image types, tags alone on a line, section precedence, criteria for each check.
- Added visual components for `.mdx` pages: callout, steps, tabs, cards and details, from a closed registry rendered by Django templates (decision 0013, checks D063 and D064).
- Raw HTML is never rendered; the semantic tags `details` and `summary` are read in `.md` and `.mdx`, and each component declares whether it needs JavaScript (decision 0013, check D065).
- Added decision 0014: what AAD-docs copies, vendors or only reads from the owner's other repositories, and which it rejects.
- Decision 0013 records what the owner confirmed on 2026-11-15: nothing in a Markdown file runs, semantic tags are allowed, each tag declares whether it needs JavaScript, and link attributes accept only `http`, `https`, `mailto` and relative paths (type `url`, check D064).
- Proposed Django 5.2 or later (decision 0008) and the design-system CSS vendored at a pinned tag.
- Added a roadmap to the plan: what the owner can do after each milestone, and what each waits for.
- Added the agent skills `repo-docs-canvas` and `pending-decisions-canvas` in `.agent/skills/`, with `.claude/skills/` as symlinks to them (operations).
- No code yet.
