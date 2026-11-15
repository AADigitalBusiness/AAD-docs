# Project plan

Read this page to see what AAD-docs will deliver, in what order, and how each milestone is accepted.

```mermaid
flowchart LR
    m0["M0<br/>Repository"] --> m1["M1<br/>Navigable docs"]
    m1 --> m2["M2<br/>Code map"]
    m2 --> m3["M3<br/>Tables and flows"]
    m3 --> m4["M4<br/>Spanish, checks, screenshots"]
    m4 --> m5["M5<br/>First project"]
    m5 -.-> m6["M6 · future<br/>Database index"]
```

## Goal

Keep the documentation of every project current, navigable and consistent, so that the owner can move through a complex project as a user would.

| Requirement | How the project meets it |
|---|---|
| Navigate a project without reading all its code | Code map generated from models, routes and classes |
| Very visual | Every page opens with a diagram; data files become interactive views |
| English for technical readers, Spanish for non-technical users | `name.es.md` next to `name.md`; Django translations for model texts |
| Screenshots and interactive pieces | `docs_screenshots`; explorer, table and simulator drawn from data files; `.mdx` pages that embed them |
| Flat files | `.md`, `.mdx`, `.yml`, `.csv`, `.json` inside each app's `docs/` |
| A fixed address for every app, page and model on the live site | Addresses taken from app and model metadata; `docs_url()` |
| Explains itself | Fixed page anatomy; `HOW-DOCS-WORK.md` |
| Installable Django app | `aad_docs` in `INSTALLED_APPS`; `__init__.py` resolves each node |
| Model metadata resolves model documentation | `docs_codemap` reads `_meta`, field options and docstrings |
| No overwriting, no repetition | One owner per fact; generated-file manifest; `docs_check` |

## Out of scope

- Editing documentation in the browser. Files are edited in the editor and reviewed in git.
- A database in the core. The app defines no models through M5. A later delivery adds an optional index: see M6.
- Hosting a public documentation site.
- Documenting code that is not a Django app.

## Milestones

Each milestone advances backend and frontend together and ends with something usable. The documentation of AAD-docs is the acceptance test: each milestone must render more of it.

### M0 · Repository

| Deliverable | Detail |
|---|---|
| Package skeleton | `pyproject.toml`, `aad_docs/__init__.py`, `apps.py`, package data for `docs/`, templates and static files |
| Demo project | `demo/` with settings, `urls.py` and one small app, `demo/catalog`, that has a model |
| CI | Tests and lint on every pull request |

Accepted when: `pip install -e .` works and `python demo/manage.py check` passes.

The demo app exists because `aad_docs` has no models. It is the only place where the model-metadata features can be shown and tested.

### M1 · Navigable docs

| Side | Deliverable |
|---|---|
| Backend | Discovery, nodes, `.md` reader, routing for apps, sections and pages, `docs_url()`, URLs and views, staff-only access |
| Frontend | Base layout, navigation menu, page with Mermaid |

Accepted when:

- `/docs/aad-docs/` and `/docs/project/` in the demo render every `.md` in this repository, diagrams included.
- An empty `__init__.py` produces a node with default slug, title and page order.
- A folder without `__init__.py` does not appear.
- Each page answers at the address its file name gives it, and `docs_url("aad_docs")` returns `/docs/aad-docs/`.
- A non-staff user gets no access.

### M2 · Code map

| Side | Deliverable |
|---|---|
| Backend | `docs_codemap`: models from `_meta`, routes from the URL resolver, classes and docstrings; `.yml` reader; generated-file manifest; model pages and their addresses |
| Frontend | Explorer: route, view, service, model, each with its file |

Accepted when:

- `docs_codemap` writes `aad_docs/docs/code-map.yml`, replacing the hand-written design target, and `demo/catalog/docs/code-map.yml` with the demo model.
- The model diagram of `demo/catalog` is drawn from its relations.
- Each model of `demo/catalog` has a page at `/docs/catalog/<model-slug>/` with no file written, and `docs_url(Model)` returns that address.
- A file in `demo/catalog/docs/<model-slug>/` shows under the address of that model.
- Editing a generated file by hand makes the next run stop and report it.
- `docs_codemap --check` fails when the code changed and the files did not.

### M3 · Tables and flows

| Side | Deliverable |
|---|---|
| Backend | `.csv`, `.json` and `.mdx` readers; reference tables generated from model metadata, settings defaults and command help |
| Frontend | Table that sorts and filters; simulator for `"type": "flow"`; pieces mounted inside an `.mdx` page |

Accepted when:

- Every file in `aad_docs/docs/06-reference/` opens as a sortable, filterable table.
- `request-flow.json` plays step by step.
- `embed-a-piece.mdx` shows its table and its flow inside the page.
- The field table of the demo model is generated, with `help_text` as its description.

### M4 · Spanish, checks, screenshots

| Side | Deliverable |
|---|---|
| Backend | Language selection with fallback; `docs_check`; `docs_screenshots` |
| Frontend | Language switcher; screenshots in guides |

Accepted when:

- With Spanish active, `01-overview` and `browse-the-docs` show their `.es.md`; every other page falls back to English.
- Model names and help texts of the demo app show in Spanish from its translations.
- `docs_check` reports each rule in [checks.csv](../aad_docs/docs/06-reference/checks.csv) on a fixture built to break it, and passes on this repository.
- `docs_screenshots` takes the screenshots of `browse-the-docs` in both languages.

### M5 · First project

Install the app in one real project, document one of its apps to the minimum (README, map, getting started, overview, generated code map) and record what the standard got wrong.

Accepted when: the owner can find a model, a route and a class of that app from `/docs/` without opening the code.

The project is not chosen yet.

### M6 · Database index (future delivery)

Recommended, not scheduled. Start it after M5, once a real project shows which of its gains are needed.

Combine the file-based documentation with [django-tree-queries](https://github.com/feincms/django-tree-queries) in an optional module, `aad_docs.index`. The files stay the source; the index is derived from them and rebuilt by a command. The reasons and the alternatives are in [decision 0009](../aad_docs/docs/07-decisions/0009-optional-database-index.md).

| Side | Deliverable |
|---|---|
| Backend | `DocNode` model on django-tree-queries; `docs_sync` and `docs_sync --check`; search; link from a node to a model; permissions per node |
| Frontend | Search box and results with their path in the tree; help link in the admin of a linked model |

Build order: search first, then the link between nodes and models, then permissions.

Accepted when:

- The core still works, with no model and no migration, in a project that does not install the module.
- Deleting every row and running `docs_sync` restores the same index.
- A search for a word in any page returns that page with its path in the tree.
- The admin of a linked model opens its documentation page.

## Risks

| Risk | Effect | Response |
|---|---|---|
| Importing `__init__.py` runs arbitrary code at startup | A broken node breaks the docs, or the project | Import inside a guard; a failing node is reported by `docs_check` and skipped, never fatal |
| Docs expose internal structure | Models and routes visible to the wrong reader | Staff-only by default; `ACCESS` setting |
| Class discovery is fuzzy | The code map lists noise or misses services | Start with models, views and URL patterns, which Django can enumerate; add other classes by convention (`services/`) and by opt-in |
| Spanish falls behind | Users read outdated pages | `synced` header checked by `docs_check` in CI |
| Generated files drift from code | The map lies | `docs_codemap --check` in CI |
| The database index falls behind the files (M6) | Search and links show outdated content | The index is never edited by hand; `docs_sync --check` in CI |
| Docs missing from installed packages | Empty nodes in production | Package data declared at M0; a check at startup |

## Open decisions

| Decision | Proposed | Recorded in |
|---|---|---|
| Frontend technology | Django templates and plain JavaScript in the package | [0007](../aad_docs/docs/07-decisions/0007-frontend-django-templates.md) |
| Package name, versions, libraries | `aad_docs`; Python 3.11+, Django 4.2+; `markdown-it-py`, `PyYAML`; Mermaid vendored | [0008](../aad_docs/docs/07-decisions/0008-package-name-and-dependencies.md) |
| First project for M5 | Not chosen | This page |
| Addresses | Taken from app and model metadata; model slug is `model_name` | [0010](../aad_docs/docs/07-decisions/0010-addresses-from-metadata.md) |
| `.mdx` | Markdown plus a closed list of tags; no JavaScript, no build | [0011](../aad_docs/docs/07-decisions/0011-mdx-closed-tag-set.md) |
| Database index | Optional module on django-tree-queries, in a future delivery | [0009](../aad_docs/docs/07-decisions/0009-optional-database-index.md) |
| Screenshot tool | Playwright against the local server | Decide at M4 |

## Next

- How the pieces fit: [03-architecture.md](03-architecture.md)
- Where each piece will live: [04-code-map.md](../aad_docs/docs/04-code-map.md)
