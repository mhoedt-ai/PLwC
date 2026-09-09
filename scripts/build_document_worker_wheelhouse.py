from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = ROOT / "docker" / "document-worker"
WHEELHOUSE = WORKER_ROOT / "wheelhouse"
VENDORED_WHEELHOUSE = WORKER_ROOT / "vendored-wheels"
LOCK = WORKER_ROOT / "requirements-doc-worker.lock"
MANIFEST_JSON = WORKER_ROOT / "wheelhouse-manifest.json"
PLATFORM = "manylinux_2_28_x86_64"
COMPATIBLE_PLATFORMS = (PLATFORM, "manylinux2014_x86_64")
PYTHON_VERSION = "312"
ABI = "cp312"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _locked_entries() -> list[dict[str, str]]:
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8-sig"))
    entries = manifest.get("wheels")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Wheelhouse manifest has no locked wheels")
    required = {"package", "version", "filename", "sha256", "source"}
    for entry in entries:
        if not isinstance(entry, dict) or not required.issubset(entry):
            raise ValueError("Wheelhouse manifest contains an incomplete entry")
        if entry["source"] not in {"pip download", "vendored"}:
            raise ValueError(f"Unsupported locked wheel source: {entry['source']}")
    filenames = [entry["filename"] for entry in entries]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Wheelhouse manifest contains duplicate filenames")
    return entries


def _download(clean: bool) -> None:
    entries = _locked_entries()
    if clean and WHEELHOUSE.exists():
        for path in WHEELHOUSE.iterdir():
            if path.name != ".gitkeep":
                path.unlink() if path.is_file() else shutil.rmtree(path)
    WHEELHOUSE.mkdir(parents=True, exist_ok=True)
    downloadable = [entry for entry in entries if entry["source"] == "pip download"]
    with tempfile.TemporaryDirectory(prefix="plwc-wheelhouse-") as temporary:
        input_path = Path(temporary) / "requirements-locked.txt"
        input_path.write_text(
            "\n".join(
                f"{entry['package']}=={entry['version']} --hash=sha256:{entry['sha256']}"
                for entry in downloadable
            )
            + "\n",
            encoding="utf-8",
        )
        command = [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--require-hashes",
                "--no-deps",
                "--only-binary=:all:",
                "--implementation",
                "cp",
                "--python-version",
                PYTHON_VERSION,
                "--abi",
                ABI,
                "--dest",
                str(WHEELHOUSE),
                "--requirement",
                str(input_path),
            ]
        for platform in COMPATIBLE_PLATFORMS:
            command.extend(("--platform", platform))
        subprocess.run(
            command,
            check=True,
            cwd=ROOT,
        )
    for entry in entries:
        if entry["source"] != "vendored":
            continue
        source = VENDORED_WHEELHOUSE / entry["filename"]
        if not source.is_file() or _sha256(source) != entry["sha256"]:
            raise ValueError(f"Vendored wheel is missing or has the wrong hash: {entry['filename']}")
        shutil.copy2(source, WHEELHOUSE / entry["filename"])


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
