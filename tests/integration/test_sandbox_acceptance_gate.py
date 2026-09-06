from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from plwc_gateway.adapters.sandbox import CONTAINER_WORKDIR, TMPFS_SPEC, DockerSandboxAdapter
from plwc_gateway.config import DockerConfig, load_gateway_config
from plwc_gateway.mcp.server import plwc_describe, plwc_sandbox_run, plwc_status


class _UnavailableSandbox:
    def status(self) -> dict[str, Any]:
        return {
            "ok": False,
            "mode": "safe",
            "policy_decision": "DENY",
            "error": "Docker was not found or is not usable. PLwC is running in Safe Mode.",
            "error_category": "sandbox_unavailable",
            "requirement_ids": ["SR-002", "OR-002"],
            "sandbox_ready": False,
        }


def test_sandbox_status_exposes_acceptance_gate_without_docker(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_status("sandbox", config=config, sandbox_adapter=_UnavailableSandbox())

    assert payload["ok"] is False
    assert payload["error_category"] == "UNAVAILABLE"
    assert payload["error_detail_category"] == "sandbox_unavailable"
    gate = payload["sandbox_acceptance_gate"]
    assert gate["requirements"] == ["SBX-001", "SBX-002", "SBX-003", "SBX-004", "SBX-005"]
    assert gate["positive_acceptance_environment"]["requires_docker_capable_windows"] is True
    assert gate["positive_acceptance_environment"]["current_non_docker_vm_is_negative_evidence_only"] is True
    assert gate["execution_boundary"]["host_shell_fallback"] is False
    assert gate["execution_boundary"]["dynamic_canary_mounts_allowed"] is False
    assert gate["execution_boundary"]["docker_socket_mount_allowed"] is False


def test_sandbox_docker_args_lock_mounts_network_tmpfs_and_socket_policy(tmp_path: Path) -> None:
    adapter = DockerSandboxAdapter(
        DockerConfig(),
        workspace_roots=[tmp_path],
        audit_log_file=tmp_path / "logs" / "audit.jsonl",
    )

    args = adapter._docker_base_args(tmp_path)

    assert "--network" in args
    assert args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert "--tmpfs" in args
    assert args[args.index("--tmpfs") + 1] == TMPFS_SPEC
    assert "--privileged" not in args
    assert "/var/run/docker.sock" not in " ".join(args)
    mounts = [args[index + 1] for index, value in enumerate(args) if value == "--mount"]
    assert mounts == [f"type=bind,source={tmp_path},target={CONTAINER_WORKDIR},readonly=false"]


def test_describe_sandbox_exposes_acceptance_gate(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_describe(scope="sandbox", config=config)

    gate = payload["data"]["sandbox_acceptance_gate"]
    assert gate["execution_boundary"]["container_workdir"] == CONTAINER_WORKDIR
    assert gate["execution_boundary"]["tmpfs"] == TMPFS_SPEC
    assert gate["acceptance_expectations"]["SBX-005"].startswith("Docker socket")


def _docker_acceptance_config(tmp_path: Path):
    if os.environ.get("PLWC_RUN_DOCKER_ACCEPTANCE") != "1":
        pytest.skip("Set PLWC_RUN_DOCKER_ACCEPTANCE=1 on a Docker-capable Windows host to run SBX acceptance tests.")
    if os.name != "nt":
        pytest.skip("SBX acceptance is defined for a Docker-capable Windows host.")
    return load_gateway_config(project_root=tmp_path)


@pytest.mark.docker_acceptance
def test_sbx_001_docker_capable_system_reports_sandbox_ready(tmp_path: Path) -> None:
    config = _docker_acceptance_config(tmp_path)

    payload = plwc_status("sandbox", config=config)

    assert payload["ok"] is True
    assert payload["sandbox_ready"] is True
    assert payload["mode"] == "docker"


@pytest.mark.docker_acceptance
def test_sbx_002_file_written_from_work_appears_in_workspace(tmp_path: Path) -> None:
    config = _docker_acceptance_config(tmp_path)

    payload = plwc_sandbox_run(
        "python",
        "from pathlib import Path\n"
        "target = Path('/work/Temp/sbx-002/from-container.txt')\n"
        "target.parent.mkdir(parents=True, exist_ok=True)\n"
        "target.write_text('from /work', encoding='utf-8')\n",
        config=config,
    )

    assert payload["ok"] is True
    assert (config.allowed_roots[0] / "Temp" / "sbx-002" / "from-container.txt").read_text(encoding="utf-8") == "from /work"


@pytest.mark.docker_acceptance
def test_sbx_003_protected_root_write_fails_but_tmp_is_writable(tmp_path: Path) -> None:
    config = _docker_acceptance_config(tmp_path)

    payload = plwc_sandbox_run(
        "shell",
        "printf ok > /tmp/plwc-sbx-003 && (touch /etc/plwc-sbx-denied 2>/dev/null && exit 44 || exit 0)",
        config=config,
    )

    assert payload["ok"] is True


@pytest.mark.docker_acceptance
def test_sbx_004_only_work_is_the_writable_workspace_mount(tmp_path: Path) -> None:
    config = _docker_acceptance_config(tmp_path)

    payload = plwc_sandbox_run(
        "shell",
        "mkdir -p /plwc-outside-mount 2>/dev/null && touch /plwc-outside-mount/file 2>/dev/null && exit 44 || exit 0",
        config=config,
    )

    assert payload["ok"] is True
    mounts = [payload["docker_args"][index + 1] for index, value in enumerate(payload["docker_args"]) if value == "--mount"]
    assert mounts == [f"type=bind,source={config.allowed_roots[0]},target={CONTAINER_WORKDIR},readonly=false"]
    assert all("canary" not in mount.casefold() for mount in mounts)


@pytest.mark.docker_acceptance
def test_sbx_005_docker_engine_interfaces_are_unavailable_in_container(tmp_path: Path) -> None:
    config = _docker_acceptance_config(tmp_path)

    payload = plwc_sandbox_run(
        "shell",
        'test ! -S /var/run/docker.sock && test ! -e /run/docker.sock && test -z "${DOCKER_HOST:-}"',
        config=config,
    )

    assert payload["ok"] is True
