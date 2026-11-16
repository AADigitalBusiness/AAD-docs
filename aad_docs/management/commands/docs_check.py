"""Management command docs_check."""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from aad_docs.checks import run_checks


class Command(BaseCommand):
    """Reports every finding listed in checks.csv and exits with an error when one is found."""

    help = "Run documentation checks (D001 to D065)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("app_labels", nargs="*", help="Optional app labels to check.")

    def handle(self, *args: Any, **options: Any) -> None:
        app_labels: list[str] = options.get("app_labels") or []
        findings = run_checks(app_labels or None)
        for f in findings:
            self.stdout.write(f"{f.code} {f.path}: {f.message}")
        if findings:
            raise CommandError(f"docs_check found {len(findings)} issue(s).")
        self.stdout.write("docs_check passed with 0 findings.")
