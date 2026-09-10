from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from test_runtime_image_manifest import valid_manifest


ROOT = Path(__file__).resolve().parents[2]
MANAGER_PATH = ROOT / "installer" / "windows" / "assets" / "runtime-image-manager.py"


def _load_manager():
    spec = importlib.util.spec_from_file_location("plwc_runtime_image_manager_execution_tests", MANAGER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


manager = _load_manager()


class FakeRunner:
    def __init__(self, *, present=(), fail_pull_id: str | None = None, fail_probe_id: str | None = None) -> None:
        self.present = set(present)
        self.fail_pull_id = fail_pull_id
        self.fail_probe_id = fail_probe_id
        self.calls: list[list[str]] = []

    @staticmethod
    def _result(command_id: str, *, ok: bool = True, stdout: str = "", exit_code: int = 0) -> dict:
        return {
            "ok": ok,
            "stdout": stdout,
            "stderr": "" if ok else "synthetic failure",
            "exit_code": exit_code,
            "cancelled": False,
            "timed_out": False,
            "report_path": f"reports/{command_id}.json",
        }

    def run(self, argv, *, phase: str, command_id: str, timeout_seconds: int, inactivity_timeout_seconds: int) -> dict:
        assert timeout_seconds >= inactivity_timeout_seconds >= 1
        args = list(argv)
        self.calls.append(args)
        if args[1] == "info":
            return self._result(command_id, stdout='"29.3.1"')
        if args[1:3] == ["image", "inspect"]:
            reference = args[-1]
            if reference not in self.present:
                return self._result(command_id, ok=False, exit_code=1)
            payload = {"Id": "sha256:" + "9" * 64, "RepoDigests": [reference], "Os": "linux", "Architecture": "amd64"}
            return self._result(command_id, stdout=json.dumps(payload))
        if args[1] == "pull":
            reference = args[-1]
            if self.fail_pull_id and self.fail_pull_id.replace("_", "-") in reference:
                return self._result(command_id, ok=False, exit_code=1)
            self.present.add(reference)
            return self._result(command_id, stdout="pulled by exact digest")
        if args[1] == "run":
            reference = next(value for value in args if value.startswith("ghcr.io/"))
            if self.fail_probe_id and self.fail_probe_id.replace("_", "-") in reference:
                return self._result(command_id, ok=False, exit_code=1)
            if "document-worker" in reference:
                output = json.dumps({"ok": True, "operation": "probe", "imports": {"pypdf": True, "Pillow": True}})
            elif "node-runner" in reference:
                output = "v22.22.3\n"
            else:
                output = "Python 3.12.13\n"
            return self._result(command_id, stdout=output)
        raise AssertionError(f"Unexpected fake Docker call: {args}")


def _image_manager(fake: FakeRunner, *, available_bytes: int = 10**12):
    return manager.RuntimeImageManager(
        valid_manifest(),
        Path("docker.exe"),
        fake,
        30,
        5,
        space_probe_path=Path.cwd(),
        free_space_provider=lambda _path: available_bytes,
    )


def test_all_missing_pulls_exact_digests_then_runs_hardened_probes() -> None:
    fake = FakeRunner()
    result = _image_manager(fake).acquire()
    assert result["state"] == "ready"
    assert [item["state"] for item in result["images"]] == ["probe_passed"] * 3
    pull_calls = [call for call in fake.calls if call[1] == "pull"]
    run_calls = [call for call in fake.calls if call[1] == "run"]
    assert len(pull_calls) == len(run_calls) == 3
    for call in pull_calls:
        assert call[2:4] == ["--platform", "linux/amd64"]
        assert "@sha256:" in call[-1]
    for call in run_calls:
        assert ["--pull", "never"] == call[call.index("--pull") : call.index("--pull") + 2]
        assert ["--network", "none"] == call[call.index("--network") : call.index("--network") + 2]
        assert "--read-only" in call and ["--cap-drop", "ALL"] == call[call.index("--cap-drop") : call.index("--cap-drop") + 2]
        assert ["--security-opt", "no-new-privileges"] == call[call.index("--security-opt") : call.index("--security-opt") + 2]


def test_matching_local_digests_skip_pull_but_not_probe() -> None:
    manifest = valid_manifest()
    refs = [image["reference"] for image in manifest["images"]]
    fake = FakeRunner(present=refs)
    result = manager.RuntimeImageManager(manifest, Path("docker.exe"), fake, 30, 5).acquire()
    assert result["ok"] is True
    assert not [call for call in fake.calls if call[1] == "pull"]
    assert len([call for call in fake.calls if call[1] == "run"]) == 3


def test_insufficient_disk_enters_safe_mode_before_first_pull() -> None:
    manifest = valid_manifest()
    required_bytes = sum(image["content_bytes"] for image in manifest["images"])
    fake = FakeRunner()
    with pytest.raises(manager.InsufficientDiskError) as captured:
        _image_manager(fake, available_bytes=required_bytes - 1).acquire()
    assert captured.value.category == "insufficient_disk"
    assert captured.value.disk_space == {
        "probe_path": str(Path.cwd().resolve()),
        "required_bytes": required_bytes,
        "available_bytes": required_bytes - 1,
        "sufficient": False,
    }
    assert [item["state"] for item in captured.value.images] == ["safe_mode"] * 3
    assert not [call for call in fake.calls if call[1] in {"pull", "run"}]


def test_disk_gate_counts_only_missing_images() -> None:
    manifest = valid_manifest()
    present_reference = manifest["images"][0]["reference"]
    required_bytes = sum(image["content_bytes"] for image in manifest["images"][1:])
    fake = FakeRunner(present=(present_reference,))
    runtime_manager = manager.RuntimeImageManager(
        manifest,
        Path("docker.exe"),
        fake,
        30,
        5,
        space_probe_path=Path.cwd(),
        free_space_provider=lambda _path: required_bytes,
    )
    result = runtime_manager.acquire()
    assert result["disk_space"]["required_bytes"] == required_bytes
    assert result["disk_space"]["sufficient"] is True
    assert len([call for call in fake.calls if call[1] == "pull"]) == 2


def test_all_present_images_do_not_require_a_disk_space_probe() -> None:
    manifest = valid_manifest()
    refs = [image["reference"] for image in manifest["images"]]
    fake = FakeRunner(present=refs)

    def fail_if_called(_path: Path) -> int:
        raise AssertionError("free-space probe must not run when no image is missing")

    result = manager.RuntimeImageManager(
        manifest,
        Path("docker.exe"),
        fake,
        30,
        5,
        space_probe_path=Path.cwd(),
        free_space_provider=fail_if_called,
    ).acquire()
    assert result["disk_space"] is None
    assert result["state"] == "ready"


def test_unavailable_disk_measurement_fails_closed_before_pull() -> None:
    fake = FakeRunner()

    def unavailable(_path: Path) -> int:
        raise OSError("synthetic disk probe failure")

    runtime_manager = manager.RuntimeImageManager(
        valid_manifest(),
        Path("docker.exe"),
        fake,
        30,
        5,
        space_probe_path=Path.cwd(),
        free_space_provider=unavailable,
    )
    with pytest.raises(manager.InsufficientDiskError) as captured:
        runtime_manager.acquire()
    assert captured.value.disk_space["available_bytes"] is None
    assert captured.value.disk_space["sufficient"] is False
    assert not [call for call in fake.calls if call[1] in {"pull", "run"}]


def test_pull_failure_stops_later_network_and_records_unattempted() -> None:
    fake = FakeRunner(fail_pull_id="node_runner")
    with pytest.raises(manager.PullVerificationError) as captured:
        _image_manager(fake).acquire()
    states = {item["id"]: item["state"] for item in captured.value.images}
    assert states == {"document_worker": "probe_passed", "node_runner": "safe_mode", "python_runner": "unattempted"}
    assert not any(
        call[1] in {"pull", "run"} and "python-runner" in " ".join(call)
        for call in fake.calls
    )


def test_probe_failure_never_becomes_ready() -> None:
    fake = FakeRunner(fail_probe_id="document_worker")
    with pytest.raises(manager.ProbeError) as captured:
        _image_manager(fake).acquire()
    assert captured.value.images[0]["state"] == "safe_mode"


def test_daemon_failure_is_not_reported_as_missing_images() -> None:
    class NoDaemon(FakeRunner):
        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            if list(argv)[1] == "info":
                return self._result(kwargs["command_id"], ok=False, exit_code=1)
            return result

    with pytest.raises(manager.DockerUnavailableError):
        _image_manager(NoDaemon()).inventory()


def test_process_runner_redacts_and_bounds_child_output(tmp_path: Path) -> None:
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27")
    result = runner.run(
        [
            sys.executable,
            "-c",
            "import sys; print('token=' + 'gh' + 'p_' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'); print('x'*70000); sys.exit(1)",
        ],
        phase="image_pull",
        command_id="synthetic-output",
        timeout_seconds=10,
        inactivity_timeout_seconds=5,
    )
    assert result["ok"] is False and result["exit_code"] == 1
    assert "ghp_" not in result["stdout"]
    assert result["stdout_truncated"] is True
    persisted = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
    assert persisted["report_id"] == result["report_id"]


def test_process_runner_timeout_writes_final_report(tmp_path: Path) -> None:
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27")
    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        phase="image_probe",
        command_id="synthetic-timeout",
        timeout_seconds=2,
        inactivity_timeout_seconds=1,
    )
    assert result["ok"] is False
    assert result["timed_out"] is True
    assert Path(result["report_path"]).is_file()


def test_successful_manager_report_uses_complete_diagnostic_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = valid_manifest()
    manifest_path = tmp_path / "runtime-images.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    docker_path = tmp_path / "docker.exe"
    docker_path.write_bytes(b"fixture")
    report_path = tmp_path / "runtime-image-report.json"

    class SuccessfulManager:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        @staticmethod
        def inventory() -> dict[str, object]:
            return {
                "ok": True,
                "phase": "image_inventory",
                "state": "inventory_complete",
                "images": [],
            }

    monkeypatch.setattr(manager, "RuntimeImageManager", SuccessfulManager)
    exit_code = manager.main(
        [
            "inventory",
            "--manifest",
            str(manifest_path),
            "--manifest-sha256",
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "--docker",
            str(docker_path),
            "--report",
            str(report_path),
            "--process-report-dir",
            str(tmp_path / "process-reports"),
            "--build-id",
            "fixture-installer-r27",
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["started"] is True
    assert report["exit_code"] == 0
    assert report["timed_out"] is False
    assert report["cancelled"] is False
    assert report["stdout"] == report["stderr"] == ""
    assert report["stdout_truncated"] is report["stderr_truncated"] is False
    assert report["exception_type"] is report["error_category"] is None
    assert report["command_id"] == "runtime-image-manager-inventory"
    assert report["started_at"] and report["finished_at"]
    assert report["duration_ms"] >= 0
    unsigned = dict(report)
    report_id = unsigned.pop("report_id")
    assert report_id == manager._sha256_bytes(manager._canonical_json(unsigned))
