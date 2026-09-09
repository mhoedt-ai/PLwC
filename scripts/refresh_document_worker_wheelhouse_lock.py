from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = ROOT / "docker" / "document-worker"
WHEELHOUSE = WORKER_ROOT / "wheelhouse"
VENDORED_WHEELHOUSE = WORKER_ROOT / "vendored-wheels"
REQUIREMENTS = WORKER_ROOT / "requirements-doc-worker.txt"
LOCK = WORKER_ROOT / "requirements-doc-worker.lock"
MANIFEST_JSON = WORKER_ROOT / "wheelhouse-manifest.json"
MANIFEST_CSV = WORKER_ROOT / "wheelhouse-manifest.csv"
PRIMARY_PLATFORM = "manylinux_2_28_x86_64"
COMPATIBLE_PLATFORMS = (PRIMARY_PLATFORM, "manylinux2014_x86_64")
PYTHON_VERSION = "312"
ABI = "cp312"


def _canonical_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(".", "-")


def _pinned_requirement(line: str) -> tuple[str, str]:
    requirement = line.split(" --hash=", 1)[0].strip()
    if "==" not in requirement:
        raise ValueError(f"Requirement is not exactly pinned: {line}")
    name, version = requirement.split("==", 1)
    if not name.strip() or not version.strip():
        raise ValueError(f"Requirement is incomplete: {line}")
    return _canonical_name(name), version.strip()


def _requirements() -> list[tuple[str, str]]:
    values = []
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            values.append(_pinned_requirement(line))
    if not values:
        raise ValueError("Document Worker requirements are empty")
    if len({name for name, _ in values}) != len(values):
        raise ValueError("Document Worker requirements contain duplicate packages")
    return values


def _constraints(direct_names: set[str]) -> list[str]:
    constraints = []
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "--")):
            continue
        name, _ = _pinned_requirement(line)
        if name not in direct_names:
            constraints.append(line.split(" --hash=", 1)[0])
    return constraints


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _metadata(path: Path) -> tuple[str, str, str, str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        wheel_name = next(name for name in archive.namelist() if name.endswith(".dist-info/WHEEL"))
        metadata = archive.read(metadata_name).decode("utf-8", errors="strict")
        wheel = archive.read(wheel_name).decode("utf-8", errors="strict")
    fields: dict[str, str] = {}
    for line in metadata.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields.setdefault(key, value)
        if "Name" in fields and "Version" in fields:
            break
    tags = [line.split(": ", 1)[1] for line in wheel.splitlines() if line.startswith("Tag: ")]
    if not fields.get("Name") or not fields.get("Version") or not tags:
        raise ValueError(f"Wheel metadata is incomplete: {path.name}")
    python_tag, abi_tag, platform_tag = tags[0].split("-", 2)
    return fields["Name"], fields["Version"], python_tag, abi_tag, platform_tag


def _source_date() -> str:
    raw = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if not raw:
        completed = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        raw = completed.stdout.strip()
    return datetime.fromtimestamp(int(raw), tz=timezone.utc).isoformat(timespec="seconds")


def _wheel_entries(directory: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.whl"), key=lambda item: item.name.casefold()):
        package, version, python_tag, abi_tag, platform_tag = _metadata(path)
        canonical = _canonical_name(package)
        entries.append(
            {
                "package": canonical,
                "version": version,
                "filename": path.name,
                "sha256": _sha256(path),
                "python_tag": python_tag,
                "abi_tag": abi_tag,
                "platform_tag": platform_tag,
                "source": "vendored" if canonical == "odfpy" else "pip download",
            }
        )
    if not entries:
        raise ValueError("The refreshed wheelhouse is empty")
    return entries


def _write_outputs(entries: list[dict[str, Any]]) -> None:
    lock_lines = [
        "# PLwC Document Worker lock input.",
        "# Refreshed explicitly by scripts/refresh_document_worker_wheelhouse_lock.py.",
        "# This file is build-time input only. Runtime document operations must not run pip.",
        "# image: plwc-document-worker:0.1.0",
        f"# target_platform: {PRIMARY_PLATFORM}",
        f"# python_version: {PYTHON_VERSION}",
        f"# abi: {ABI}",
        "--only-binary=:all:",
        "",
    ]
    lock_lines.extend(f"{entry['package']}=={entry['version']} --hash=sha256:{entry['sha256']}" for entry in entries)
    LOCK.write_text("\n".join(lock_lines) + "\n", encoding="utf-8", newline="\n")

    manifest = {
        "schema_version": 1,
        "generated_at_utc": _source_date(),
        "image": "plwc-document-worker:0.1.0",
        "target_platform": PRIMARY_PLATFORM,
        "python_version": PYTHON_VERSION,
        "abi": ABI,
        "requirements_file": REQUIREMENTS.name,
        "lock_file": LOCK.name,
        "wheelhouse_path": "docker/document-worker/wheelhouse",
        "wheels": entries,
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    with MANIFEST_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("package", "version", "filename", "sha256", "python_tag", "abi_tag", "platform_tag", "source"),
        )
        writer.writeheader()
        writer.writerows(entries)


def _refresh() -> None:
    requirements = _requirements()
    direct_names = {name for name, _ in requirements}
    binary_requirements = [f"{name}=={version}" for name, version in requirements if name != "odfpy"]
    with tempfile.TemporaryDirectory(prefix="plwc-wheelhouse-refresh-") as temporary:
        directory = Path(temporary)
        input_path = directory / "requirements-binary.txt"
        constraints_path = directory / "constraints-existing.txt"
        download_path = directory / "wheelhouse"
        input_path.write_text("\n".join(binary_requirements) + "\n", encoding="utf-8")
        constraints_path.write_text("\n".join(_constraints(direct_names)) + "\n", encoding="utf-8")
        download_path.mkdir()
        command = [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--only-binary=:all:",
            "--implementation",
            "cp",
            "--python-version",
            PYTHON_VERSION,
            "--abi",
            ABI,
            "--dest",
            str(download_path),
            "--requirement",
            str(input_path),
            "--constraint",
            str(constraints_path),
        ]
        for platform in COMPATIBLE_PLATFORMS:
            command.extend(("--platform", platform))
        subprocess.run(command, check=True, cwd=ROOT)

        vendored = VENDORED_WHEELHOUSE / "odfpy-1.4.1-py2.py3-none-any.whl"
        if not vendored.is_file():
            raise ValueError(f"Vendored odfpy wheel is missing: {vendored}")
        shutil.copy2(vendored, download_path / vendored.name)

        entries = _wheel_entries(download_path)
        observed = {entry["package"]: entry["version"] for entry in entries}
        missing_or_changed = {
            name: {"expected": version, "observed": observed.get(name)}
            for name, version in requirements
            if observed.get(name) != version
        }
        if missing_or_changed:
            raise ValueError(f"Refreshed wheelhouse does not match direct requirements: {missing_or_changed}")

        WHEELHOUSE.mkdir(parents=True, exist_ok=True)
        for path in WHEELHOUSE.iterdir():
            if path.name != ".gitkeep":
                path.unlink() if path.is_file() else shutil.rmtree(path)
        for path in download_path.glob("*.whl"):
            shutil.copy2(path, WHEELHOUSE / path.name)
        _write_outputs(entries)
        print(f"Refreshed {len(entries)} locked Document Worker wheels.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicitly refresh the PLwC Document Worker wheel lock")
    parser.add_argument(
        "--accept-mutable-resolution",
        action="store_true",
        help="Acknowledge that package resolution may change the committed wheel lock",
    )
    args = parser.parse_args()
    if not args.accept_mutable_resolution:
        parser.error("--accept-mutable-resolution is required; normal builds must use the immutable builder")
    _refresh()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
