"""Code map and reference table writer for AAD-docs."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import yaml
from django.apps import apps

from aad_docs.codemap.classes import describe_classes
from aad_docs.codemap.models import describe_models
from aad_docs.codemap.routes import describe_routes
from aad_docs.conf import SETTINGS_SPEC, get_settings
from aad_docs.generated import GeneratedManifest
from aad_docs.nodes import NODE_OPTIONS_SPEC
from aad_docs.readers import FILE_TYPES_SPEC
from aad_docs.readers.mdx import MDX_TAGS


COMMANDS_SPEC: tuple[dict[str, str], ...] = (
    {
        "command": "docs_codemap",
        "arguments": "[app_label ...]",
        "writes": "code-map.yml, 06-reference/*.csv, .generated.yml",
        "meaning": "Generates the code map and reference tables from models, routes, classes and the Python registries. Stops when a generated file was edited by hand.",
    },
    {
        "command": "docs_codemap --check",
        "arguments": "[app_label ...]",
        "writes": "nothing",
        "meaning": "Exits with an error when the generated files are out of date with the code. For CI.",
    },
    {
        "command": "docs_check",
        "arguments": "[app_label ...]",
        "writes": "nothing",
        "meaning": "Reports every finding listed in checks.csv. Exits with an error when one is found.",
    },
    {
        "command": "docs_screenshots",
        "arguments": "[app_label ...]",
        "writes": "assets/*.png",
        "meaning": "Retakes the screenshots of the guides against the local server in each language.",
    },
)


def _to_csv_text(columns: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])
    return buf.getvalue()


def build_reference_tables_for_aad_docs() -> dict[str, str]:
    """Build the 06-reference/*.csv tables for aad_docs from their owners in Python (decision 0012)."""
    from aad_docs.checks import CHECKS

    tables: dict[str, str] = {}
    tables["06-reference/settings.csv"] = _to_csv_text(
        ["key", "type", "default", "meaning"],
        list(SETTINGS_SPEC),
    )
    tables["06-reference/node-options.csv"] = _to_csv_text(
        ["option", "type", "required", "default", "meaning"],
        list(NODE_OPTIONS_SPEC),
    )
    mdx_rows = [
        {
            "tag": spec["tag"],
            "form": spec["form"],
            "attributes": spec["attributes"],
            "places_in_the_page": spec["places_in_the_page"],
            "reads_from": spec["reads_from"],
            "js": spec["js"],
            "works_in": spec["works_in"],
        }
        for spec in MDX_TAGS.values()
    ]
    tables["06-reference/mdx-tags.csv"] = _to_csv_text(
        ["tag", "form", "attributes", "places_in_the_page", "reads_from", "js", "works_in"],
        mdx_rows,
    )
    tables["06-reference/file-types.csv"] = _to_csv_text(
        ["extension", "holds", "written_by", "reader", "shown_as"],
        list(FILE_TYPES_SPEC),
    )
    tables["06-reference/commands.csv"] = _to_csv_text(
        ["command", "arguments", "writes", "meaning"],
        list(COMMANDS_SPEC),
    )
    check_rows = [
        {
            "code": c["code"],
            "finding": c["finding"],
            "detected_by": c["detected_by"],
            "fix": c["fix"],
        }
        for c in CHECKS.values()
    ]
    tables["06-reference/checks.csv"] = _to_csv_text(
        ["code", "finding", "detected_by", "fix"],
        check_rows,
    )
    return tables


def build_codemap_payload(app_label: str) -> dict[str, Any]:
    """Assemble the code-map.yml data structure for app_label."""
    return {
        "app": app_label,
        "status": "generated",
        "models": describe_models(app_label),
        "routes": describe_routes(app_label),
        "modules": describe_classes(app_label),
    }


def build_model_field_tables(app_label: str) -> dict[str, str]:
    """Build CSV field tables for each model of an app."""
    tables: dict[str, str] = {}
    for m in describe_models(app_label):
        rows = [
            {
                "field": f["name"],
                "type": f["type"],
                "verbose_name": f["verbose_name"],
                "required": "yes" if f["required"] else "no",
                "relation": f["relation"],
                "description": f["help_text"],
            }
            for f in m["fields"]
        ]
        tables[f"06-reference/{m['model_name']}-fields.csv"] = _to_csv_text(
            ["field", "type", "verbose_name", "required", "relation", "description"],
            rows,
        )
    return tables


def write_codemap(
    app_labels: list[str] | None = None,
    *,
    check_only: bool = False,
    include_reference_tables: bool = True,
) -> list[str]:
    """Write code-map.yml and reference tables through the generated-file guard.

    When check_only=True, returns the list of files that are out of date without writing.
    """
    cfg = get_settings()
    exclude = set(cfg.get("EXCLUDE_APPS") or [])

    if app_labels:
        target_configs = [apps.get_app_config(lbl) for lbl in app_labels]
    else:
        target_configs = [
            ac
            for ac in apps.get_app_configs()
            if ac.label not in exclude and (Path(ac.path) / "docs" / "__init__.py").is_file()
        ]

    written_or_drifted: list[str] = []

    for ac in target_configs:
        docs_dir = Path(ac.path) / "docs"
        if not (docs_dir / "__init__.py").is_file():
            continue
        manifest = GeneratedManifest(docs_dir)

        payload = build_codemap_payload(ac.label)
        yml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

        files_to_process: dict[str, str] = {"code-map.yml": yml_text}
        if include_reference_tables:
            if ac.label == "aad_docs":
                files_to_process.update(build_reference_tables_for_aad_docs())
            else:
                files_to_process.update(build_model_field_tables(ac.label))

        for rel_path, content in files_to_process.items():
            if check_only:
                if manifest.would_change(rel_path, content):
                    written_or_drifted.append(f"{ac.label}:{rel_path}")
            else:
                out_path = manifest.write(rel_path, content)
                written_or_drifted.append(str(out_path))

    return written_or_drifted
