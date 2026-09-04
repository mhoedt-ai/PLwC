# PLwC Core H1 Acceptance Evidence

Date: 2026-07-30

Scope: PLwC core only. Chat Bridge and Windows Setup remain outside this H1
acceptance pass.

## Outcome

PLwC core local H1 acceptance is ready for the implemented Phase-A contract on
this Docker-capable Windows host: workspace structure, artifact provenance,
Describe/Next-Step, public error classes, effective governance policy, sandbox
acceptance gating, Docker-backed SBX/DOC acceptance, and document artifact
validation/provenance all have executable tests.

Docker Desktop is installed and reachable on this host. The Docker-backed SBX
and DOC acceptance suites were executed with `PLWC_RUN_DOCKER_ACCEPTANCE=1` and
passed.

## Acceptance Matrix

| Briefing item | Status | Evidence |
| --- | --- | --- |
| PLWC-P0-01 Workspace contract | PASS | `tests/integration/test_workspace_contract.py` verifies idempotent creation of `Tagebuch/`, `Temp/`, and `Trashcan/`, no `Inbox/`, conflict fail-closed behavior, and runtime status reporting. |
| PLWC-P0-02 Artifact provenance | PASS | Workspace binary writes report `artifact_origin=workspace_binary_write` and `validation_status=unvalidated`; existing binaries report `artifact_origin=unknown` and `validation_status=unvalidated`; document-worker PDFs report `artifact_origin=document_worker` and `validation_status=validated` only after technical PDF validation. |
| PLWC-P1-01 Describe / Next-Step | PASS | `plwc_describe(scope="document_operation", operation="create_pdf")` returns a create-PDF-only contract; unknown scopes and operations return `next_tool`, `next_operation`, `next_plan_type`, `required_fields`, and `example_call`. |
| PLWC-P1-02 Error classes | PASS | Public `error_category` uses `INVALID_REQUEST`, `NOT_FOUND`, `UNAVAILABLE`, `CONFLICT`, and `POLICY_DENY`; fine-grained compatibility detail remains in `error_detail_category`; `policy_decision` remains separate. |
| PLWC-P1-03 Effective governance | PASS | `effective_governance_policy` is shared by status, Governor plan, and Governor apply; user preference and effective policy fields are separate; `effective_policy_overridden_by_global_minimum` is false unless a real override occurs. |
| PLWC-P0-03 SBX-001..SBX-005 | PASS | `tests/integration/test_sandbox_acceptance_gate.py` exposes the machine-readable acceptance gate and contains `docker_acceptance` tests for SBX-001..SBX-005. On this host, `$env:PLWC_RUN_DOCKER_ACCEPTANCE="1"; python -m pytest tests/integration/test_sandbox_acceptance_gate.py -m docker_acceptance -q` passed with `5 passed, 3 deselected`. |
| PLWC-P0-03 DOC-001 | PASS | `test_doc_001_docker_worker_create_pdf_writes_user_target_and_validates` runs the public `plwc_document_operation(operation="create_pdf")` path without a fake adapter, uses the local `plwc-document-worker:0.1.0` Docker image, writes the PDF to the requested workspace path, validates it with `pypdf`, and verifies that any workspace intermediate artifacts remain under `Temp/`. |
| PLWC-P0-03 DOC-002 | PASS | Worker PDF and `write_binary` PDF produce distinct provenance and validation statuses; audit receives the same public fields. |

## Verification Commands

Executed in `<REPOSITORY_ROOT>`:

```powershell
Get-Process | Where-Object { $_.ProcessName -like '*docker*' }
docker --version
docker info --format 'ServerVersion={{.ServerVersion}};OSType={{.OSType}};OperatingSystem={{.OperatingSystem}};Containers={{.Containers}};Images={{.Images}}'
```

Result: Docker processes are running; `docker --version` reports Docker
`29.3.1`; `docker info` reports Docker Desktop with a reachable Linux engine.

```powershell
$env:PYTHONPATH = "src"
@'
from plwc_gateway.adapters.docker_cli import resolve_docker_executable
print(resolve_docker_executable())
'@ | python -
```

Result: `C:\Program Files\Docker\Docker\resources\bin\docker.EXE`.

```powershell
python -m py_compile src\plwc_gateway\mcp\server.py tests\integration\test_document_provenance_contract.py tests\integration\test_sandbox_acceptance_gate.py
```

Result: passed.

```powershell
git diff --check -- src/plwc_gateway/mcp/server.py tests/integration/test_document_provenance_contract.py tests/integration/test_sandbox_acceptance_gate.py pyproject.toml
```

Result: passed with Git LF/CRLF warnings only.

```powershell
python -m pytest tests/integration/test_workspace_contract.py tests/integration/test_describe_contract.py tests/integration/test_error_governance_contract.py tests/integration/test_document_provenance_contract.py tests/integration/test_sandbox_acceptance_gate.py
```

Result: 19 passed, 6 skipped when Docker acceptance is not enabled.

```powershell
$env:PLWC_RUN_DOCKER_ACCEPTANCE = "1"
python -m pytest tests/integration/test_sandbox_acceptance_gate.py -m docker_acceptance -q
```

Result: 5 passed, 3 deselected.

```powershell
$env:PLWC_RUN_DOCKER_ACCEPTANCE = "1"
python -m pytest tests/integration/test_document_provenance_contract.py -m docker_acceptance -q
```

Result: 1 passed, 3 deselected.

```powershell
$env:PLWC_RUN_DOCKER_ACCEPTANCE = "1"
python -m pytest -m docker_acceptance -q
```

Result: 6 passed, 41 deselected.

```powershell
$env:PLWC_RUN_DOCKER_ACCEPTANCE = "1"
python -m pytest
```

Result: 47 passed.

## Docker Acceptance Notes

The Docker-positive SBX/DOC acceptance tests remain gated by
`PLWC_RUN_DOCKER_ACCEPTANCE=1` so normal local test runs can stay
non-Docker-dependent. On this Docker-capable Windows host, all six checks
passed:

- SBX-001: Docker-capable system reports `sandbox_ready=true`.
- SBX-002: a file written under `/work` appears in the configured workspace.
- SBX-003: `/etc` or equivalent protected-root writes fail while `/tmp` may be writable.
- SBX-004: positive write is inside `/work`; outside-mount write fails; no dynamic canary mount is added.
- SBX-005: Docker socket and comparable engine interfaces are unavailable inside the container.
- DOC-001: a PDF is created at the requested workspace path through the real Docker document worker and technically validated.

Run them only on a Docker-capable Windows host with:

```powershell
$env:PLWC_RUN_DOCKER_ACCEPTANCE = "1"
python -m pytest -m docker_acceptance
```

## Non-H1 Items

- No version bump to 1.0.0 was performed.
- Chat Bridge changes are intentionally not part of this H1 core pass.
- Windows Setup changes are intentionally not part of this H1 core pass.
- SBX and DOC-001 have passed on this Docker-capable Windows host; a final
  release gate still requires the later Bridge/Setup pillars.
