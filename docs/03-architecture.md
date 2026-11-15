# Architecture

Read this page to understand how AAD-docs is built: its components, the data that moves between them, and the one contract that separates backend from frontend.

```mermaid
flowchart LR
    subgraph backend["Backend · Python and Django"]
        discovery["Discovery"] --> nodes["Nodes"]
        nodes --> readers["Readers"]
        readers --> language["Language"]
        language --> views["URLs and views"]
        commands["Commands"]
    end
    subgraph frontend["Frontend · templates and light JavaScript"]
        nav["Navigation"]
        page["Page"]
        explorer["Explorer"]
        table["Table"]
        simulator["Simulator"]
    end
    files[("&lt;app&gt;/docs/")] --> discovery
    code[("Models, urls, classes")] --> commands
    commands --> files
    views -- "node tree + page content" --> frontend
```

**Status: design.** No component exists yet. The [plan](PLAN.md) says when each one is built.

## The contract

The backend hands the frontend a node tree with the content already read. The frontend never opens a file.

| Object | Field | Meaning |
|---|---|---|
| Node | `slug` | Address segment: `/docs/<slug>/` |
| Node | `title` | Shown in the menu, in the active language |
| Node | `order` | Position among its siblings |
| Node | `pages` | List of Page |
| Node | `children` | List of Node, one per subfolder that has an `__init__.py` |
| Page | `slug` | File stem without its numeric prefix: `01-overview` becomes `overview` |
| Page | `title` | First heading of a `.md`; file stem for data files |
| Page | `kind` | `md`, `yml`, `csv` or `json` |
| Page | `languages` | Languages the page exists in |
| Page | `content` | HTML for `md`; parsed data for the other kinds |

## Backend

| Component | Does | Delivers |
|---|---|---|
| Discovery | Walks `INSTALLED_APPS` and the root folder, finds each `docs/` that has an `__init__.py` | List of folders |
| Nodes | Imports each `__init__.py`, reads `node`, applies defaults | Node tree |
| Readers | One reader per extension turns a file into data | Page content |
| Language | Picks `name.es.md` when Spanish is active, falls back to `name.md` | Page in the requested language |
| URLs and views | Serves `/docs/`, `/docs/<slug>/` and deeper paths; checks access | One response per node or page |
| Commands | `docs_codemap`, `docs_check`, `docs_screenshots` | Generated files in the repository |

Rules the backend enforces:

- Only `.md`, `.yml`, `.csv` and `.json` are read. Images under `assets/` are served, never listed as pages. Files and folders that start with a dot are ignored.
- A folder without `__init__.py` is not a node.
- The tree is built once per process and cached. In `DEBUG` it is rebuilt on every request.
- A page path is resolved against the node's folder and may not leave it.

## Frontend

| Component | Does | Reads |
|---|---|---|
| Navigation | Menu with the node tree and a language switcher | Node tree |
| Page | Draws the HTML of a `.md`, runs Mermaid, shows screenshots | `md` content |
| Explorer | Click-through view of the code map: route, view, service, model | `code-map.yml` |
| Table | Sorts and filters | `csv` content |
| Simulator | Steps through a flow | `json` content with `"type": "flow"` |
| Style | Applies the visual standard and the page anatomy | All of the above |

The frontend is Django templates and plain JavaScript shipped inside the package. This is proposed, not settled: see [decision 0007](../aad_docs/docs/07-decisions/0007-frontend-django-templates.md).

## Generated files

Commands write files; people write pages. The two never share a file.

```mermaid
flowchart LR
    code[("Code")] --> codemap["docs_codemap"]
    codemap --> yml["code-map.yml"]
    codemap --> csv["06-reference/*.csv"]
    codemap --> manifest[".generated.yml<br/>hash of each generated file"]
    manifest --> guard{"Hash still matches?"}
    guard -- yes --> overwrite["Regenerate"]
    guard -- no --> stop["Stop and report<br/>a hand edit"]
```

- `docs_codemap` reads model metadata (`_meta`, field options, docstrings), the URL resolver and class docstrings.
- Each `docs/` folder holds a `.generated.yml` manifest with the hash of every generated file. A file whose hash no longer matches was edited by hand: the command stops instead of overwriting it.
- No command ever writes a `.md`.

## Next

- Where each component lives in the code: [04-code-map.md](../aad_docs/docs/04-code-map.md)
- How one request travels: [request-flow.json](../aad_docs/docs/request-flow.json)
- Why it is built this way: [07-decisions/](../aad_docs/docs/07-decisions/)
