from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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
    def _result(
        command_id: str,
        *,
        ok: bool = True,
        stdout: str = "",
        stderr: str | None = None,
        exit_code: int = 0,
        cancelled: bool = False,
        timed_out: bool = False,
    ) -> dict:
        return {
            "ok": ok,
            "stdout": stdout,
            "stderr": ("" if ok else "synthetic failure") if stderr is None else stderr,
            "exit_code": exit_code,
            "cancelled": cancelled,
            "timed_out": timed_out,
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


def _main_args(tmp_path: Path, *, operation: str = "inventory", consent: bool = False) -> tuple[list[str], Path, Path]:
    manifest_path = tmp_path / "runtime-images.json"
    manifest_path.write_text(json.dumps(valid_manifest()), encoding="utf-8")
    docker_path = tmp_path / "docker.exe"
    docker_path.write_bytes(b"fixture")
    report_path = tmp_path / "runtime-image-report.json"
    arguments = [
        operation,
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
    if consent:
        arguments.extend(("--consent-token", manager.CONSENT_TOKEN))
    return arguments, manifest_path, report_path


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


def test_friendly_tag_never_satisfies_or_changes_locked_reference() -> None:
    manifest = valid_manifest()
    friendly_tags = [image["display_tag"] for image in manifest["images"]]
    fake = FakeRunner(present=friendly_tags)
    result = _image_manager(fake).acquire()
    assert result["state"] == "ready"
    assert len([call for call in fake.calls if call[1] == "pull"]) == 3
    assert all(tag not in call for tag in friendly_tags for call in fake.calls)
    assert all("@sha256:" in call[-1] for call in fake.calls if call[1] == "pull")


def test_single_missing_image_pulls_only_that_digest_and_probes_all() -> None:
    manifest = valid_manifest()
    exact_refs = [image["reference"] for image in manifest["images"]]
    fake = FakeRunner(present=exact_refs[1:])
    result = _image_manager(fake).acquire()
    pulls = [call for call in fake.calls if call[1] == "pull"]
    assert len(pulls) == 1
    assert pulls[0][-1] == exact_refs[0]
    assert len([call for call in fake.calls if call[1] == "run"]) == 3
    assert [item["state"] for item in result["images"]] == ["probe_passed"] * 3


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


@pytest.mark.parametrize(("cancelled", "timed_out"), [(True, False), (False, True)])
def test_pull_cancel_or_timeout_stops_without_retry(cancelled: bool, timed_out: bool) -> None:
    class InterruptedPull(FakeRunner):
        def run(self, argv, **kwargs):
            args = list(argv)
            if args[1] == "pull":
                self.calls.append(args)
                return self._result(
                    kwargs["command_id"],
                    ok=False,
                    exit_code=130 if cancelled else 124,
                    cancelled=cancelled,
                    timed_out=timed_out,
                )
            return super().run(argv, **kwargs)

    fake = InterruptedPull()
    with pytest.raises(manager.CancelledOrTimedOutError) as captured:
        _image_manager(fake).acquire()
    assert captured.value.cancelled is cancelled
    assert captured.value.timed_out is timed_out
    assert len([call for call in fake.calls if call[1] == "pull"]) == 1
    assert not [call for call in fake.calls if call[1] == "run"]


@pytest.mark.parametrize(
    "payload_update",
    [
        {"RepoDigests": ["ghcr.io/mhoedt-ai/plwc-document-worker@sha256:" + "f" * 64]},
        {"Architecture": "arm64"},
    ],
)
def test_post_pull_digest_or_platform_mismatch_fails_before_probe(payload_update: dict) -> None:
    class MismatchedAfterPull(FakeRunner):
        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            if kwargs["command_id"] == "inspect-document_worker-after":
                payload = json.loads(result["stdout"])
                payload.update(payload_update)
                result["stdout"] = json.dumps(payload)
            return result

    fake = MismatchedAfterPull()
    with pytest.raises(manager.PullVerificationError, match="digest or platform"):
        _image_manager(fake).acquire()
    assert not [call for call in fake.calls if call[1] == "run"]
    assert len([call for call in fake.calls if call[1] == "pull"]) == 1


@pytest.mark.parametrize("failure_text", ["unauthorized: authentication required", "TLS handshake timeout"])
def test_first_pull_network_failure_never_logs_in_or_continues(failure_text: str) -> None:
    class NetworkFailure(FakeRunner):
        def run(self, argv, **kwargs):
            args = list(argv)
            if args[1] == "pull":
                self.calls.append(args)
                return self._result(kwargs["command_id"], ok=False, stderr=failure_text, exit_code=1)
            return super().run(argv, **kwargs)

    fake = NetworkFailure()
    with pytest.raises(manager.PullVerificationError):
        _image_manager(fake).acquire()
    assert len([call for call in fake.calls if call[1] == "pull"]) == 1
    assert not any("login" in call for call in fake.calls)


def test_probe_failure_never_becomes_ready() -> None:
    fake = FakeRunner(fail_probe_id="document_worker")
    with pytest.raises(manager.ProbeError) as captured:
        _image_manager(fake).acquire()
    assert captured.value.images[0]["state"] == "safe_mode"


def test_invalid_success_probe_output_fails_closed() -> None:
    class InvalidProbeOutput(FakeRunner):
        def run(self, argv, **kwargs):
            result = super().run(argv, **kwargs)
            if kwargs["command_id"] == "probe-document_worker":
                result["stdout"] = "not-json"
            return result

    with pytest.raises(manager.ProbeError):
        _image_manager(InvalidProbeOutput(present=[valid_manifest()["images"][0]["reference"]])).acquire()


def test_probe_timeout_is_categorized_and_stops_later_images() -> None:
    class TimedOutProbe(FakeRunner):
        def run(self, argv, **kwargs):
            args = list(argv)
            if kwargs["command_id"] == "probe-document_worker":
                self.calls.append(args)
                return self._result(kwargs["command_id"], ok=False, exit_code=124, timed_out=True)
            return super().run(argv, **kwargs)

    refs = [image["reference"] for image in valid_manifest()["images"]]
    fake = TimedOutProbe(present=refs)
    with pytest.raises(manager.CancelledOrTimedOutError) as captured:
        _image_manager(fake).acquire()
    assert captured.value.timed_out is True
    assert len([call for call in fake.calls if call[1] == "run"]) == 1


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


def test_process_runner_normalizes_invalid_utf8_and_control_bytes(tmp_path: Path) -> None:
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27")
    result = runner.run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'ok\\xff\\x01end'); sys.exit(1)"],
        phase="image_pull",
        command_id="synthetic-invalid-output",
        timeout_seconds=10,
        inactivity_timeout_seconds=5,
    )
    assert result["exit_code"] == 1
    assert "\ufffd" in result["stdout"]
    assert "\x01" not in result["stdout"]
    assert "?" in result["stdout"]


def test_process_runner_creation_failure_keeps_started_false_envelope(tmp_path: Path, monkeypatch) -> None:
    def fail_start(*_args, **_kwargs):
        raise OSError("synthetic process creation failure")

    monkeypatch.setattr(manager.subprocess, "Popen", fail_start)
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27")
    result = runner.run(
        ["missing-docker.exe", "info"],
        phase="image_inventory",
        command_id="synthetic-start-failure",
        timeout_seconds=10,
        inactivity_timeout_seconds=5,
    )
    assert result["started"] is False
    assert result["exception_type"] == "OSError"
    assert result["error_category"] == "process_start_or_capture_failed"
    assert result["ok"] is False
    persisted = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
    assert persisted == result


def test_process_runner_uses_allowlisted_environment_and_anonymous_docker_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    user_docker_config = tmp_path / "user-docker-config"
    user_docker_config.mkdir()
    credentials = user_docker_config / "config.json"
    credentials.write_text('{"auths":{"private":{"auth":"do-not-inherit"}}}', encoding="utf-8")
    monkeypatch.setenv("DOCKER_CONFIG", str(user_docker_config))
    monkeypatch.setenv("PLWC_SYNTHETIC_SECRET", "must-not-reach-child")
    original_popen = manager.subprocess.Popen
    observed_environment: dict[str, str] = {}

    def capture_environment(*args, **kwargs):
        observed_environment.update(kwargs["env"])
        return original_popen(*args, **kwargs)

    monkeypatch.setattr(manager.subprocess, "Popen", capture_environment)
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27")
    result = runner.run(
        [sys.executable, "-c", "print('ok')"],
        phase="image_inventory",
        command_id="synthetic-environment",
        timeout_seconds=10,
        inactivity_timeout_seconds=5,
    )
    assert result["ok"] is True
    assert observed_environment["DOCKER_CONFIG"] == str(runner.docker_config_directory)
    assert observed_environment["DOCKER_CONFIG"] != str(user_docker_config)
    assert observed_environment["DOCKER_CLI_HINTS"] == "false"
    assert "PLWC_SYNTHETIC_SECRET" not in observed_environment
    assert credentials.read_text(encoding="utf-8") == '{"auths":{"private":{"auth":"do-not-inherit"}}}'
    assert list(runner.docker_config_directory.iterdir()) == []


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


def test_process_runner_cancel_file_terminates_owned_child(tmp_path: Path) -> None:
    cancel_file = tmp_path / "cancel"
    cancel_file.write_text("cancel", encoding="utf-8")
    runner = manager.ProcessRunner(tmp_path / "reports", build_id="test-r27", cancel_file=cancel_file)
    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        phase="image_pull",
        command_id="synthetic-cancel",
        timeout_seconds=10,
        inactivity_timeout_seconds=5,
    )
    assert result["ok"] is False
    assert result["cancelled"] is True
    assert result["timed_out"] is False
    assert result["error_category"] == "cancelled"


def test_second_acquisition_is_idempotent_and_does_not_touch_docker_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docker_config = tmp_path / "docker-config"
    docker_config.mkdir()
    credentials = docker_config / "config.json"
    credentials.write_text('{"auths":{"private":{"auth":"do-not-read"}}}', encoding="utf-8")
    monkeypatch.setenv("DOCKER_CONFIG", str(docker_config))
    before = credentials.read_bytes()
    fake = FakeRunner()
    runtime_manager = _image_manager(fake)
    first = runtime_manager.acquire()
    pulls_after_first = len([call for call in fake.calls if call[1] == "pull"])
    second = runtime_manager.acquire()
    assert first["state"] == second["state"] == "ready"
    assert pulls_after_first == 3
    assert len([call for call in fake.calls if call[1] == "pull"]) == pulls_after_first
    assert credentials.read_bytes() == before
    assert os.environ["DOCKER_CONFIG"] == str(docker_config)


def test_each_attempt_gets_a_new_plan_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = valid_manifest()
    manifest_path = tmp_path / "runtime-images.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    docker_path = tmp_path / "docker.exe"
    docker_path.write_bytes(b"fixture")

    class SuccessfulManager:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        @staticmethod
        def inventory() -> dict[str, object]:
            return {"ok": True, "phase": "image_inventory", "state": "inventory_complete", "images": []}

    monkeypatch.setattr(manager, "RuntimeImageManager", SuccessfulManager)
    plan_ids = []
    for attempt in range(2):
        report_path = tmp_path / f"runtime-image-report-{attempt}.json"
        assert manager.main(
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
                str(tmp_path / f"process-reports-{attempt}"),
                "--build-id",
                "fixture-installer-r27",
            ]
        ) == 0
        plan_ids.append(json.loads(report_path.read_text(encoding="utf-8"))["plan_id"])
    assert plan_ids[0] != plan_ids[1]


@pytest.mark.parametrize("variant", ["tampered_manifest", "missing_docker", "missing_consent"])
def test_preconditions_fail_before_process_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
) -> None:
    operation = "acquire" if variant == "missing_consent" else "inventory"
    arguments, manifest_path, report_path = _main_args(tmp_path, operation=operation)
    if variant == "tampered_manifest":
        manifest_path.write_text("{}", encoding="utf-8")
    elif variant == "missing_docker":
        Path(arguments[arguments.index("--docker") + 1]).unlink()

    class ForbiddenRunner:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("no Docker process runner may be created")

    monkeypatch.setattr(manager, "ProcessRunner", ForbiddenRunner)
    expected_exit = 22 if variant == "missing_docker" else 21
    assert manager.main(arguments) == expected_exit
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["exit_code"] == expected_exit
    assert report["state"] == "safe_mode"
    assert report["started"] is True


def test_unexpected_manager_exception_has_outer_report_and_exit_40(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments, _manifest_path, report_path = _main_args(tmp_path, operation="acquire", consent=True)

    class ExplodingManager:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        @staticmethod
        def acquire() -> dict:
            raise RuntimeError("synthetic unexpected manager failure")

    monkeypatch.setattr(manager, "RuntimeImageManager", ExplodingManager)
    assert manager.main(arguments) == 40
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["exception_type"] == "RuntimeError"
    assert report["error_category"] == "unexpected_error"
    assert report["exit_code"] == 40
    assert report["ok"] is False


def test_keyboard_interrupt_uses_secondary_report_when_primary_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arguments, _manifest_path, report_path = _main_args(tmp_path, operation="acquire", consent=True)

    class InterruptedManager:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        @staticmethod
        def acquire() -> dict:
            raise KeyboardInterrupt()

    real_atomic_write = manager._atomic_write_json

    def fail_primary(path: Path, value: dict) -> None:
        if Path(path) == report_path:
            raise OSError("synthetic primary write failure")
        real_atomic_write(Path(path), value)

    monkeypatch.setattr(manager, "RuntimeImageManager", InterruptedManager)
    monkeypatch.setattr(manager, "_atomic_write_json", fail_primary)
    assert manager.main(arguments) == 25
    fallback = report_path.with_name("r27-runtime-image-fallback.json")
    assert not report_path.exists()
    report = json.loads(fallback.read_text(encoding="utf-8"))
    assert report["cancelled"] is True
    assert report["timed_out"] is False
    assert Path(report["report_path"]) == fallback.resolve()
    unsigned = dict(report)
    report_id = unsigned.pop("report_id")
    assert report_id == manager._sha256_bytes(manager._canonical_json(unsigned))


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
