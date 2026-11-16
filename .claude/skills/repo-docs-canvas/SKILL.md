---
name: repo-docs-canvas
description: Mostrar la documentación de un repo (md, mdx, yml, csv, json) como un canvas navegable publicado como artifact. Úsalo al pedir ver los documentos del repo, mostrar el repo en un canvas o actualizar ese canvas.
---

# Repo docs canvas

Publishes the documentation files of a git repository as one self-contained HTML page: a sticky file tree on the left, every file as a section on the right, in repository order. Mermaid diagrams are drawn, CSV files become tables, links between pages work, and `.mdx`, `.yml`, `.json` and `.py` files show as source with a label.

The page shows the repository **as committed**: the script reads tracked files with `git ls-files`. Commit first, or tell the person the canvas shows tracked files only.

## Files of this skill

| File | Use |
|---|---|
| `scripts/repo_canvas.py` | Builds the page. Needs `markdown-it-py` |
| `scripts/approvals.js.html` | Script that draws the Approve / Request changes controls; added only with `--approvals` |
| `scripts/repo_canvas.template.html` | Layout and theme tokens (light, system dark, explicit dark). The script reads it from its own folder |

## Steps

1. Find the repo root. Ask only if there are several candidates and the request does not name one. Check that it is a git repository and that `markdown-it-py` imports (`pip install --break-system-packages markdown-it-py` if not).
2. Build: `python3 .claude/skills/repo-docs-canvas/scripts/repo_canvas.py <repo_root> <scratchpad>/canvas.html --title "<Repo name>"`. The script prints the number of files and pending items. A link that renders as `#` points to a file that is not tracked: report it, do not hide it.
3. Publish with the Artifact tool, `file_path` set to `<scratchpad>/canvas.html`. First publish: pass `icon` (`docs`) and a one-sentence `description`. Later publishes of the same path keep the URL; do not pass `icon` again.
4. With `--approvals`, each pending decision gets Approve and Request changes controls, plus an optional note. Publish that page with `capabilities: {db: {rules: [{path: "approvals", read: "view", write: "owner"}]}, user: {}}`. Only the artifact's owner can write, so a reader who is not the owner sees "Waiting for the owner". Each verdict is one document, `approvals/<decision number>`, with `decision`, `title`, `verdict` (`approved` or `changes`), `note` and `at`. Later publishes of the same path keep the capabilities when `capabilities` is omitted. The page never edits the repository: `pending-decisions-canvas` describes how the verdicts reach the files.
5. Reply in one or two sentences: what the page holds and what changed since the last version. Do not paste the link; the card carries it.

## Agent documentation

The documentation written for coding agents (`AGENTS.md`, `CLAUDE.md` and everything under `.claude/`) is hidden by default, because the people who read the canvas are not its audience. A checkbox in the header, "Show agent documentation", shows it for technical readers, and a link that points to one of those files shows it by itself. Pass `--show-agent-docs` to open the page with them visible. The count in the header leaves them out.

## Rules

- Mermaid renders natively in artifacts through `<pre class="mermaid">`. Do not load a Mermaid library.
- The script escapes everything and `markdown-it` runs in `commonmark` mode without `html`. Never put raw HTML from the documents into the page.
- Do not edit the repository to produce the canvas. The canvas is a view; the files stay the source.
- A small change to a published page goes as `edits` on the same `file_path`. A changed repository means a rebuild and a new publish.
- Use `--pending-regex` only when the repository has `**Status:**` lines; `pending-decisions-canvas` covers that.
