# Safe Mode

Safe Mode is activated when Docker is unavailable or unusable.

Required message:

```text
Docker was not found or is not usable. PLwC is running in Safe Mode. File and profile-safe operations remain available, but sandboxed code execution is disabled. To enable sandboxed execution, install Docker Desktop, start Docker, and restart PLwC.
```

Setup hint:

```text
Quick setup: install Docker Desktop from the official Docker website, start Docker Desktop, verify it with 'docker --version', then restart PLwC.
```

## Safe Mode Rules

- Workspace file operations may remain available.
- Protected governance files remain protected.
- Sandboxed code execution is disabled.
- Host shell fallback is forbidden.

The public sandbox tool returns a structured Safe Mode denial when Docker is
disabled, missing or unusable. It must not run caller-provided code through a
host shell fallback.

## Docker Mode Rules

When Docker is available, sandbox execution still uses server-owned arguments
only. The model cannot provide Docker flags, image names, mounts, network mode,
privileged mode, user IDs, capabilities, environment variables or resource
limits.

The default Docker run profile uses:

- `--rm`
- `--network none`
- `--read-only`
- tmpfs `/tmp`
- `--cap-drop ALL`
- `--security-opt no-new-privileges`
- non-root user
- memory, CPU and PID limits
- exactly one validated workspace bind mount at `/work`

The sandbox denies Docker socket mounts, host root or home mounts, Source A/B
mounts, repository root mounts and multiple workspace mounts. Docker unavailable
or invalid Docker policy states remain fail-closed and never fall back to host
execution.
