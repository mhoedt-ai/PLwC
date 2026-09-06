from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader, PdfWriter

from plwc_gateway.audit import InMemoryAuditLogger
from plwc_gateway.adapters.document_worker import DOCUMENT_WORKER_IMAGE, WORKER_CONTAINER_WORKDIR
from plwc_gateway.config import load_gateway_config
from plwc_gateway.mcp.server import plwc_document_operation, plwc_workspace_operation


class _PdfWorkerAdapter:
    def __init__(self, workspace_root: Path, *, valid_pdf: bool = True) -> None:
        self.workspace_root = workspace_root
        self.valid_pdf = valid_pdf

    def create_pdf(self, output_path: str, **_kwargs: Any) -> dict[str, Any]:
        target = self.workspace_root / output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.valid_pdf:
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with target.open("wb") as handle:
                writer.write(handle)
        else:
            target.write_bytes(b"%PDF-invalid")
        return {
            "ok": True,
            "operation": "create_pdf",
            "status": "created",
            "worker_image": "test-document-worker",
            "policy_decision": "allow",
            "output_path": str(target),
            "file_size": target.stat().st_size,
            "changed_files": [Path(output_path).as_posix()],
            "workspace_intermediate_artifacts": [],
            "requirement_ids": ["FR-PDF-V2-001"],
        }


def _docker_document_acceptance_config(tmp_path: Path):
    if os.environ.get("PLWC_RUN_DOCKER_ACCEPTANCE") != "1":
        pytest.skip("Set PLWC_RUN_DOCKER_ACCEPTANCE=1 on a Docker-capable Windows host to run DOC acceptance tests.")
    if os.name != "nt":
        pytest.skip("DOC acceptance is defined for a Docker-capable Windows host.")
    return load_gateway_config(project_root=tmp_path)


def test_create_pdf_reports_worker_provenance_validation_and_audit(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)
    audit_logger = InMemoryAuditLogger()

    payload = plwc_document_operation(
        "create_pdf",
        output_path="Temp/doc-001/generated.pdf",
        content={"title": "DOC-001", "lines": ["validated worker PDF"]},
        config=config,
        audit_logger=audit_logger,
        adapter=_PdfWorkerAdapter(config.allowed_roots[0]),
    )

    target = config.allowed_roots[0] / "Temp" / "doc-001" / "generated.pdf"
    assert payload["ok"] is True
    assert target.is_file()
    assert len(PdfReader(str(target)).pages) == 1
    assert payload["artifact_origin"] == "document_worker"
    assert payload["artifact_origin_detail"] == "document_worker_create_pdf"
    assert payload["validation_status"] == "validated"
    assert payload["validation_detail_status"] == "technically_validated"
    assert payload["technical_validation"]["status"] == "passed"
    assert payload["technical_validation"]["page_count"] == 1
    assert payload["workspace_intermediate_artifacts"] == []
    assert "Temp/<task>/" in payload["intermediate_artifact_policy"]

    completion = [
        event for event in audit_logger.events
        if event["event"] == "tool_call_completed"
    ][-1]
    assert completion["artifact_origin"] == "document_worker"
    assert completion["validation_status"] == "validated"


def test_worker_pdf_and_workspace_binary_pdf_have_distinct_provenance(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    worker_pdf = plwc_document_operation(
        "create_pdf",
        output_path="Temp/doc-002/worker.pdf",
        content={"title": "DOC-002", "lines": ["worker PDF"]},
        config=config,
        adapter=_PdfWorkerAdapter(config.allowed_roots[0]),
    )
    binary_pdf = plwc_workspace_operation(
        "write_binary",
        path="Temp/doc-002/binary.pdf",
        content_base64=base64.b64encode(b"%PDF-workspace-binary-write").decode("ascii"),
        config=config,
    )

    assert worker_pdf["artifact_origin"] == "document_worker"
    assert worker_pdf["artifact_origin_detail"] == "document_worker_create_pdf"
    assert worker_pdf["validation_status"] == "validated"
    assert worker_pdf["validation_detail_status"] == "technically_validated"
    assert binary_pdf["artifact_origin"] == "workspace_binary_write"
    assert binary_pdf["validation_status"] == "unvalidated"
    assert worker_pdf["artifact_origin"] != binary_pdf["artifact_origin"]
    assert worker_pdf["validation_status"] != binary_pdf["validation_status"]


def test_create_pdf_fails_closed_when_worker_output_is_not_a_valid_pdf(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_document_operation(
        "create_pdf",
        output_path="Temp/doc-001/invalid.pdf",
        content={"title": "Invalid", "lines": ["not a PDF"]},
        config=config,
        adapter=_PdfWorkerAdapter(config.allowed_roots[0], valid_pdf=False),
    )

    assert payload["ok"] is False
    assert payload["artifact_origin"] == "document_worker"
    assert payload["artifact_origin_detail"] == "document_worker_create_pdf"
    assert payload["validation_status"] == "validation_failed"
    assert payload["error_category"] == "UNAVAILABLE"
    assert payload["error_detail_category"] == "document_validation_failed"
    assert payload["technical_validation"]["status"] == "failed"


@pytest.mark.docker_acceptance
def test_doc_001_docker_worker_create_pdf_writes_user_target_and_validates(tmp_path: Path) -> None:
    config = _docker_document_acceptance_config(tmp_path)

    payload = plwc_document_operation(
        "create_pdf",
        output_path="Temp/doc-001/docker-worker.pdf",
        content={
            "title": "DOC-001 Docker Worker Acceptance",
            "lines": [
                "This PDF was created through the real Docker document worker.",
                "The public PLwC payload must report validated worker provenance.",
            ],
        },
        config=config,
    )

    target = config.allowed_roots[0] / "Temp" / "doc-001" / "docker-worker.pdf"
    assert payload["ok"] is True, payload
    assert target.is_file()
    assert len(PdfReader(str(target)).pages) >= 1
    assert payload["worker_image"] == DOCUMENT_WORKER_IMAGE
    assert payload["worker_mount"] == WORKER_CONTAINER_WORKDIR
    assert payload["runtime"]["pull_policy"] == "never"
    assert payload["runtime"]["network"] == "none"
    assert payload["output_path"] == "Temp/doc-001/docker-worker.pdf"
    assert payload["changed_files"] == ["Temp/doc-001/docker-worker.pdf"]
    assert payload["artifact_origin"] == "document_worker"
    assert payload["artifact_origin_detail"] == "document_worker_create_pdf"
    assert payload["validation_status"] == "validated"
    assert payload["validation_detail_status"] == "technically_validated"
    assert payload["technical_validation"]["status"] == "passed"
    assert Path(payload["technical_validation"]["path"]).resolve() == target.resolve()
    assert payload["technical_validation"]["page_count"] >= 1
    assert all(
        Path(path).parts and Path(path).parts[0] == "Temp"
        for path in payload["workspace_intermediate_artifacts"]
    )
