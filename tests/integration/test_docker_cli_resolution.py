from __future__ import annotations

import subprocess
from pathlib import Path

from plwc_gateway.adapters import docker_cli
from plwc_gateway.adapters import document_worker
from plwc_gateway.adapters import sandbox
from plwc_gateway.adapters.document_worker import DocumentWorkerAdapter
from plwc_gateway.adapters.sandbox import DockerSandboxAdapter
from plwc_gateway.config import DockerConfig, load_gateway_config
from plwc_gateway.mcp.server import plwc_status


class _UnavailableDocumentWorker:
    def status(self) -> dict[str, object]:
        return {
            "ok": False,
            "operation": "status",
            "status": "docker_unavailable",
            "error_category": "docker_unavailable",
            "error": "Docker is unavailable for the optional document worker.",
        }


def test_resolves_official_windows_cli_when_process_path_is_stale(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = (
        tmp_path / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
    )
    docker_executable.parent.mkdir(parents=True)
    docker_executable.write_bytes(b"test")

    monkeypatch.delenv("PLWC_DOCKER_EXE", raising=False)
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.delenv("ProgramW6432", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(docker_cli.shutil, "which", lambda _name: None)
    monkeypatch.setattr(docker_cli.sys, "platform", "win32")

    assert docker_cli.resolve_docker_executable() == str(
        docker_executable.resolve()
    )


def test_explicit_docker_cli_wins_over_process_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configured = tmp_path / "docker.exe"
    configured.write_bytes(b"test")
    monkeypatch.setenv("PLWC_DOCKER_EXE", str(configured))
    monkeypatch.setattr(
        docker_cli.shutil,
        "which",
        lambda _name: str(tmp_path / "path-docker.exe"),
    )

    assert docker_cli.resolve_docker_executable() == str(configured.resolve())


def test_sandbox_uses_resolved_cli_for_every_docker_call(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())
    calls: list[list[str]] = []

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    adapter = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "logs" / "audit.jsonl",
        runner=runner,
    )

    status = adapter.status()

    assert status.sandbox_ready is True
    assert status.docker_executable == docker_executable
    assert calls
    assert all(call[0] == docker_executable for call in calls)
    assert adapter._docker_args("print('ok')", tmp_path)[0] == docker_executable
    assert adapter._docker_args_for_shell("true", tmp_path)[0] == docker_executable
    assert adapter._docker_args_for_node("/work/test.js", tmp_path)[0] == docker_executable


def test_cli_failure_does_not_claim_daemon_was_checked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="client failed",
        )

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    status = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "audit.jsonl",
        runner=runner,
    ).status()

    assert status.docker_cli_available is False
    assert status.docker_daemon_available is None


def test_cli_and_stopped_daemon_are_reported_separately(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())
    calls: list[list[str]] = []

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="Docker version test",
                stderr="",
            )
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="Docker daemon is not running",
        )

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    status = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "audit.jsonl",
        runner=runner,
    ).status()

    assert status.docker_cli_available is True
    assert status.docker_daemon_available is False
    assert status.sandbox_ready is False
    assert [call[1:] for call in calls] == [["--version"], ["info"]]
    assert all(call[0] == docker_executable for call in calls)


def test_daemon_probe_timeout_enters_safe_mode_instead_of_raising(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="Docker version test",
                stderr="",
            )
        raise subprocess.TimeoutExpired(args, timeout=5)

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    status = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "audit.jsonl",
        runner=runner,
    ).status()

    assert status.ok is False
    assert status.mode == "safe"
    assert status.docker_cli_available is True
    assert status.docker_daemon_available is False
    assert "timed out after 5 seconds" in (status.docker_daemon_error or "")


def test_first_run_continues_when_daemon_probe_times_out(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="Docker version test",
                stderr="",
            )
        raise subprocess.TimeoutExpired(args, timeout=5)

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    config = load_gateway_config(project_root=tmp_path)
    adapter = DockerSandboxAdapter(
        config.docker,
        workspace_roots=config.allowed_roots,
        audit_log_file=tmp_path / "logs" / "audit.jsonl",
        runner=runner,
    )

    result = plwc_status(
        "first_run",
        config=config,
        sandbox_adapter=adapter,
        document_worker_adapter=_UnavailableDocumentWorker(),
    )

    assert result["scope"] == "first_run"
    assert result["docker_status"] == "daemon_not_running"
    assert result["safe_mode"] is True
    assert result["onboarding_required"] is True
    assert "profile_creation" in result["next_action"]


def test_sandbox_image_probe_timeout_enters_safe_mode_instead_of_raising(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        if args[1:] in (["--version"], ["info"]):
            return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")
        raise subprocess.TimeoutExpired(args, timeout=5)

    monkeypatch.setattr(
        sandbox,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    status = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "audit.jsonl",
        runner=runner,
    ).status()

    assert status.ok is False
    assert status.mode == "safe"
    assert status.docker_cli_available is True
    assert status.docker_daemon_available is True
    assert status.sandbox_image_available is None
    assert "sandbox image probe failed" in (status.error or "")


def test_document_worker_uses_resolved_cli(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docker_executable = str((tmp_path / "docker.exe").resolve())
    calls: list[list[str]] = []

    def runner(args: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(
        document_worker,
        "resolve_docker_executable",
        lambda: docker_executable,
    )
    adapter = DocumentWorkerAdapter(workspace_roots=[tmp_path], runner=runner)

    assert adapter.status().ok is True
    assert calls[0][0] == docker_executable
    assert adapter._docker_args(["probe"])[0] == docker_executable
