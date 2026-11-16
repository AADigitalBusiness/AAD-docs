"""Management command docs_codemap."""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from aad_docs.codemap.writer import write_codemap
from aad_docs.generated import HandEditedError


class Command(BaseCommand):
    """Generates the code map and reference tables from models, routes, classes and Python registries."""

    help = "Generates code-map.yml and reference tables from models, routes, classes and Python registries."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("app_labels", nargs="*", help="Optional app labels to generate code maps for.")
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with an error when generated files are out of date with the code.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        app_labels: list[str] = options.get("app_labels") or []
        check_only: bool = bool(options.get("check"))

        try:
            result = write_codemap(app_labels or None, check_only=check_only)
        except HandEditedError as exc:
            raise CommandError(str(exc)) from exc

        if check_only:
            if result:
                raise CommandError(f"Generated files are out of date: {', '.join(result)}")
            self.stdout.write("All generated files are up to date.")
        else:
            for path_str in result:
                self.stdout.write(f"Wrote {path_str}")
