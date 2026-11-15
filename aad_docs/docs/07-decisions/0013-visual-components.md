# 0013 · Pages use visual components from a closed registry

Read this page to know how a page gets callouts, steps, tabs and cards, and why an author cannot write HTML or define a component of their own.

```mermaid
flowchart LR
    subgraph before["Before"]
        b["Markdown text, tables and images.<br/>Structure that Markdown lacks needs raw HTML"]
    end
    subgraph after["After"]
        a[".mdx tag → registry → Django template<br/>drawn with the design system"]
    end
    before --> after
```

**Status:** Proposed · 2026-11-15. The owner confirmed on 2026-11-15 that nothing in a Markdown file runs, that semantic tags such as `details` and `summary` are allowed, that each tag declares whether it needs JavaScript, and that link attributes accept only safe schemes. The component list is not yet confirmed.

## Context

Markdown has headings, lists, tables and code. A documentation page also needs a warning that stands out, a procedure drawn as steps, alternatives in tabs and a set of linked cards. The owner asked for documentation elements that become visual components, as in his other projects: `wagtail-shopify` reads components that stand alone on a line, and `django-dsadmin` ships its components as Django templates.

## Decision

Every visual element is a component in one registry, `readers.mdx.MDX_TAGS`. The registry is the owner of [mdx-tags.csv](../06-reference/mdx-tags.csv).

A component has:

| Part | Meaning |
|---|---|
| Name | The tag an author writes: `Callout`, `Steps`, `Tabs` |
| Form | `line` for a tag on one line; `container` for a tag that opens and closes on its own lines and holds Markdown |
| Attributes | Each with a type, whether it is required and, where it applies, the list of values |
| Parent | The container it may sit in: `Tab` only in `Tabs`, `Card` only in `Cards` |
| Template | `aad_docs/templates/aad_docs/components/<name>.html` |

The first set:

| Component | Shows |
|---|---|
| `Callout` | A note, tip, warning or danger box around the text it holds |
| `Steps` | A numbered list drawn as a sequence |
| `Tabs` and `Tab` | Alternatives, one panel for each tab |
| `Cards` and `Card` | A grid of linked cards |
| `details` and `summary` | A section the reader opens and closes. They keep their HTML names and work in `.md` and in `.mdx` |
| `Model`, `ModelDiagram`, `Table`, `Explorer`, `Flow`, `Screenshot` | The data pieces of [decision 0011](0011-mdx-closed-tag-set.md) |

```mdx
<Callout type="warning">
Run `docs_codemap --check` before you merge.
</Callout>
```

- The reader renders the body of a container as Markdown, then renders the template with its attributes and body.
- Templates use the classes of the design system chosen in [0007](0007-frontend-django-templates.md) and no inline style.
- Nothing in a Markdown file ever runs. Raw HTML is never rendered: a tag that the registry does not list shows as text. The owner chose this on 2026-11-15, so that no page can run a script.
- Each component declares in the registry whether it needs JavaScript: `none` (HTML and CSS are enough), `enhance` (it works without JavaScript and the script improves it, as `Tabs` and `Table`) or `required` (it does not appear without the script, as `Explorer` and `Flow`).
- A page loads only the scripts that the components it uses ask for. Scripts are static files of the package, never inline. A `required` component shows a short notice when JavaScript is off.
- An attribute that becomes a link, such as `href` of a `Card`, has the type `url` in the registry. It accepts only `http`, `https`, `mailto` and relative paths, so `javascript:` and `data:` values are refused. A value outside that list shows no link, and `docs_check` reports it (D064).
- Text attributes, such as `title` and `summary`, are translated in the `.es.mdx` file.
- An author cannot define a component in a page. A new component is a registry entry, a template and a test, and `mdx-tags.csv` is regenerated from it.

## Alternatives

- **Raw HTML in the page, allowed or filtered.** No registry to maintain, but `docs_check` cannot validate it, a public site would run its scripts, and a filter needs a new dependency.
- **Components defined in each page, as in full MDX.** It needs a build and lets a page run code: [0011](0011-mdx-closed-tag-set.md).
- **GitHub alert syntax only** (`> [!NOTE]`). It works in `.md` and on GitHub, and covers callouts only.

## Consequences

- GitHub shows the tags of an `.mdx` as text. A page that must read well there stays `.md`.
- A component is a contract: its attributes and template are part of the interface, and renaming one is a breaking change.
- `docs_check` reports an unclosed container or a tag in the wrong parent (D063) and a missing or unlisted attribute, or a `url` value with a scheme that is not allowed (D064).
- The appearance of every page changes in one place, the templates.
- A page that uses only components with `js: none` loads no script. A policy that allows only own scripts (`script-src 'self'`) works.
- `docs_check` reports an HTML tag outside the registry (D065), because it would show as text.

## Next

- The tags and their attributes: [mdx-tags.csv](../06-reference/mdx-tags.csv)
- Use them: [embed-a-piece.mdx](../05-guides/embed-a-piece.mdx)
- The frontend decision: [0007 · The frontend is Django templates and plain JavaScript](0007-frontend-django-templates.md)
