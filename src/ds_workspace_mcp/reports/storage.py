from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ds_workspace_mcp.exceptions import InvalidDatasetNameError, PathTraversalError


@dataclass(frozen=True)
class ReportFileMetadata:
    """Filesystem metadata for one stored report artifact."""

    output_name: str
    output_path: str
    size_bytes: int
    created_at: str
    metadata_changed_at: str
    modified_at: str
    content_sha256: str | None = None


class ReportStorage:
    """Safe, transactional storage for markdown reports inside one root."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def list_markdown_reports(self) -> list[ReportFileMetadata]:
        """Return metadata for markdown report files directly inside the root."""

        if not self.root.exists():
            return []

        reports: list[ReportFileMetadata] = []
        for path in sorted(self.root.glob("*.md")):
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            if resolved.parent != self.root:
                continue
            reports.append(self.metadata_for_path(resolved, include_hash=False))
        return reports

    def read_text(self, output_name: str) -> tuple[Path, str]:
        """Read a markdown report after resolving and validating its name."""

        path = self.resolve_existing(output_name)
        return path, path.read_text(encoding="utf-8")

    def write_text(self, output_name: str, content: str, *, overwrite: bool = False) -> Path:
        """Write a report atomically, failing on collisions unless overwrite is enabled."""

        if not isinstance(content, str):
            raise InvalidDatasetNameError("report content must be a string.")

        self.root.mkdir(parents=True, exist_ok=True)
        target_path = self.resolve_target(output_name)
        if target_path.exists() and target_path.is_symlink():
            raise PathTraversalError("Report output must stay inside the reports directory.")
        if target_path.exists() and not overwrite:
            raise InvalidDatasetNameError(f"Modeling report already exists: {target_path.name}")

        temp_path: Path | None = None
        try:
            temp_path = self._write_temp_file(target_path, content)
            self._commit_temp_file(temp_path, target_path, overwrite=overwrite)
        except FileExistsError as error:
            raise InvalidDatasetNameError(
                f"Modeling report already exists: {target_path.name}"
            ) from error
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

        return target_path

    def copy(self, output_name: str, new_output_name: str, *, overwrite: bool = False) -> Path:
        """Copy one report using the same atomic target semantics as save."""

        source_path, markdown = self.read_text(output_name)
        target_path = self.write_text(new_output_name, markdown, overwrite=overwrite)
        if source_path == target_path and not overwrite:
            raise InvalidDatasetNameError(f"Modeling report already exists: {new_output_name}")
        return target_path

    def rename(self, output_name: str, new_output_name: str, *, overwrite: bool = False) -> Path:
        """Rename one report without silently replacing an existing target."""

        source_path = self.resolve_existing(output_name)
        target_path = self.resolve_target(new_output_name)
        if source_path == target_path:
            raise InvalidDatasetNameError(f"Modeling report already exists: {new_output_name}")
        if target_path.exists() and target_path.is_symlink():
            raise PathTraversalError("Report output must stay inside the reports directory.")
        if target_path.exists() and not overwrite:
            raise InvalidDatasetNameError(f"Modeling report already exists: {new_output_name}")

        if overwrite:
            source_path.replace(target_path)
        else:
            try:
                os.link(source_path, target_path)
            except FileExistsError as error:
                raise InvalidDatasetNameError(
                    f"Modeling report already exists: {new_output_name}"
                ) from error
            source_path.unlink()
        return target_path

    def delete(self, output_name: str) -> Path:
        """Delete one validated report."""

        path = self.resolve_existing(output_name)
        path.unlink()
        return path

    def metadata(self, output_name: str, *, include_hash: bool = True) -> ReportFileMetadata:
        """Return metadata for one existing report."""

        path = self.resolve_existing(output_name)
        return self.metadata_for_path(path, include_hash=include_hash)

    def metadata_for_path(self, path: Path, *, include_hash: bool) -> ReportFileMetadata:
        """Return metadata for an already resolved report path."""

        stat = path.stat()
        return ReportFileMetadata(
            output_name=path.name,
            output_path=str(path),
            size_bytes=stat.st_size,
            created_at=_format_timestamp(_created_timestamp(stat)),
            metadata_changed_at=_format_timestamp(stat.st_ctime),
            modified_at=_format_timestamp(stat.st_mtime),
            content_sha256=_sha256_file(path) if include_hash else None,
        )

    def resolve_existing(self, output_name: str) -> Path:
        """Resolve one existing markdown report inside the root."""

        path = self.resolve_target(output_name)
        if not path.exists():
            raise InvalidDatasetNameError(f"Modeling report not found: {output_name}")
        if path.is_symlink() or not path.is_file():
            raise PathTraversalError("Report output must stay inside the reports directory.")
        resolved = path.resolve()
        if resolved.parent != self.root:
            raise PathTraversalError("Report output must stay inside the reports directory.")
        return resolved

    def resolve_target(self, output_name: str) -> Path:
        """Resolve a markdown report target inside the root."""

        safe_name = self._validate_output_name(output_name)
        candidate_path = self.root / safe_name
        if candidate_path.is_symlink():
            raise PathTraversalError("Report output must stay inside the reports directory.")
        if candidate_path.exists():
            resolved = candidate_path.resolve()
            if resolved.parent != self.root:
                raise PathTraversalError("Report output must stay inside the reports directory.")
            return resolved

        resolved_parent = candidate_path.parent.resolve()
        if resolved_parent != self.root:
            raise PathTraversalError("Report output must stay inside the reports directory.")
        return candidate_path.resolve()

    def _write_temp_file(self, target_path: Path, content: str) -> Path:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.root,
                prefix=f".{target_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
        except Exception:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
        return temp_path

    def _commit_temp_file(self, temp_path: Path, target_path: Path, *, overwrite: bool) -> None:
        if overwrite:
            os.replace(temp_path, target_path)
            return

        os.link(temp_path, target_path)
        temp_path.unlink()

    @staticmethod
    def _validate_output_name(output_name: str) -> str:
        if not isinstance(output_name, str) or not output_name.strip():
            raise InvalidDatasetNameError("output_name must be a non-empty string.")

        candidate_name = output_name.strip()
        if Path(candidate_name).name != candidate_name:
            raise PathTraversalError("Report output must stay inside the reports directory.")
        if not candidate_name.lower().endswith(".md"):
            raise InvalidDatasetNameError("Report output_name must end with .md.")
        return candidate_name


def _format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _created_timestamp(stat_result: os.stat_result) -> float:
    return getattr(stat_result, "st_birthtime", stat_result.st_ctime)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as report_file:
        for chunk in iter(lambda: report_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
