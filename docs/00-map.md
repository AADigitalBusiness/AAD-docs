# Map

Use this page to find any document in the repository.

```
AAD-docs/
├── README.md                     ← entry point
├── README.es.md                  ← entry point in Spanish
├── CHANGELOG.md                  ← what changed and when
├── docs/                         ← root node: what crosses every app
│   ├── __init__.py               ← resolves the root node
│   ├── 00-map.md                 ← this page
│   ├── 02-getting-started.md     ← install and run
│   ├── 03-architecture.md        ← components and data flow
│   ├── 08-operations.md          ← release, CI, access
│   ├── HOW-DOCS-WORK.md          ← the documentation standard
│   └── PLAN.md                   ← milestones and acceptance criteria
└── aad_docs/                     ← the Django app (code arrives at milestone 1)
    └── docs/                     ← app node: documentation of aad_docs itself
        ├── __init__.py           ← resolves the app node
        ├── 01-overview.md        ← what it is and is not
        ├── 01-overview.es.md
        ├── 04-code-map.md        ← where to start reading the code
        ├── code-map.yml          ← modules, classes, routes (design target)
        ├── request-flow.json     ← how one request travels, step by step
        ├── 05-guides/            ← tasks, step by step
        ├── 06-reference/         ← exact options, settings, commands, checks
        └── 07-decisions/         ← why it is built this way
```

## Find by question

| Question | Document |
|---|---|
| What is this and what does it not do? | [01-overview.md](../aad_docs/docs/01-overview.md) |
| How do I install it? | [02-getting-started.md](02-getting-started.md) |
| How is it built? | [03-architecture.md](03-architecture.md) |
| Which file holds a class or route? | [04-code-map.md](../aad_docs/docs/04-code-map.md) |
| How do I document one of my apps? | [document-an-app.md](../aad_docs/docs/05-guides/document-an-app.md) |
| How do I browse the documentation? | [browse-the-docs.md](../aad_docs/docs/05-guides/browse-the-docs.md) |
| What are the exact options of a node? | [node-options.csv](../aad_docs/docs/06-reference/node-options.csv) |
| Which settings exist? | [settings.csv](../aad_docs/docs/06-reference/settings.csv) |
| What does each command do? | [commands.csv](../aad_docs/docs/06-reference/commands.csv) |
| What does `docs_check` verify? | [checks.csv](../aad_docs/docs/06-reference/checks.csv) |
| Which file types are read, and how is each shown? | [file-types.csv](../aad_docs/docs/06-reference/file-types.csv) |
| Why was it designed this way? | [07-decisions/](../aad_docs/docs/07-decisions/) |
| How do I release and operate it? | [08-operations.md](08-operations.md) |
| How do I write a page in this standard? | [HOW-DOCS-WORK.md](HOW-DOCS-WORK.md) |
| What gets built next? | [PLAN.md](PLAN.md) |
