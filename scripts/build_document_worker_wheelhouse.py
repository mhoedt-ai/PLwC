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
REQUIREMENTS = WORKER_ROOT / "requirements-doc-worker.txt"
LOCK = WORKER_ROOT / "requirements-doc-worker.lock"
MANIFEST_JSON = WORKER_ROOT / "wheelhouse-manifest.json"
MANIFEST_CSV = WORKER_ROOT / "wheelhouse-manifest.csv"
PLATFORM = "manylinux2014_x86_64"
PYTHON_VERSION = "312"
ABI = "cp312"


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


def _wheel_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(WHEELHOUSE.glob("*.whl"), key=lambda item: item.name.casefold()):
        package, version, python_tag, abi_tag, platform_tag = _metadata(path)
        entries.append(
            {
                "package": package.lower().replace("_", "-"),
                "version": version,
                "filename": path.name,
                "sha256": _sha256(path),
                "python_tag": python_tag,
                "abi_tag": abi_tag,
                "platform_tag": platform_tag,
                "source": "pip wheel" if package.lower() == "odfpy" else "pip download",
            }
        )
    if not entries:
        raise ValueError(f"No wheels found under {WHEELHOUSE}")
    return entries


def _write_outputs(entries: list[dict[str, Any]]) -> None:
    lock_lines = [
        "# PLwC Document Worker lock input.",
        "# Generated from the offline wheelhouse by scripts/build_document_worker_wheelhouse.py.",
        "# This file is build-time input only. Runtime document operations must not run pip.",
        "# image: ghcr.io/mhoedt-ai/plwc-document-worker:0.1.0",
        f"# target_platform: {PLATFORM}",
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
        "image": "ghcr.io/mhoedt-ai/plwc-document-worker:0.1.0",
        "target_platform": PLATFORM,
        "python_version": PYTHON_VERSION,
        "abi": ABI,
        "requirements_file": REQUIREMENTS.name,
        "lock_file": LOCK.name,
        "wheelhouse_path": "docker/document-worker/wheelhouse",
        "wheels": entries,
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    with MANIFEST_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("package", "version", "filename", "sha256", "python_tag", "abi_tag", "platform_tag", "source"))
        writer.writeheader()
        writer.writerows(entries)


def _download(clean: bool) -> None:
    if clean and WHEELHOUSE.exists():
        for path in WHEELHOUSE.iterdir():
            if path.name != ".gitkeep":
                path.unlink() if path.is_file() else shutil.rmtree(path)
    WHEELHOUSE.mkdir(parents=True, exist_ok=True)
    requirements = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    binary_requirements = [line for line in requirements if not line.lower().startswith("odfpy==")]
    with tempfile.TemporaryDirectory(prefix="plwc-wheelhouse-") as temporary:
        input_path = Path(temporary) / "requirements-binary.txt"
        input_path.write_text("\n".join(binary_requirements) + "\n", encoding="utf-8")
        subprocess.run(
            [
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
                "--platform",
                PLATFORM,
                "--dest",
                str(WHEELHOUSE),
                "--requirement",
                str(input_path),
            ],
            check=True,
            cwd=ROOT,
        )
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(WHEELHOUSE), "odfpy==1.4.1"],
            check=True,
            cwd=ROOT,
        )
    _write_outputs(_wheel_entries())


def _verify() -> None:
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8-sig"))
    expected = {entry["filename"]: entry for entry in manifest.get("wheels", [])}
    observed = {path.name: path for path in WHEELHOUSE.glob("*.whl")}
    if set(expected) != set(observed):
        raise ValueError(
            f"Wheelhouse inventory mismatch: missing={sorted(set(expected) - set(observed))}, "
            f"unexpected={sorted(set(observed) - set(expected))}"
        )
    for name, path in observed.items():
        if _sha256(path) != expected[name]["sha256"]:
            raise ValueError(f"Wheel hash mismatch: {name}")
    lock = LOCK.read_text(encoding="utf-8")
    for entry in expected.values():
        expected_line = f"{entry['package']}=={entry['version']} --hash=sha256:{entry['sha256']}"
        if expected_line not in lock:
            raise ValueError(f"Wheel lock entry missing: {entry['filename']}")
    print(f"Verified {len(observed)} Document Worker wheels ({sum(path.stat().st_size for path in observed.values())} bytes).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the PLwC Document Worker offline wheelhouse")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.clean and not args.download:
        parser.error("--clean is allowed only together with --download")
    if args.download:
        _download(args.clean)
    _verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
