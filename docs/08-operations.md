# Operations

Use this page to release AAD-docs, run its checks in CI and control who can read the documentation.

```mermaid
flowchart LR
    change["Change merged to main"] --> check["CI: tests + docs_check"]
    check -- pass --> tag["Tag a version"]
    check -- fail --> fix["Fix and push again"]
    tag --> install["Projects install the tag"]
```

**Status: planned.** CI and releases start at milestone 1 of the [plan](PLAN.md).

## Release

1. Update `CHANGELOG.md`.
2. Tag the version.

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. In each project, install the tag.

   ```bash
   pip install git+ssh://git@github.com/AADigitalBusiness/AAD-docs.git@v0.1.0
   ```

## Checks in CI

Run these on every pull request, in this repository and in every project that installs the app.

```bash
python manage.py docs_codemap --check
python manage.py docs_check
```

- `docs_codemap --check` fails when the generated files are out of date with the code.
- `docs_check` fails on the rules listed in [checks.csv](../aad_docs/docs/06-reference/checks.csv).

## Access

The documentation exposes models, routes and class names. Treat it as internal.

- Default: only staff users can open `/docs/`.
- Change it with the `ACCESS` setting: see [settings.csv](../aad_docs/docs/06-reference/settings.csv).
- A node can hide a page per request, because `__init__.py` is Python.

## Packaging

`docs/` folders hold non-Python files. A distributed app must declare them as package data, or only the `.py` files ship.

## If something fails

| Symptom | Check |
|---|---|
| A node is missing from the menu | The folder has an `__init__.py`; the app is in `INSTALLED_APPS` |
| A page shows in English with Spanish active | The `.es.md` file exists next to the English one |
| `docs_codemap` stops without writing | A generated file was edited by hand; restore it or delete it and rerun |
| Docs are missing after `pip install` | `docs/` is not declared as package data |
