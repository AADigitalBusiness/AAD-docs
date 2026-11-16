"""Generated-file manifest and hand-edit guard for AAD-docs.

Content hashing adapted from django-md-cms / wagtail-shopify (see decisions 0012 and 0014).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


class HandEditedError(RuntimeError):
    """Raised when a generated file on disk was edited by hand (D040)."""


INITIAL_DESIGN_TARGETS: frozenset[str] = frozenset(
    {
        "code-map.yml",
        "06-reference/settings.csv",
        "06-reference/node-options.csv",
        "06-reference/mdx-tags.csv",
        "06-reference/file-types.csv",
        "06-reference/commands.csv",
        "06-reference/checks.csv",
    }
)


def sha256_text(content: str) -> str:
    """Return the hex SHA-256 digest of UTF-8 text."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class GeneratedManifest:
    """Tracks the hash of each generated file and refuses to overwrite one edited by hand.

    Replaces once a file of the initial design-target set that has no entry in .generated.yml.
    """

    MANIFEST_FILENAME = ".generated.yml"

    def __init__(self, docs_dir: Path) -> None:
        self.docs_dir = docs_dir.resolve()
        self.manifest_path = self.docs_dir / self.MANIFEST_FILENAME
        self.entries: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self.manifest_path.is_file():
            return {}
        try:
            data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except yaml.YAMLError:
            pass
        return {}

    def save(self) -> None:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        serialized = yaml.safe_dump(self.entries, sort_keys=True, allow_unicode=True)
        self.manifest_path.write_text(serialized, encoding="utf-8")

    def check_file_guard(self, rel_path: str) -> None:
        """Raise HandEditedError if rel_path was edited by hand."""
        rel_norm = rel_path.replace("\\", "/").lstrip("/")
        if rel_norm == "request-flow.json":
            raise HandEditedError("request-flow.json is hand-written and may not be overwritten.")

        target = (self.docs_dir / rel_norm).resolve()
        if not target.is_relative_to(self.docs_dir):
            raise ValueError(f"Refusing path outside docs_dir: {rel_path}")

        if not target.exists():
            return

        current_hash = sha256_text(target.read_text(encoding="utf-8"))
        recorded_hash = self.entries.get(rel_norm)

        if recorded_hash is not None:
            if current_hash != recorded_hash:
                raise HandEditedError(
                    f"Generated file '{rel_norm}' in {self.docs_dir} was edited by hand (D040)."
                )
            return

        # File exists on disk but has no entry in .generated.yml
        if rel_norm in INITIAL_DESIGN_TARGETS:
            return
        raise HandEditedError(
            f"Existing file '{rel_norm}' in {self.docs_dir} is not in {self.MANIFEST_FILENAME} and is not an initial design target."
        )

    def hand_edited_files(self) -> list[str]:
        """Return relative paths of tracked files whose on-disk hash differs from .generated.yml (D040)."""
        bad: list[str] = []
        for rel_norm, recorded_hash in sorted(self.entries.items()):
            target = self.docs_dir / rel_norm
            if not target.is_file():
                continue
            actual = sha256_text(target.read_text(encoding="utf-8"))
            if actual != recorded_hash:
                bad.append(rel_norm)
        return bad

    def would_change(self, rel_path: str, new_content: str) -> bool:
        """Return True if writing new_content would change the file on disk (or fail the guard)."""
        rel_norm = rel_path.replace("\\", "/").lstrip("/")
        self.check_file_guard(rel_norm)
        target = self.docs_dir / rel_norm
        if not target.is_file():
            return True
        return target.read_text(encoding="utf-8") != new_content

    def write(self, rel_path: str, content: str) -> Path:
        """Write content to rel_path after verifying the hand-edit guard, and update .generated.yml."""
        rel_norm = rel_path.replace("\\", "/").lstrip("/")
        self.check_file_guard(rel_norm)
        target = (self.docs_dir / rel_norm).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.entries[rel_norm] = sha256_text(content)
        self.save()
        return target
