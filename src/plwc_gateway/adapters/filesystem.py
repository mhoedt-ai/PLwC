"""Safe internal filesystem adapter for governed workspace access."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from plwc_gateway.policy import (
    evaluate_intent,
    IntentAction,
    PathPolicyResult,
    PolicyDecision,
    PolicyIntent,
    execute_with_policy,
    guard_path,
)

EntryKind = Literal["directory", "file", "other"]
WriteMode = Literal["rewrite", "append"]
COMMANDER_WORKSPACE_REQUIREMENTS = ("FR-006", "FR-CMD-001", "SR-010")

# RC12-FS-003 — search scope guards. Text search walked the whole tree and opened
# every file line-by-line with no size/binary/scope guard, so a single large binary
# (e.g. a multi-GB .zip) or a huge export tree blocked the operation for minutes.
# These bound what search reads; they only ever REDUCE scope (never widen it).
DEFAULT_SEARCH_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB — skip larger files in text search
DEFAULT_SEARCH_MAX_FILES_SCANNED = 50_000  # cap files content-scanned per search
DEFAULT_SEARCH_EXCLUDED_DIRS = ("qdrant_storage", ".git", "__pycache__", "node_modules")
_SEARCH_BINARY_PROBE_BYTES = 8192  # a NUL byte in the head marks the file as binary


@dataclass(frozen=True)
class FilesystemEntry:
    path: str
    kind: EntryKind
    size: int | None = None


@dataclass(frozen=True)
class FilesystemSearchMatch:
    path: str
    line_number: int
    line: str


@dataclass(frozen=True)
class FilesystemFileContent:
    path: str
    content: str | None = None
    size: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class FilesystemResult:
    ok: bool
    operation: str
    policy_decision: PolicyDecision
    path: str | None = None
    content: str | None = None
    entries: tuple[FilesystemEntry, ...] = ()
    matches: tuple[FilesystemSearchMatch, ...] = ()
    files: tuple[FilesystemFileContent, ...] = ()
    info: dict[str, Any] | None = None
    bytes_written: int | None = None
    replacements: int | None = None
    error: str | None = None
    requirement_ids: tuple[str, ...] = ()
    binary_data: dict[str, Any] | None = None
    source_path: str | None = None
    target_path: str | None = None
    search_stats: dict[str, Any] | None = None


class SafeFilesystemAdapter:
    def __init__(
        self,
        allowed_roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
        *,
        base_dir: str | os.PathLike[str] | None = None,
        protected_path_patterns: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None = None,
        project_root: str | os.PathLike[str] | None = None,
        policy_engine: Any | None = None,
        max_list_entries: int = 500,
        max_search_results: int = 100,
        max_batch_files: int = 10,
        max_batch_bytes: int = 1_000_000,
        max_binary_bytes: int = 100 * 1024 * 1024,
        max_search_file_bytes: int = DEFAULT_SEARCH_MAX_FILE_BYTES,
        max_search_files_scanned: int = DEFAULT_SEARCH_MAX_FILES_SCANNED,
        search_excluded_dirs: Iterable[str] = DEFAULT_SEARCH_EXCLUDED_DIRS,
    ) -> None:
        self.allowed_roots = _coerce_roots(allowed_roots)
        self.base_dir = base_dir
        self.protected_path_patterns = _coerce_roots(protected_path_patterns)
        self.project_root = project_root
        self.policy_engine = policy_engine
        self.max_list_entries = max_list_entries
        self.max_search_results = max_search_results
        self.max_batch_files = max_batch_files
        self.max_batch_bytes = max_batch_bytes
        self.max_binary_bytes = max_binary_bytes
        self.max_search_file_bytes = max_search_file_bytes
        self.max_search_files_scanned = max_search_files_scanned
        self.search_excluded_dirs = frozenset(d.casefold() for d in search_excluded_dirs)

    def read_text(self, path: str | os.PathLike[str], *, encoding: str = "utf-8") -> FilesystemResult:
        return self._execute(
            operation="read_file",
            path=path,
            action=IntentAction.READ,
            adapter_call=lambda: self._read_text(path, encoding),
        )

    def read_multiple_text(
        self,
        paths: Iterable[str | os.PathLike[str]],
        *,
        encoding: str = "utf-8",
        max_files: int | None = None,
        max_file_bytes: int | None = None,
        max_total_bytes: int | None = None,
    ) -> FilesystemResult:
        path_values = tuple(paths)
        effective_max_files = min(max_files or self.max_batch_files, self.max_batch_files)
        effective_max_file_bytes = min(max_file_bytes or self.max_batch_bytes, self.max_batch_bytes)
        effective_max_total_bytes = min(max_total_bytes or self.max_batch_bytes, self.max_batch_bytes)

        if not path_values:
            return self._denied_result("read_multiple_files", "", "At least one path is required.", ("NFR-002",))
        if effective_max_files < 1 or effective_max_file_bytes < 1 or effective_max_total_bytes < 1:
            return self._denied_result(
                "read_multiple_files",
                "",
                "Batch read limits must be positive integers.",
                ("FR-CMD-001", "NFR-002"),
            )
        if len(path_values) > effective_max_files:
            return self._denied_result(
                "read_multiple_files",
                "",
                f"Batch read supports at most {effective_max_files} files.",
                ("FR-CMD-001", "NFR-002"),
            )

        files: list[FilesystemFileContent] = []
        total_bytes = 0
        denied: FilesystemResult | None = None
        for path in path_values:
            result = self.read_text(path, encoding=encoding)
            if not result.ok:
                files.append(FilesystemFileContent(path=os.fspath(path), error=result.error))
                if result.policy_decision == PolicyDecision.DENY and denied is None:
                    denied = result
                continue
            content = result.content or ""
            size = len(content.encode(encoding))
            if size > effective_max_file_bytes:
                return self._denied_result(
                    "read_multiple_files",
                    path,
                    f"Batch read file exceeds {effective_max_file_bytes} bytes.",
                    ("FR-CMD-001", "NFR-002"),
                )
            total_bytes += size
            if total_bytes > effective_max_total_bytes:
                return self._denied_result(
                    "read_multiple_files",
                    os.fspath(path),
                    f"Batch read exceeds {effective_max_total_bytes} bytes.",
                    ("FR-CMD-001", "NFR-002"),
                )
            files.append(FilesystemFileContent(path=str(result.path or path), content=content, size=size))

        if denied is not None:
            return FilesystemResult(
                ok=False,
                operation="read_multiple_files",
                policy_decision=PolicyDecision.DENY,
                files=tuple(files),
                error="One or more paths were denied by policy.",
                requirement_ids=denied.requirement_ids,
            )

        return FilesystemResult(
            ok=True,
            operation="read_multiple_files",
            policy_decision=PolicyDecision.ALLOW,
            files=tuple(files),
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def write_text(
        self,
        path: str | os.PathLike[str],
        content: str,
        *,
        mode: WriteMode = "rewrite",
        encoding: str = "utf-8",
    ) -> FilesystemResult:
        if mode not in {"rewrite", "append"}:
            return self._denied_result("write_file", path, "Unsupported write mode.", ("NFR-002",))

        return self._execute(
            operation="write_file",
            path=path,
            action=IntentAction.WRITE,
            adapter_call=lambda: self._write_text(path, content, mode, encoding),
        )

    def list_directory(
        self,
        path: str | os.PathLike[str],
        *,
        depth: int = 1,
    ) -> FilesystemResult:
        return self._execute(
            operation="list_directory",
            path=path,
            action=IntentAction.READ,
            adapter_call=lambda: self._list_directory(path, depth),
        )

    def create_directory(self, path: str | os.PathLike[str]) -> FilesystemResult:
        return self._execute(
            operation="create_directory",
            path=path,
            action=IntentAction.WRITE,
            adapter_call=lambda: self._create_directory(path),
        )

    def move_path(
        self,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        overwrite: bool = False,
    ) -> FilesystemResult:
        source_policy = self._evaluate_path_policy(operation="move_path", path=source, action=IntentAction.WRITE)
        if source_policy is not None:
            return source_policy
        destination_policy = self._evaluate_path_policy(
            operation="move_path",
            path=destination,
            action=IntentAction.WRITE,
        )
        if destination_policy is not None:
            return destination_policy
        return self._move_path(source, destination, overwrite=overwrite)

    def copy_path(
        self,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        overwrite: bool = False,
        max_bytes: int | None = None,
    ) -> FilesystemResult:
        """Byte-exact copy of a workspace file. Binary-safe; no text encoding."""
        source_policy = self._evaluate_path_policy(operation="copy_path", path=source, action=IntentAction.READ)
        if source_policy is not None:
            return source_policy
        destination_policy = self._evaluate_path_policy(
            operation="copy_path",
            path=destination,
            action=IntentAction.WRITE,
        )
        if destination_policy is not None:
            return destination_policy
        effective_max = max_bytes if max_bytes is not None and max_bytes > 0 else self.max_binary_bytes
        return self._copy_path(source, destination, overwrite=overwrite, max_bytes=effective_max)

    def read_binary(
        self,
        path: str | os.PathLike[str],
        *,
        max_bytes: int | None = None,
    ) -> FilesystemResult:
        """Read a workspace file as raw bytes and return base64-encoded content."""
        effective_max = max_bytes if max_bytes is not None and max_bytes > 0 else self.max_binary_bytes
        return self._execute(
            operation="read_binary",
            path=path,
            action=IntentAction.READ,
            adapter_call=lambda: self._read_binary(path, effective_max),
        )

    def write_binary(
        self,
        path: str | os.PathLike[str],
        content_base64: str,
        *,
        mode: WriteMode = "rewrite",
        max_bytes: int | None = None,
    ) -> FilesystemResult:
        """Write raw bytes (decoded from base64) to a workspace file."""
        if mode not in {"rewrite", "append"}:
            return self._denied_result("write_binary", path, "Unsupported write mode.", ("NFR-002",))
        effective_max = max_bytes if max_bytes is not None and max_bytes > 0 else self.max_binary_bytes
        return self._execute(
            operation="write_binary",
            path=path,
            action=IntentAction.WRITE,
            adapter_call=lambda: self._write_binary(path, content_base64, mode, effective_max),
        )

    def replace_text(
        self,
        path: str | os.PathLike[str],
        search: str,
        replacement: str,
        *,
        expected_replacements: int = 1,
        encoding: str = "utf-8",
    ) -> FilesystemResult:
        if not search:
            return self._denied_result("replace_text", path, "Search text must not be empty.", ("FR-CMD-001", "NFR-002"))
        if expected_replacements < 1:
            return self._denied_result(
                "replace_text",
                path,
                "expected_replacements must be at least 1.",
                ("FR-CMD-001", "NFR-002"),
            )
        return self._execute(
            operation="replace_text",
            path=path,
            action=IntentAction.WRITE,
            adapter_call=lambda: self._replace_text(path, search, replacement, expected_replacements, encoding),
        )

    def file_info(self, path: str | os.PathLike[str]) -> FilesystemResult:
        return self._execute(
            operation="file_info",
            path=path,
            action=IntentAction.READ,
            adapter_call=lambda: self._file_info(path),
        )

    def search_text(
        self,
        path: str | os.PathLike[str],
        query: str,
        *,
        max_results: int | None = None,
        encoding: str = "utf-8",
    ) -> FilesystemResult:
        if not query:
            return self._denied_result("search_text", path, "Search query is required.", ("NFR-002",))

        return self._execute(
            operation="search_text",
            path=path,
            action=IntentAction.READ,
            adapter_call=lambda: self._search_text(path, query, max_results, encoding),
        )

    def _execute(
        self,
        *,
        operation: str,
        path: str | os.PathLike[str],
        action: IntentAction,
        adapter_call: Callable[[], FilesystemResult],
    ) -> FilesystemResult:
        intent = PolicyIntent(
            tool_name=f"plwc_workspace_{operation}",
            action=action,
            target_path=os.fspath(path),
            metadata={
                "allowed_roots": self.allowed_roots,
                "base_dir": self.base_dir,
                "protected_patterns": self.protected_path_patterns,
                "pattern_base_dir": self.project_root or self.base_dir,
            },
        )
        execution = execute_with_policy(intent, adapter_call, self.policy_engine)
        if not execution.executed:
            return FilesystemResult(
                ok=False,
                operation=operation,
                policy_decision=execution.policy.decision,
                path=os.fspath(path),
                error=execution.policy.reason,
                requirement_ids=execution.policy.requirement_ids,
            )
        return execution.adapter_result

    def _read_text(self, path: str | os.PathLike[str], encoding: str) -> FilesystemResult:
        guarded = self._guard(path, "read_file", "read")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            content = resolved.read_text(encoding=encoding)
        except Exception as exc:
            return self._adapter_error("read_file", path, exc)

        return FilesystemResult(
            ok=True,
            operation="read_file",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            content=content,
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _write_text(
        self,
        path: str | os.PathLike[str],
        content: str,
        mode: WriteMode,
        encoding: str,
    ) -> FilesystemResult:
        operation = "append" if mode == "append" else "write"
        guarded = self._guard(path, "write_file", operation)
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))

        try:
            if mode == "append":
                with resolved.open("a", encoding=encoding) as handle:
                    handle.write(content)
            else:
                resolved.write_text(content, encoding=encoding)
        except Exception as exc:
            return self._adapter_error("write_file", path, exc)

        return FilesystemResult(
            ok=True,
            operation="write_file",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            bytes_written=len(content.encode(encoding)),
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _create_directory(self, path: str | os.PathLike[str]) -> FilesystemResult:
        guarded = self._guard(path, "create_directory", "create")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return self._adapter_error("create_directory", path, exc)
        return FilesystemResult(
            ok=True,
            operation="create_directory",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _move_path(
        self,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        overwrite: bool,
    ) -> FilesystemResult:
        guarded_source = self._guard(source, "move_path", "move")
        if isinstance(guarded_source, FilesystemResult):
            return guarded_source
        guarded_destination = self._guard(destination, "move_path", "move")
        if isinstance(guarded_destination, FilesystemResult):
            return guarded_destination
        resolved_source = Path(guarded_source.absolute_path or os.fspath(source))
        resolved_destination = Path(guarded_destination.absolute_path or os.fspath(destination))
        try:
            if not resolved_source.exists():
                return self._adapter_error("move_path", source, FileNotFoundError(str(resolved_source)))
            if resolved_destination.exists() and not overwrite:
                return self._denied_result(
                    "move_path",
                    destination,
                    "Destination already exists; overwrite is false.",
                    ("FR-CMD-001", "NFR-002"),
                )
            if overwrite:
                resolved_source.replace(resolved_destination)
            else:
                resolved_source.rename(resolved_destination)
        except Exception as exc:
            return self._adapter_error("move_path", source, exc)
        return FilesystemResult(
            ok=True,
            operation="move_path",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved_destination),
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _copy_path(
        self,
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        overwrite: bool,
        max_bytes: int,
    ) -> FilesystemResult:
        guarded_source = self._guard(source, "copy_path", "read")
        if isinstance(guarded_source, FilesystemResult):
            return guarded_source
        guarded_destination = self._guard(destination, "copy_path", "write")
        if isinstance(guarded_destination, FilesystemResult):
            return guarded_destination
        resolved_source = Path(guarded_source.absolute_path or os.fspath(source))
        resolved_destination = Path(guarded_destination.absolute_path or os.fspath(destination))
        try:
            if not resolved_source.exists():
                return self._denied_result(
                    "copy_path",
                    source,
                    f"Source file does not exist: {resolved_source}",
                    ("FR-CMD-001", "NFR-002"),
                )
            if not resolved_source.is_file():
                return self._denied_result(
                    "copy_path",
                    source,
                    "copy_path only supports files; source is not a regular file.",
                    ("FR-CMD-001", "NFR-002"),
                )
            source_size = resolved_source.stat().st_size
            if source_size > max_bytes:
                return self._denied_result(
                    "copy_path",
                    source,
                    f"Source file exceeds workspace_binary_max_bytes ({source_size} > {max_bytes}).",
                    ("FR-CMD-001", "NFR-002"),
                )
            if resolved_destination.exists() and not overwrite:
                return self._denied_result(
                    "copy_path",
                    destination,
                    "Destination already exists; overwrite is false.",
                    ("FR-CMD-001", "NFR-002"),
                )
            shutil.copy2(resolved_source, resolved_destination)
            written_size = resolved_destination.stat().st_size
            source_hash = _sha256_of_file(resolved_source)
            target_hash = _sha256_of_file(resolved_destination)
        except Exception as exc:
            return self._adapter_error("copy_path", source, exc)
        return FilesystemResult(
            ok=True,
            operation="copy_path",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved_destination),
            source_path=str(resolved_source),
            target_path=str(resolved_destination),
            bytes_written=written_size,
            binary_data={
                "source_sha256": source_hash,
                "target_sha256": target_hash,
                "source_bytes": source_size,
                "target_bytes": written_size,
            },
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _read_binary(
        self,
        path: str | os.PathLike[str],
        max_bytes: int,
    ) -> FilesystemResult:
        guarded = self._guard(path, "read_binary", "read")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            if not resolved.exists():
                return self._denied_result(
                    "read_binary",
                    path,
                    f"File does not exist: {resolved}",
                    ("FR-CMD-001", "NFR-002"),
                )
            if not resolved.is_file():
                return self._denied_result(
                    "read_binary",
                    path,
                    "read_binary only supports files.",
                    ("FR-CMD-001", "NFR-002"),
                )
            size = resolved.stat().st_size
            if size > max_bytes:
                return self._denied_result(
                    "read_binary",
                    path,
                    f"File exceeds workspace_binary_max_bytes ({size} > {max_bytes}).",
                    ("FR-CMD-001", "NFR-002"),
                )
            raw = resolved.read_bytes()
        except Exception as exc:
            return self._adapter_error("read_binary", path, exc)
        encoded = base64.b64encode(raw).decode("ascii")
        sha256 = hashlib.sha256(raw).hexdigest()
        return FilesystemResult(
            ok=True,
            operation="read_binary",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            binary_data={
                "content_base64": encoded,
                "size": size,
                "sha256": sha256,
                "max_bytes": max_bytes,
            },
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _write_binary(
        self,
        path: str | os.PathLike[str],
        content_base64: str,
        mode: WriteMode,
        max_bytes: int,
    ) -> FilesystemResult:
        guarded = self._guard(path, "write_binary", "write" if mode == "rewrite" else "append")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            return self._denied_result(
                "write_binary",
                path,
                f"content_base64 is not valid base64: {exc}",
                ("FR-CMD-001", "NFR-002"),
            )
        if len(raw) > max_bytes:
            return self._denied_result(
                "write_binary",
                path,
                f"Decoded payload exceeds workspace_binary_max_bytes ({len(raw)} > {max_bytes}).",
                ("FR-CMD-001", "NFR-002"),
            )
        try:
            if mode == "append":
                # Enforce limit also on the resulting file when appending.
                existing_size = resolved.stat().st_size if resolved.exists() else 0
                if existing_size + len(raw) > max_bytes:
                    return self._denied_result(
                        "write_binary",
                        path,
                        f"Appended file would exceed workspace_binary_max_bytes ({existing_size + len(raw)} > {max_bytes}).",
                        ("FR-CMD-001", "NFR-002"),
                    )
                with resolved.open("ab") as handle:
                    handle.write(raw)
            else:
                resolved.write_bytes(raw)
            written_size = resolved.stat().st_size
        except Exception as exc:
            return self._adapter_error("write_binary", path, exc)
        return FilesystemResult(
            ok=True,
            operation="write_binary",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            bytes_written=written_size,
            binary_data={
                "bytes_written": len(raw),
                "file_size": written_size,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "max_bytes": max_bytes,
                "mode": mode,
            },
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _replace_text(
        self,
        path: str | os.PathLike[str],
        search: str,
        replacement: str,
        expected_replacements: int,
        encoding: str,
    ) -> FilesystemResult:
        guarded = self._guard(path, "replace_text", "write")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            content = resolved.read_text(encoding=encoding)
            count = content.count(search)
            if count != expected_replacements:
                return self._denied_result(
                    "replace_text",
                    path,
                    f"Expected {expected_replacements} replacement(s), found {count}.",
                    ("FR-CMD-001", "NFR-002"),
                )
            updated = content.replace(search, replacement)
            self._write_text_atomic(resolved, updated, encoding)
        except Exception as exc:
            return self._adapter_error("replace_text", path, exc)
        return FilesystemResult(
            ok=True,
            operation="replace_text",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            bytes_written=len(updated.encode(encoding)),
            replacements=count,
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _write_text_atomic(self, path: Path, content: str, encoding: str) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding=encoding,
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".plwc-tmp",
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            temp_path.replace(path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _file_info(self, path: str | os.PathLike[str]) -> FilesystemResult:
        guarded = self._guard(path, "file_info", "read")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        try:
            entry = _entry_for_path(resolved)
            stat_result = resolved.stat()
        except Exception as exc:
            return self._adapter_error("file_info", path, exc)
        info = {
            "path": str(resolved),
            "kind": entry.kind,
            "size": entry.size,
            "extension": resolved.suffix.casefold(),
            "name": resolved.name,
            "modified_time_ns": stat_result.st_mtime_ns,
            "created_time_ns": stat_result.st_ctime_ns,
        }
        return FilesystemResult(
            ok=True,
            operation="file_info",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            info=info,
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _list_directory(self, path: str | os.PathLike[str], depth: int) -> FilesystemResult:
        if depth < 1:
            return self._denied_result("list_directory", path, "Directory depth must be at least 1.", ("NFR-002",))

        guarded = self._guard(path, "list_directory", "read")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))

        try:
            if not resolved.is_dir():
                return self._adapter_error("list_directory", path, NotADirectoryError(str(resolved)))
            entries = tuple(self._collect_entries(resolved, depth))
        except Exception as exc:
            return self._adapter_error("list_directory", path, exc)

        return FilesystemResult(
            ok=True,
            operation="list_directory",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            entries=entries,
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _search_text(
        self,
        path: str | os.PathLike[str],
        query: str,
        max_results: int | None,
        encoding: str,
    ) -> FilesystemResult:
        guarded = self._guard(path, "search_text", "read")
        if isinstance(guarded, FilesystemResult):
            return guarded
        resolved = Path(guarded.absolute_path or os.fspath(path))
        result_limit = min(max_results or self.max_search_results, self.max_search_results)

        try:
            collected, search_stats = self._collect_matches(resolved, query, result_limit, encoding)
        except Exception as exc:
            return self._adapter_error("search_text", path, exc)

        return FilesystemResult(
            ok=True,
            operation="search_text",
            policy_decision=PolicyDecision.ALLOW,
            path=str(resolved),
            matches=tuple(collected),
            search_stats=search_stats,
            requirement_ids=COMMANDER_WORKSPACE_REQUIREMENTS,
        )

    def _evaluate_path_policy(
        self,
        *,
        operation: str,
        path: str | os.PathLike[str],
        action: IntentAction,
    ) -> FilesystemResult | None:
        intent = PolicyIntent(
            tool_name=f"plwc_workspace_{operation}",
            action=action,
            target_path=os.fspath(path),
            metadata={
                "allowed_roots": self.allowed_roots,
                "base_dir": self.base_dir,
                "protected_patterns": self.protected_path_patterns,
                "pattern_base_dir": self.project_root or self.base_dir,
            },
        )
        policy = evaluate_intent(intent, self.policy_engine)
        if policy.allowed:
            return None
        return FilesystemResult(
            ok=False,
            operation=operation,
            policy_decision=policy.decision,
            path=os.fspath(path),
            error=policy.reason,
            requirement_ids=policy.requirement_ids,
        )

    def _guard(
        self,
        path: str | os.PathLike[str],
        operation_name: str,
        path_operation: str,
    ) -> PathPolicyResult | FilesystemResult:
        result = guard_path(
            path,
            self.allowed_roots,
            base_dir=self.base_dir,
            operation=path_operation,
            protected_patterns=self.protected_path_patterns,
            pattern_base_dir=self.project_root or self.base_dir,
        )
        if result.allowed:
            return result
        return FilesystemResult(
            ok=False,
            operation=operation_name,
            policy_decision=result.decision,
            path=os.fspath(path),
            error=result.reason,
            requirement_ids=result.requirement_ids,
        )

    def _collect_entries(self, root: Path, depth: int) -> list[FilesystemEntry]:
        entries: list[FilesystemEntry] = []

        def visit(current: Path, remaining_depth: int) -> None:
            if remaining_depth <= 0 or len(entries) >= self.max_list_entries:
                return
            for entry in sorted(current.iterdir(), key=lambda item: item.name.casefold()):
                if len(entries) >= self.max_list_entries:
                    return
                guarded = self._guard(entry, "list_directory", "read")
                if isinstance(guarded, FilesystemResult):
                    continue

                entries.append(_entry_for_path(entry))
                if entry.is_dir():
                    visit(entry, remaining_depth - 1)

        visit(root, depth)
        return entries

    def _collect_matches(
        self,
        root: Path,
        query: str,
        max_results: int,
        encoding: str,
    ) -> tuple[list[FilesystemSearchMatch], dict[str, Any]]:
        # RC12-FS-003 — bound the walk: skip oversized and binary files, prune
        # excluded directories, and cap how many files are content-scanned. The
        # caller always learns what was skipped (search_stats) so a search never
        # silently passes over the file holding the answer.
        matches: list[FilesystemSearchMatch] = []
        skipped = {"too_large": 0, "binary": 0, "unreadable": 0}
        scanned_files = 0
        scan_cap_reached = False
        result_limit_reached = False

        candidates: Iterator[Path] = (
            iter([root]) if root.is_file() else _walk_files(root, self.search_excluded_dirs)
        )
        for candidate in candidates:
            if len(matches) >= max_results:
                result_limit_reached = True
                break
            if scanned_files >= self.max_search_files_scanned:
                scan_cap_reached = True
                break
            guarded = self._guard(candidate, "search_text", "read")
            if isinstance(guarded, FilesystemResult):
                continue
            try:
                file_size = candidate.stat().st_size
            except OSError:
                skipped["unreadable"] += 1
                continue
            if file_size > self.max_search_file_bytes:
                skipped["too_large"] += 1
                continue
            if self._is_binary(candidate):
                skipped["binary"] += 1
                continue
            scanned_files += 1
            try:
                with candidate.open("r", encoding=encoding) as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if query in line:
                            matches.append(
                                FilesystemSearchMatch(
                                    path=str(candidate),
                                    line_number=line_number,
                                    line=line.rstrip("\r\n"),
                                )
                            )
                            if len(matches) >= max_results:
                                result_limit_reached = True
                                break
            except (UnicodeDecodeError, OSError):
                # Binary content past the probe window, or a transient read error:
                # the file was examined; treat it as non-matching and move on.
                continue

        stats = {
            "scanned_files": scanned_files,
            "skipped_files": dict(skipped),
            "skipped_total": sum(skipped.values()),
            "excluded_dirs": sorted(self.search_excluded_dirs),
            "max_file_bytes": self.max_search_file_bytes,
            "max_files_scanned": self.max_search_files_scanned,
            "truncated": scan_cap_reached,
            "result_limit_reached": result_limit_reached,
        }
        return matches, stats

    def _is_binary(self, path: Path) -> bool:
        """A NUL byte in the head window marks the file as binary (skip it)."""
        try:
            with path.open("rb") as handle:
                return b"\x00" in handle.read(_SEARCH_BINARY_PROBE_BYTES)
        except OSError:
            return False

    def _denied_result(
        self,
        operation: str,
        path: str | os.PathLike[str],
        reason: str,
        requirement_ids: tuple[str, ...],
    ) -> FilesystemResult:
        return FilesystemResult(
            ok=False,
            operation=operation,
            policy_decision=PolicyDecision.DENY,
            path=os.fspath(path),
            error=reason,
            requirement_ids=requirement_ids,
        )

    def _adapter_error(
        self,
        operation: str,
        path: str | os.PathLike[str],
        exc: Exception,
    ) -> FilesystemResult:
        return FilesystemResult(
            ok=False,
            operation=operation,
            policy_decision=PolicyDecision.ALLOW,
            path=os.fspath(path),
            error=str(exc),
            requirement_ids=("NFR-002",),
        )


def _coerce_roots(
    allowed_roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
) -> tuple[str | os.PathLike[str], ...]:
    if allowed_roots is None:
        return ()
    if isinstance(allowed_roots, (str, os.PathLike)):
        return (allowed_roots,)
    return tuple(allowed_roots)


def _entry_for_path(path: Path) -> FilesystemEntry:
    try:
        stat_result = path.stat()
        size = stat_result.st_size
    except OSError:
        size = None

    if path.is_dir():
        kind: EntryKind = "directory"
    elif path.is_file():
        kind = "file"
    else:
        kind = "other"

    return FilesystemEntry(path=str(path), kind=kind, size=size)


def _walk_files(root: Path, excluded_dirs: frozenset[str]) -> Iterator[Path]:
    # RC12-FS-003 — prune excluded directories in place (os.walk honours edits to
    # dir_names) and stream paths lazily so a capped search never materialises the
    # whole tree.
    for current_root, dir_names, file_names in os.walk(root, followlinks=False):
        dir_names[:] = sorted(
            (name for name in dir_names if name.casefold() not in excluded_dirs),
            key=str.casefold,
        )
        file_names.sort(key=str.casefold)
        for file_name in file_names:
            yield Path(current_root) / file_name


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
