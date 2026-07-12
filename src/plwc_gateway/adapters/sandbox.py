"""Server-owned Docker sandbox adapter."""

from __future__ import annotations

import subprocess
import fnmatch
import os
import re
import shutil
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plwc_gateway.config import DockerConfig
from plwc_gateway.policy import IntentAction, PolicyDecision, PolicyIntent, execute_with_policy
from plwc_gateway.policy.paths import PROTECTED_GOVERNANCE_FILENAMES

SAFE_MODE_MESSAGE = (
    "Docker was not found or is not usable. PLwC is running in Safe Mode. "
    "File and profile-safe operations remain available, but sandboxed code "
    "execution is disabled. To enable sandboxed execution, install Docker "
    "Desktop, start Docker, and restart PLwC."
)
CONTAINER_WORKDIR = "/work"
CONTAINER_USER = "65532:65532"
TMPFS_SPEC = "/tmp:rw,noexec,nosuid,nodev,size=64m"
MEMORY_LIMIT_RE = re.compile(r"^[1-9][0-9]*[kmgKMG]?$")
CPU_LIMIT_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
DOCKER_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$")


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    mode: str
    policy_decision: PolicyDecision
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    error: str | None = None
    docker_args: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = ()
    python_available: bool | None = None
    docker_cli_available: bool | None = None
    docker_daemon_available: bool | None = None
    sandbox_image: str | None = None
    sandbox_image_available: bool | None = None
    docker_pull_disabled: bool = True
    next_action: str | None = None
    python_executable: str | None = None
    python_version: str | None = None
    docker_executable: str | None = None
    docker_version: str | None = None
    docker_daemon_error: str | None = None
    workspace_mount_allowed: bool | None = None
    workspace_mount_reason: str | None = None
    audit_log_writable: bool | None = None
    audit_log_reason: str | None = None
    sandbox_ready: bool = False
    node_image: str | None = None
    node_image_available: bool | None = None


class DockerSandboxAdapter:
    def __init__(
        self,
        docker: DockerConfig,
        *,
        workspace_roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None = None,
        project_root: str | os.PathLike[str] | None = None,
        audit_log_file: str | os.PathLike[str] | None = None,
        protected_path_patterns: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        policy_engine: Any | None = None,
    ) -> None:
        self.docker = docker
        self.workspace_roots = _coerce_roots(workspace_roots)
        self.project_root = Path(project_root).resolve(strict=False) if project_root is not None else None
        self.audit_log_file = Path(audit_log_file).resolve(strict=False) if audit_log_file is not None else None
        self.protected_path_patterns = _coerce_roots(protected_path_patterns)
        self.runner = runner
        self.policy_engine = policy_engine

    def status(self) -> SandboxResult:
        python_available = bool(sys.executable)
        python_executable = sys.executable or None
        python_version = ".".join(str(part) for part in sys.version_info[:3])
        docker_executable = shutil.which("docker")
        mount_root = self._workspace_mount_root()
        mount_allowed = not isinstance(mount_root, SandboxResult)
        mount_reason = "Workspace mount is allowed." if mount_allowed else mount_root.error
        audit_ok, audit_reason = self._audit_log_status()
        if not self.docker.enabled:
            return self._safe_mode(
                "Docker execution is disabled by local policy.",
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=None,
                docker_daemon_available=None,
                docker_executable=docker_executable,
                sandbox_image_available=None,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Enable Docker Mode in local policy only after Docker Desktop is installed and reviewed.",
            )
        config_error = self._docker_policy_error()
        if config_error:
            return self._policy_error(
                config_error,
                ("SR-003", "NFR-002"),
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=None,
                docker_daemon_available=None,
                docker_executable=docker_executable,
                sandbox_image_available=None,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Fix the local PLwC Docker policy configuration.",
            )
        try:
            version = self.runner(["docker", "--version"], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError) as exc:
            return self._safe_mode(
                str(exc),
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=False,
                docker_daemon_available=False,
                docker_executable=docker_executable,
                sandbox_image_available=None,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Install Docker Desktop, start Docker, and restart PLwC. PLwC will not install Docker automatically.",
            )
        if version.returncode != 0:
            return self._safe_mode(
                version.stderr or version.stdout,
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=False,
                docker_daemon_available=False,
                docker_executable=docker_executable,
                docker_version=version.stdout.strip() or None,
                sandbox_image_available=None,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Install Docker Desktop, start Docker, and restart PLwC. PLwC will not install Docker automatically.",
            )
        info = self.runner(["docker", "info"], capture_output=True, text=True, timeout=5)
        if info.returncode != 0:
            return self._safe_mode(
                info.stderr or info.stdout,
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=True,
                docker_daemon_available=False,
                docker_executable=docker_executable or "docker",
                docker_version=version.stdout.strip() or None,
                docker_daemon_error=(info.stderr or info.stdout).strip() or None,
                sandbox_image_available=None,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Start Docker Desktop and verify that the Docker daemon is reachable.",
            )
        image = self.runner(["docker", "image", "inspect", self.docker.image], capture_output=True, text=True, timeout=5)
        if image.returncode != 0:
            return self._policy_error(
                _missing_local_image_error(image.stderr or image.stdout)
                or "Docker sandbox image is not available locally.",
                ("SR-003", "NFR-002"),
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=True,
                docker_daemon_available=True,
                docker_executable=docker_executable or "docker",
                docker_version=version.stdout.strip() or None,
                sandbox_image_available=False,
                workspace_mount_allowed=mount_allowed,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action=(
                    f"Prepare the sandbox image manually with 'docker pull {self.docker.image}'. "
                    "PLwC will not pull images automatically because runtime pulls are disabled."
                ),
            )
        node_inspect = self.runner(
            ["docker", "image", "inspect", self.docker.node_image],
            capture_output=True, text=True, timeout=5,
        )
        node_image_ok = node_inspect.returncode == 0
        if not mount_allowed and isinstance(mount_root, SandboxResult):
            return self._policy_error(
                mount_root.error or "Sandbox workspace mount is not allowed.",
                mount_root.requirement_ids or ("SR-006", "NFR-002"),
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=True,
                docker_daemon_available=True,
                docker_executable=docker_executable or "docker",
                docker_version=version.stdout.strip() or None,
                sandbox_image_available=True,
                workspace_mount_allowed=False,
                workspace_mount_reason=mount_reason,
                audit_log_writable=audit_ok,
                audit_log_reason=audit_reason,
                next_action="Choose a safe configured PLwC workspace root before retrying sandbox execution.",
            )
        if audit_ok is False:
            return self._policy_error(
                audit_reason or "Audit log is not writable.",
                ("FR-008", "NFR-002"),
                python_available=python_available,
                python_executable=python_executable,
                python_version=python_version,
                docker_cli_available=True,
                docker_daemon_available=True,
                docker_executable=docker_executable or "docker",
                docker_version=version.stdout.strip() or None,
                sandbox_image_available=True,
                workspace_mount_allowed=True,
                workspace_mount_reason=mount_reason,
                audit_log_writable=False,
                audit_log_reason=audit_reason,
                next_action="Fix the PLwC audit log path or permissions before retrying sandbox execution.",
            )
        return SandboxResult(
            ok=True,
            mode="docker",
            policy_decision=PolicyDecision.ALLOW,
            stdout=version.stdout,
            exit_code=version.returncode,
            requirement_ids=("FR-007",),
            python_available=python_available,
            python_executable=python_executable,
            python_version=python_version,
            docker_cli_available=True,
            docker_daemon_available=True,
            docker_executable=docker_executable or "docker",
            docker_version=version.stdout.strip() or None,
            sandbox_image=self.docker.image,
            sandbox_image_available=True,
            docker_pull_disabled=True,
            workspace_mount_allowed=True,
            workspace_mount_reason=mount_reason,
            audit_log_writable=audit_ok,
            audit_log_reason=audit_reason,
            sandbox_ready=True,
            node_image=self.docker.node_image,
            node_image_available=node_image_ok,
            next_action="Docker Mode is available. Sandbox execution remains policy-controlled with no host-shell fallback.",
        )

    def run_python(self, code: str) -> SandboxResult:
        if not code.strip():
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=PolicyDecision.DENY,
                error="Sandbox code is required.",
                requirement_ids=("NFR-002",),
            )

        intent = PolicyIntent(tool_name="plwc_run_python_sandboxed", action=IntentAction.EXECUTE_SANDBOXED)

        def adapter_call() -> SandboxResult:
            status = self.status()
            if not status.ok:
                if _is_sandbox_policy_denial(status):
                    return status
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=SAFE_MODE_MESSAGE,
                    requirement_ids=("SR-002", "FR-007"),
                )
            workspace_root = self._workspace_mount_root()
            if isinstance(workspace_root, SandboxResult):
                return workspace_root
            args = self._docker_args(code, workspace_root)
            try:
                completed = self.runner(
                    list(args),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.docker.timeout_seconds + 5,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=f"{SAFE_MODE_MESSAGE} Detail: {exc}",
                    docker_args=args,
                    requirement_ids=("SR-002", "NFR-002"),
                )
            missing_image = (
                _missing_local_image_error(completed.stderr or completed.stdout)
                if completed.returncode != 0
                else None
            )
            if missing_image:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                    error=missing_image,
                    docker_args=args,
                    requirement_ids=("SR-003", "NFR-002"),
                )
            return SandboxResult(
                ok=completed.returncode == 0,
                mode="docker",
                policy_decision=PolicyDecision.ALLOW,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                docker_args=args,
                requirement_ids=("FR-007", "SR-003", "SR-010"),
            )

        execution = execute_with_policy(intent, adapter_call, self.policy_engine)
        if not execution.executed:
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=execution.policy.decision,
                error=execution.policy.reason,
                requirement_ids=execution.policy.requirement_ids,
            )
        return execution.adapter_result

    def run_shell(self, command: str) -> SandboxResult:
        if not command.strip():
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=PolicyDecision.DENY,
                error="Sandbox command is required.",
                requirement_ids=("NFR-002",),
            )

        intent = PolicyIntent(tool_name="plwc_run_shell_sandboxed", action=IntentAction.EXECUTE_SANDBOXED)

        def adapter_call() -> SandboxResult:
            status = self.status()
            if not status.ok:
                if _is_sandbox_policy_denial(status):
                    return status
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=SAFE_MODE_MESSAGE,
                    requirement_ids=("SR-002", "FR-007"),
                )
            workspace_root = self._workspace_mount_root()
            if isinstance(workspace_root, SandboxResult):
                return workspace_root
            args = self._docker_args_for_shell(command, workspace_root)
            try:
                completed = self.runner(
                    list(args),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.docker.timeout_seconds + 5,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=f"{SAFE_MODE_MESSAGE} Detail: {exc}",
                    docker_args=args,
                    requirement_ids=("SR-002", "NFR-002"),
                )
            missing_image = (
                _missing_local_image_error(completed.stderr or completed.stdout)
                if completed.returncode != 0
                else None
            )
            if missing_image:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                    error=missing_image,
                    docker_args=args,
                    requirement_ids=("SR-003", "NFR-002"),
                )
            return SandboxResult(
                ok=completed.returncode == 0,
                mode="docker",
                policy_decision=PolicyDecision.ALLOW,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                docker_args=args,
                requirement_ids=("FR-007", "SR-003", "SR-010"),
            )

        execution = execute_with_policy(intent, adapter_call, self.policy_engine)
        if not execution.executed:
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=execution.policy.decision,
                error=execution.policy.reason,
                requirement_ids=execution.policy.requirement_ids,
            )
        return execution.adapter_result

    def run_node(self, script_path: str) -> SandboxResult:
        if not script_path.strip():
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=PolicyDecision.DENY,
                error="Node sandbox script path is required.",
                requirement_ids=("NFR-002",),
            )

        intent = PolicyIntent(tool_name="plwc_sandbox_run", action=IntentAction.EXECUTE_SANDBOXED)

        def adapter_call() -> SandboxResult:
            status = self.status()
            if not status.ok:
                if _is_sandbox_policy_denial(status):
                    return status
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=SAFE_MODE_MESSAGE,
                    requirement_ids=("SR-002", "FR-007"),
                )
            node_inspect = self.runner(
                ["docker", "image", "inspect", self.docker.node_image],
                capture_output=True, text=True, timeout=5,
            )
            if node_inspect.returncode != 0:
                error = (
                    _missing_local_image_error(node_inspect.stderr or node_inspect.stdout)
                    or "Node sandbox image is not available locally."
                )
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=error,
                    requirement_ids=("SR-003", "NFR-002"),
                    node_image=self.docker.node_image,
                    node_image_available=False,
                    next_action=(
                        f"Build the Node runner image with "
                        f"'docker build -t {self.docker.node_image} docker/node-runner/'. "
                        "PLwC will not pull images automatically."
                    ),
                )
            workspace_root = self._workspace_mount_root()
            if isinstance(workspace_root, SandboxResult):
                return workspace_root
            args = self._docker_args_for_node(script_path, workspace_root)
            try:
                completed = self.runner(
                    list(args),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.docker.timeout_seconds + 5,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    error=f"{SAFE_MODE_MESSAGE} Detail: {exc}",
                    docker_args=args,
                    requirement_ids=("SR-002", "NFR-002"),
                )
            missing_image = (
                _missing_local_image_error(completed.stderr or completed.stdout)
                if completed.returncode != 0
                else None
            )
            if missing_image:
                return SandboxResult(
                    ok=False,
                    mode="safe",
                    policy_decision=PolicyDecision.DENY,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                    error=missing_image,
                    docker_args=args,
                    requirement_ids=("SR-003", "NFR-002"),
                )
            return SandboxResult(
                ok=completed.returncode == 0,
                mode="docker",
                policy_decision=PolicyDecision.ALLOW,
                stdout=completed.stdout,
                stderr=completed.stderr,
                exit_code=completed.returncode,
                docker_args=args,
                node_image=self.docker.node_image,
                node_image_available=True,
                requirement_ids=("FR-007", "SR-003", "SR-010"),
            )

        execution = execute_with_policy(intent, adapter_call, self.policy_engine)
        if not execution.executed:
            return SandboxResult(
                ok=False,
                mode="safe",
                policy_decision=execution.policy.decision,
                error=execution.policy.reason,
                requirement_ids=execution.policy.requirement_ids,
            )
        return execution.adapter_result

    def _docker_args(self, code: str, workspace_root: Path) -> tuple[str, ...]:
        return (*self._docker_base_args(workspace_root), self.docker.image, "python", "-c", code)

    def _docker_args_for_shell(self, command: str, workspace_root: Path) -> tuple[str, ...]:
        return (*self._docker_base_args(workspace_root), self.docker.image, "sh", "-lc", command)

    def _docker_args_for_node(self, script_path: str, workspace_root: Path) -> tuple[str, ...]:
        base = list(self._docker_base_args(workspace_root))
        # Node uses a dedicated memory limit; V8 idle footprint exceeds CPython.
        mem_idx = base.index("--memory") + 1
        base[mem_idx] = self.docker.node_memory
        return (*base, self.docker.node_image, "node", script_path)

    def _docker_base_args(self, workspace_root: Path) -> tuple[str, ...]:
        return (
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            TMPFS_SPEC,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            CONTAINER_USER,
            "--memory",
            self.docker.memory,
            "--cpus",
            self.docker.cpus,
            "--pids-limit",
            str(self.docker.pids_limit),
            "--workdir",
            CONTAINER_WORKDIR,
            "--mount",
            f"type=bind,source={workspace_root},target={CONTAINER_WORKDIR},readonly=false",
        )

    def _docker_policy_error(self) -> str | None:
        if self.docker.network != "none":
            return "Docker network mode must be none."
        if not self.docker.read_only_root:
            return "Docker root filesystem must remain read-only."
        if self.docker.allow_privileged:
            return "Docker privileged mode is forbidden."
        if self.docker.allow_docker_socket_mount:
            return "Docker socket mounts are forbidden."
        if self.docker.allow_host_network:
            return "Docker host networking is forbidden."
        if self.docker.allow_dynamic_image:
            return "Dynamic Docker image selection is forbidden."
        if self.docker.allow_dynamic_mounts:
            return "Dynamic Docker mounts are forbidden."
        if not DOCKER_IMAGE_RE.fullmatch(self.docker.image) or self.docker.image.startswith("-"):
            return "Docker image must be a static server-owned image reference."
        if not MEMORY_LIMIT_RE.fullmatch(self.docker.memory):
            return "Docker memory limit must be a static server-owned value."
        if not CPU_LIMIT_RE.fullmatch(self.docker.cpus) or float(self.docker.cpus) <= 0:
            return "Docker CPU limit must be a positive server-owned value."
        if self.docker.pids_limit <= 0:
            return "Docker PID limit must be positive."
        if self.docker.timeout_seconds <= 0:
            return "Docker timeout must be positive."
        if not DOCKER_IMAGE_RE.fullmatch(self.docker.node_image) or self.docker.node_image.startswith("-"):
            return "Docker node_image must be a static server-owned image reference."
        if not MEMORY_LIMIT_RE.fullmatch(self.docker.node_memory):
            return "Docker node_memory limit must be a static server-owned value."
        return None

    def _workspace_mount_root(self) -> Path | SandboxResult:
        if len(self.workspace_roots) != 1:
            return self._policy_error("Exactly one sandbox workspace root is required.", ("SR-006", "NFR-002"))

        root = _resolve_root(self.workspace_roots[0])
        if _is_filesystem_root(root):
            return self._policy_error("Sandbox workspace mount must not be a filesystem root.", ("SR-006", "NFR-002"))
        if _same_path(root, Path.home().resolve(strict=False)):
            return self._policy_error("Sandbox workspace mount must not be the user home directory.", ("SR-006", "NFR-002"))
        if self.project_root is not None:
            source_overlap = _source_overlap(root, self.project_root)
            if source_overlap:
                return self._policy_error(f"Sandbox workspace mount must not overlap {source_overlap}.", ("SR-006", "NFR-002"))
            if _same_path(root, self.project_root):
                return self._policy_error("Sandbox workspace mount must not be the repository root.", ("SR-006", "NFR-002"))
        if not root.exists() or not root.is_dir():
            return self._policy_error("Sandbox workspace mount must be an existing directory.", ("SR-006", "NFR-002"))
        if _contains_docker_socket(root):
            return self._policy_error("Docker socket mounts are forbidden.", ("SR-003", "SR-006"))
        if _contains_protected_target(root, self.protected_path_patterns, self.project_root):
            return self._policy_error("Sandbox workspace mount contains protected governance targets.", ("SR-004", "SR-006"))
        return root

    def _audit_log_status(self) -> tuple[bool | None, str | None]:
        if self.audit_log_file is None:
            return None, "Audit log path was not provided to the sandbox adapter."
        if self.audit_log_file.exists() and self.audit_log_file.is_dir():
            return False, "Audit log path points to a directory."
        try:
            self.audit_log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_log_file.open("a", encoding="utf-8"):
                pass
        except OSError as exc:
            return False, f"Audit log is not writable: {exc}"
        return True, "Audit log is writable."

    def _policy_error(
        self,
        reason: str,
        requirement_ids: tuple[str, ...],
        *,
        python_available: bool | None = None,
        docker_cli_available: bool | None = None,
        docker_daemon_available: bool | None = None,
        sandbox_image_available: bool | None = None,
        python_executable: str | None = None,
        python_version: str | None = None,
        docker_executable: str | None = None,
        docker_version: str | None = None,
        docker_daemon_error: str | None = None,
        workspace_mount_allowed: bool | None = None,
        workspace_mount_reason: str | None = None,
        audit_log_writable: bool | None = None,
        audit_log_reason: str | None = None,
        next_action: str | None = None,
    ) -> SandboxResult:
        return SandboxResult(
            ok=False,
            mode="safe",
            policy_decision=PolicyDecision.DENY,
            error=reason,
            requirement_ids=requirement_ids,
            python_available=python_available,
            docker_cli_available=docker_cli_available,
            docker_daemon_available=docker_daemon_available,
            sandbox_image=self.docker.image,
            sandbox_image_available=sandbox_image_available,
            docker_pull_disabled=True,
            python_executable=python_executable,
            python_version=python_version,
            docker_executable=docker_executable,
            docker_version=docker_version,
            docker_daemon_error=docker_daemon_error,
            workspace_mount_allowed=workspace_mount_allowed,
            workspace_mount_reason=workspace_mount_reason,
            audit_log_writable=audit_log_writable,
            audit_log_reason=audit_log_reason,
            next_action=next_action or "Fix the local PLwC sandbox policy before retrying.",
        )

    def _safe_mode(
        self,
        detail: str,
        *,
        python_available: bool | None = None,
        docker_cli_available: bool | None = None,
        docker_daemon_available: bool | None = None,
        sandbox_image_available: bool | None = None,
        python_executable: str | None = None,
        python_version: str | None = None,
        docker_executable: str | None = None,
        docker_version: str | None = None,
        docker_daemon_error: str | None = None,
        workspace_mount_allowed: bool | None = None,
        workspace_mount_reason: str | None = None,
        audit_log_writable: bool | None = None,
        audit_log_reason: str | None = None,
        next_action: str | None = None,
    ) -> SandboxResult:
        return SandboxResult(
            ok=False,
            mode="safe",
            policy_decision=PolicyDecision.DENY,
            error=f"{SAFE_MODE_MESSAGE} Detail: {detail}",
            requirement_ids=("SR-002", "OR-002"),
            python_available=python_available,
            docker_cli_available=docker_cli_available,
            docker_daemon_available=docker_daemon_available,
            sandbox_image=self.docker.image,
            sandbox_image_available=sandbox_image_available,
            docker_pull_disabled=True,
            python_executable=python_executable,
            python_version=python_version,
            docker_executable=docker_executable,
            docker_version=docker_version,
            docker_daemon_error=docker_daemon_error,
            workspace_mount_allowed=workspace_mount_allowed,
            workspace_mount_reason=workspace_mount_reason,
            audit_log_writable=audit_log_writable,
            audit_log_reason=audit_log_reason,
            next_action=next_action or "Install and start Docker Desktop to enable Docker Mode. PLwC will not install Docker or pull images automatically.",
        )


def _coerce_roots(
    roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
) -> tuple[str | os.PathLike[str], ...]:
    if roots is None:
        return ()
    if isinstance(roots, (str, os.PathLike)):
        return (roots,)
    return tuple(roots)


def _is_sandbox_policy_denial(result: SandboxResult) -> bool:
    return any(requirement_id in result.requirement_ids for requirement_id in ("SR-003", "SR-006", "NFR-002"))


def _missing_local_image_error(output: str) -> str | None:
    text = output.casefold()
    if "no such image" not in text and "pull access denied" not in text and "image not found" not in text:
        return None
    return "Docker sandbox image is not available locally; implicit image pulls are disabled."


def _resolve_root(root: str | os.PathLike[str]) -> Path:
    return Path(root).expanduser().resolve(strict=False)


def _source_overlap(candidate: Path, project_root: Path) -> str | None:
    parts = {part.casefold() for part in candidate.parts}
    if "pba2" in parts:
        return "Source A ../PBA2"
    if "mcp_hardened_commander" in parts:
        return "Source B ../MCP_Hardened_Commander"
    source_roots = (
        ("Source A ../PBA2", (project_root.parent / "PBA2").resolve(strict=False)),
        ("Source B ../MCP_Hardened_Commander", (project_root.parent / "MCP_Hardened_Commander").resolve(strict=False)),
    )
    for label, source_root in source_roots:
        if _is_inside_or_same(candidate, source_root) or _is_inside_or_same(source_root, candidate):
            return label
    return None


def _contains_protected_target(
    root: Path,
    protected_patterns: tuple[str | os.PathLike[str], ...],
    project_root: Path | None,
) -> bool:
    if not root.exists():
        return False
    try:
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve(strict=False)
            if resolved.name.casefold() in _protected_filenames_casefold():
                return True
            if _matches_protected_pattern(resolved, protected_patterns, project_root):
                return True
    except OSError:
        return True
    return False


def _matches_protected_pattern(
    candidate: Path,
    protected_patterns: tuple[str | os.PathLike[str], ...],
    project_root: Path | None,
) -> bool:
    if project_root is None:
        return False
    candidate_text = _normalize(candidate)
    for raw_pattern in protected_patterns:
        pattern_path = Path(raw_pattern).expanduser()
        if not pattern_path.is_absolute():
            pattern_path = project_root / pattern_path
        if fnmatch.fnmatch(candidate_text, _normalize(pattern_path)):
            return True
    return False


def _contains_docker_socket(root: Path) -> bool:
    if root.name.casefold() == "docker.sock":
        return True
    try:
        for candidate in root.rglob("docker.sock"):
            if candidate.exists():
                return True
    except OSError:
        return True
    return False


def _is_inside_or_same(candidate: Path, root: Path) -> bool:
    try:
        common_path = os.path.commonpath([_normalize(candidate), _normalize(root)])
    except ValueError:
        return False
    return common_path == _normalize(root)


def _is_filesystem_root(path_value: Path) -> bool:
    anchor = Path(path_value.anchor) if path_value.anchor else None
    return anchor is not None and _same_path(path_value, anchor)


def _same_path(left: Path, right: Path) -> bool:
    return _normalize(left) == _normalize(right)


def _protected_filenames_casefold() -> frozenset[str]:
    return frozenset(name.casefold() for name in PROTECTED_GOVERNANCE_FILENAMES)


def _normalize(path_value: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path_value)))
