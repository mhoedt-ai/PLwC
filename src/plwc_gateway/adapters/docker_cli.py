"""Resolve the local Docker CLI without relying on a freshly inherited PATH."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def resolve_docker_executable() -> str | None:
    configured = os.environ.get("PLWC_DOCKER_EXE", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute() and candidate.is_file():
            return str(candidate.resolve(strict=False))

    discovered = shutil.which("docker")
    if discovered:
        return discovered

    if sys.platform != "win32":
        return None

    candidates = (
        _program_files_candidate(os.environ.get("ProgramFiles")),
        _program_files_candidate(os.environ.get("ProgramW6432")),
        _local_app_data_candidate(
            os.environ.get("LOCALAPPDATA"),
            Path("Programs") / "DockerDesktop" / "resources" / "bin" / "docker.exe",
        ),
        _local_app_data_candidate(
            os.environ.get("LOCALAPPDATA"),
            Path("Programs") / "Docker" / "Docker" / "resources" / "bin" / "docker.exe",
        ),
    )
    seen: set[str] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return str(candidate.resolve(strict=False))
    return None


def _program_files_candidate(root: str | None) -> Path | None:
    if not root:
        return None
    return Path(root) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"


def _local_app_data_candidate(root: str | None, relative_path: Path) -> Path | None:
    if not root:
        return None
    return Path(root) / relative_path
