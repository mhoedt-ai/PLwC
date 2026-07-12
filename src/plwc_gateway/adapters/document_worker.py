"""Internal Docker-backed Document Worker adapter.

This adapter is intentionally not exposed as a public MCP tool yet. It provides
the controlled runtime boundary for future governed document operations while
keeping the gateway runtime dependency set slim.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from plwc_gateway.config import load_gateway_config
from plwc_gateway.policy.paths import guard_path


DOCUMENT_WORKER_IMAGE = "plwc-document-worker:0.1.0"
WORKER_CONTAINER_WORKDIR = "/work"
WORKER_TMPFS_SPEC = "/tmp:rw,noexec,nosuid,nodev,size=128m"
WORKER_CONTAINER_USER = "65532:65532"

DOCUMENT_WORKER_REQUIREMENT_IDS = (
    "FR-DOC-MVP-001",
    "FR-DOC-MVP-002",
    "FR-DOC-MVP-003",
    "FR-DOC-MVP-008",
    "FR-DOC-MVP-009",
    "FR-DOC-MVP-010",
    "FR-DOC-MVP-012",
    "FR-DOC-MVP-013",
    "FR-DOC-MVP-014",
)

SUPPORTED_CREATE_OPERATIONS: Mapping[str, str] = {
    "create_docx": ".docx",
    "create_xlsx": ".xlsx",
    "create_pptx": ".pptx",
    "create_pdf": ".pdf",
}
SUPPORTED_EDIT_OPERATIONS: frozenset[str] = frozenset({"edit_docx"})
SUPPORTED_PDF_OPERATIONS = frozenset(
    {
        "inspect_pdf",
        "merge_pdf",
        "split_pdf",
        "extract_pdf",
        "rotate_pdf",
        "extract_pdf_text",
    }
)
SUPPORTED_ZIP_OPERATIONS = frozenset({"inspect_zip", "extract_zip", "create_zip"})
SUPPORTED_OFFICE_OPERATIONS = frozenset(
    {
        "inspect_docx",
        "extract_docx_text",
        "inspect_xlsx",
        "extract_xlsx_data",
        "inspect_pptx",
        "extract_pptx_text",
        "inspect_odt",
        "extract_odt_text",
        "inspect_ods",
        "extract_ods_data",
        "inspect_odp",
        "extract_odp_text",
    }
)
SUPPORTED_IMAGE_READ_OPERATIONS = frozenset({"read_image"})

WORKER_COMMANDS: Mapping[str, str] = {
    "create_docx": "create-docx",
    "edit_docx": "edit-docx",
    "create_xlsx": "create-xlsx",
    "create_pptx": "create-pptx",
    "create_pdf": "create-pdf",
    "inspect_pdf": "inspect-pdf",
    "merge_pdf": "merge-pdf",
    "split_pdf": "split-pdf",
    "extract_pdf": "extract-pdf",
    "rotate_pdf": "rotate-pdf",
    "extract_pdf_text": "extract-pdf-text",
    "inspect_zip": "inspect-zip",
    "extract_zip": "extract-zip",
    "create_zip": "create-zip",
    "inspect_docx": "inspect-docx",
    "extract_docx_text": "extract-docx-text",
    "inspect_xlsx": "inspect-xlsx",
    "extract_xlsx_data": "extract-xlsx-data",
    "inspect_pptx": "inspect-pptx",
    "extract_pptx_text": "extract-pptx-text",
    "inspect_odt": "inspect-odt",
    "extract_odt_text": "extract-odt-text",
    "inspect_ods": "inspect-ods",
    "extract_ods_data": "extract-ods-data",
    "inspect_odp": "inspect-odp",
    "extract_odp_text": "extract-odp-text",
    "read_image": "read-image",
}

PROTECTED_OUTPUT_SEGMENTS = {"profile", "profiles", "governance"}
PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE = 1_500_000_000
PDF_MAX_INPUT_FILES = 8
PDF_MAX_MERGE_OUTPUT_PAGES = 100
PDF_MAX_EXTRACT_OUTPUT_PAGES = 50
PDF_MAX_SPLIT_OUTPUT_FILES = 250
PDF_MAX_ROTATE_ALL_PAGES = 100
PDF_MAX_ROTATE_SELECTED_PAGES = 50
PDF_TEXT_MAX_PAGES = 50
PDF_TEXT_MAX_CHARS = 500_000
PDF_TEXT_MAX_PREVIEW_CHARS = 1_000
ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE = 2_000_000_000
ZIP_MAX_ENTRIES = 5_000
ZIP_MAX_EXTRACTED_BYTES = 750_000_000
ZIP_MAX_SINGLE_FILE_BYTES = 250_000_000
ZIP_MAX_PATH_LENGTH = 240
ZIP_MAX_COMPRESSION_RATIO = 100
ZIP_MAX_NESTED_DEPTH = 40
OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE = 1_000_000_000
OFFICE_MAX_TEXT_CHARS = 500_000
OFFICE_MAX_PREVIEW_CHARS = 1_000
OFFICE_MAX_XLSX_SHEETS = 10
OFFICE_MAX_XLSX_ROWS = 2_000
OFFICE_MAX_XLSX_CELLS = 50_000
OFFICE_MAX_PPTX_SLIDES = 250
OFFICE_MAX_ODF_TABLES = 10
OFFICE_MAX_ODF_ROWS = 2_000
OFFICE_MAX_ODF_CELLS = 50_000
OFFICE_MAX_XML_PART_BYTES = 100_000_000
DOCX_V2_MAX_JSON_INPUT_BYTES = 10_000_000
DOCX_V2_MAX_CONTENT_ELEMENTS = 20_000
DOCX_V2_MAX_PARAGRAPHS = 20_000
DOCX_V2_MAX_TABLES = 200
DOCX_V2_MAX_TABLE_CELLS = 100_000
DOCX_V2_MAX_IMAGES = 100
DOCX_V2_MAX_IMAGE_BYTES = 10_000_000
DOCX_V2_MAX_OUTPUT_BYTES = 200_000_000
XLSX_V2_MAX_JSON_INPUT_BYTES = 10_000_000
XLSX_V2_MAX_SHEETS = 50
XLSX_V2_MAX_ROWS_PER_SHEET = 100_000
XLSX_V2_MAX_COLUMNS_PER_SHEET = 256
XLSX_V2_MAX_CELLS_PER_SHEET = 500_000
XLSX_V2_MAX_TOTAL_CELLS = 1_000_000
XLSX_V2_MAX_MERGED_RANGES = 1_000
XLSX_V2_MAX_OUTPUT_BYTES = 200_000_000
PPTX_V2_MAX_JSON_INPUT_BYTES = 10_000_000
PPTX_V2_MAX_SLIDES = 250
PPTX_V2_MAX_CONTENT_ELEMENTS_PER_SLIDE = 50
PPTX_V2_MAX_BULLET_ITEMS_PER_SLIDE = 200
PPTX_V2_MAX_TABLES_PER_SLIDE = 5
PPTX_V2_MAX_TABLE_CELLS_PER_SLIDE = 2_000
PPTX_V2_MAX_IMAGES = 100
PPTX_V2_MAX_IMAGE_BYTES = 10_000_000
PPTX_V2_MAX_OUTPUT_BYTES = 200_000_000
PDF_V2_MAX_JSON_INPUT_BYTES = 10_000_000
PDF_V2_MAX_CONTENT_ELEMENTS = 20_000
PDF_V2_MAX_PARAGRAPHS = 20_000
PDF_V2_MAX_TABLES = 200
PDF_V2_MAX_TABLE_CELLS = 100_000
PDF_V2_MAX_IMAGES = 100
PDF_V2_MAX_IMAGE_BYTES = 10_000_000
PDF_V2_MAX_OUTPUT_BYTES = 200_000_000
READ_IMAGE_DEFAULT_MAX_SIZE_KB = 2_048
READ_IMAGE_HARD_MAX_SIZE_KB = 5_120
READ_IMAGE_SUPPORTED_INPUT_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
READ_IMAGE_SUPPORTED_INPUT_FORMATS = ("png", "jpg", "jpeg", "webp", "gif")
READ_IMAGE_OUTPUT_FORMATS = frozenset({"png", "jpeg", "webp"})
DOCUMENT_WORKER_IMPORTS = (
    "pypdf",
    "docx",
    "openpyxl",
    "pptx",
    "reportlab",
    "weasyprint",
    "odf",
    "pandas",
    "defusedxml",
    "PIL",
)
PDF_WORKER_REQUIREMENT_IDS = DOCUMENT_WORKER_REQUIREMENT_IDS + (
    "FR-PDF-MVP-001",
    "FR-PDF-MVP-002",
    "FR-PDF-MVP-003",
    "FR-PDF-MVP-004",
    "FR-PDF-MVP-005",
    "FR-PDF-MVP-006",
    "FR-PDF-MVP-007",
    "FR-PDF-MVP-008",
    "FR-PDF-MVP-009",
    "FR-PDF-MVP-010",
    "FR-PDF-MVP-011",
    "FR-PDF-MVP-012",
)
PDF_TEXT_REQUIREMENT_IDS = PDF_WORKER_REQUIREMENT_IDS + (
    "FR-PDF-TEXT-001",
    "FR-PDF-TEXT-002",
    "FR-PDF-TEXT-003",
    "FR-PDF-TEXT-004",
    "FR-PDF-TEXT-005",
)
ZIP_WORKER_REQUIREMENT_IDS = DOCUMENT_WORKER_REQUIREMENT_IDS + (
    "FR-ARCH-MVP-001",
    "FR-ARCH-MVP-002",
    "FR-ARCH-MVP-003",
    "FR-ARCH-MVP-004",
    "FR-ARCH-MVP-005",
    "FR-ARCH-MVP-006",
    "FR-ARCH-MVP-007",
    "FR-ARCH-MVP-008",
    "FR-ARCH-MVP-009",
    "FR-ARCH-MVP-010",
)
OFFICE_WORKER_REQUIREMENT_IDS = DOCUMENT_WORKER_REQUIREMENT_IDS + (
    "FR-OFFICE-MVP-001",
    "FR-OFFICE-MVP-002",
    "FR-OFFICE-MVP-003",
    "FR-OFFICE-MVP-004",
    "FR-OFFICE-MVP-005",
    "FR-OFFICE-MVP-006",
    "FR-OFFICE-MVP-007",
    "FR-OFFICE-MVP-008",
    "FR-OFFICE-MVP-009",
    "FR-OFFICE-MVP-010",
    "FR-OFFICE-MVP-011",
    "FR-OFFICE-MVP-012",
)
EDIT_DOCX_MAX_INPUT_BYTES = OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE
EDIT_DOCX_MAX_OUTPUT_BYTES = 200_000_000
EDIT_DOCX_MAX_XML_PART_BYTES = OFFICE_MAX_XML_PART_BYTES
EDIT_DOCX_REQUIREMENT_IDS = DOCUMENT_WORKER_REQUIREMENT_IDS + (
    "FR-DOCX-EDIT-001",
    "FR-DOCX-EDIT-002",
    "FR-DOCX-EDIT-003",
    "FR-DOCX-EDIT-004",
    "FR-DOCX-EDIT-005",
    "FR-DOCX-EDIT-006",
    "FR-DOCX-EDIT-007",
    "FR-DOCX-EDIT-008",
    "FR-DOCX-EDIT-009",
    "FR-DOCX-EDIT-010",
)
DOCX_V2_REQUIREMENT_IDS = OFFICE_WORKER_REQUIREMENT_IDS + (
    "FR-DOCX-V2-001",
    "FR-DOCX-V2-002",
    "FR-DOCX-V2-003",
    "FR-DOCX-V2-004",
    "FR-DOCX-V2-005",
    "FR-DOCX-V2-006",
    "FR-DOCX-V2-007",
    "FR-DOCX-V2-008",
    "FR-DOCX-V2-009",
    "FR-DOCX-V2-010",
)
XLSX_V2_REQUIREMENT_IDS = OFFICE_WORKER_REQUIREMENT_IDS + (
    "FR-XLSX-V2-001",
    "FR-XLSX-V2-002",
    "FR-XLSX-V2-003",
    "FR-XLSX-V2-004",
    "FR-XLSX-V2-005",
    "FR-XLSX-V2-006",
    "FR-XLSX-V2-007",
    "FR-XLSX-V2-008",
    "FR-XLSX-V2-009",
    "FR-XLSX-V2-010",
)
PPTX_V2_REQUIREMENT_IDS = OFFICE_WORKER_REQUIREMENT_IDS + (
    "FR-PPTX-V2-001",
    "FR-PPTX-V2-002",
    "FR-PPTX-V2-003",
    "FR-PPTX-V2-004",
    "FR-PPTX-V2-005",
    "FR-PPTX-V2-006",
    "FR-PPTX-V2-007",
    "FR-PPTX-V2-008",
    "FR-PPTX-V2-009",
    "FR-PPTX-V2-010",
)
PDF_V2_REQUIREMENT_IDS = PDF_WORKER_REQUIREMENT_IDS + (
    "FR-PDF-V2-001",
    "FR-PDF-V2-002",
    "FR-PDF-V2-003",
    "FR-PDF-V2-004",
    "FR-PDF-V2-005",
    "FR-PDF-V2-006",
    "FR-PDF-V2-007",
    "FR-PDF-V2-008",
    "FR-PDF-V2-009",
    "FR-PDF-V2-010",
)
IMAGE_READ_REQUIREMENT_IDS = DOCUMENT_WORKER_REQUIREMENT_IDS + (
    "FR-IMG-001",
    "FR-IMG-002",
    "FR-IMG-003",
    "FR-IMG-004",
)


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DocumentWorkerResult:
    """Structured internal result for document worker operations."""

    ok: bool
    operation: str
    status: str
    worker_image: str
    policy_decision: str
    output_path: str | None = None
    file_size: int | None = None
    error_category: str | None = None
    error: str | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    docker_args: tuple[str, ...] = ()
    requirement_ids: tuple[str, ...] = DOCUMENT_WORKER_REQUIREMENT_IDS
    extra: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "operation": self.operation,
            "status": self.status,
            "worker_image": self.worker_image,
            "policy_decision": self.policy_decision,
            "requirement_ids": list(self.requirement_ids),
        }
        if self.output_path is not None:
            payload["output_path"] = self.output_path
        if self.file_size is not None:
            payload["file_size"] = self.file_size
        if self.error_category is not None:
            payload["error_category"] = self.error_category
        if self.error is not None:
            payload["error"] = self.error
        if self.exit_code is not None:
            payload["exit_code"] = self.exit_code
        if self.stdout:
            payload["stdout"] = self.stdout
        if self.stderr:
            payload["stderr"] = self.stderr
        if self.docker_args:
            payload["docker_args"] = list(self.docker_args)
        if self.extra:
            for key, value in self.extra.items():
                payload.setdefault(str(key), value)
        return payload


class DocumentWorkerAdapter:
    """Run document creation smoke operations inside the prepared worker image."""

    def __init__(
        self,
        *,
        workspace_roots: Iterable[Path | str] | None = None,
        worker_image: str = DOCUMENT_WORKER_IMAGE,
        runner: Runner = subprocess.run,
        timeout_seconds: int = 120,
        memory: str = "512m",
        cpus: str = "1.0",
        pids_limit: int = 256,
    ) -> None:
        if workspace_roots is None:
            config = load_gateway_config()
            roots = list(config.allowed_roots)
        else:
            roots = list(workspace_roots)
        if not roots:
            roots = [Path.cwd()]
        self.workspace_root = Path(roots[0]).expanduser().resolve()
        self.workspace_roots = [Path(root).expanduser().resolve() for root in roots]
        self.worker_image = worker_image
        self.runner = runner
        self.timeout_seconds = timeout_seconds
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit

    def status(self) -> DocumentWorkerResult:
        inspect = self._inspect_image()
        if inspect.returncode != 0:
            return self._failure(
                operation="status",
                category=_worker_status_category(inspect.stderr or inspect.stdout),
                error=self._combined_error(inspect) or "Document worker image is not available locally.",
                exit_code=inspect.returncode,
                stdout=inspect.stdout or "",
                stderr=inspect.stderr or "",
            )
        return DocumentWorkerResult(
            ok=True,
            operation="status",
            status="available",
            worker_image=self.worker_image,
            policy_decision="allow",
            stdout=inspect.stdout or "",
            stderr=inspect.stderr or "",
        )

    def probe_dependencies(self) -> DocumentWorkerResult:
        return self._run_worker("probe_dependencies", None, ["probe"])

    def create_docx(
        self,
        output_path: str | Path,
        *,
        title: str = "PLwC DOCX Smoke",
        body: str = "Document Worker DOCX smoke test.",
        content: Mapping[str, Any] | None = None,
        input_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._create(
            "create_docx",
            output_path,
            title=title,
            body=body,
            content=content,
            input_path=input_path,
            overwrite=overwrite,
        )

    def create_xlsx(
        self,
        output_path: str | Path,
        *,
        title: str = "PLwC XLSX Smoke",
        body: str = "Document Worker XLSX smoke test.",
        content: Mapping[str, Any] | None = None,
        input_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._create(
            "create_xlsx",
            output_path,
            title=title,
            body=body,
            content=content,
            input_path=input_path,
            overwrite=overwrite,
        )

    def create_pptx(
        self,
        output_path: str | Path,
        *,
        title: str = "PLwC PPTX Smoke",
        body: str = "Document Worker PPTX smoke test.",
        content: Mapping[str, Any] | None = None,
        input_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._create(
            "create_pptx",
            output_path,
            title=title,
            body=body,
            content=content,
            input_path=input_path,
            overwrite=overwrite,
        )

    def create_pdf(
        self,
        output_path: str | Path,
        *,
        title: str = "PLwC PDF Smoke",
        body: str = "Document Worker PDF smoke test.",
        content: Mapping[str, Any] | None = None,
        input_path: str | Path | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._create(
            "create_pdf",
            output_path,
            title=title,
            body=body,
            content=content,
            input_path=input_path,
            overwrite=overwrite,
        )

    def edit_docx(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        content: Mapping[str, Any] | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        input_check = self._resolve_input_path(input_path, ".docx", requirement_ids=EDIT_DOCX_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, input_file_size = input_check
        if input_file_size > EDIT_DOCX_MAX_INPUT_BYTES:
            return self._failure(
                operation="edit_docx",
                category="limit_exceeded",
                error=f"edit_docx input exceeds limit of {EDIT_DOCX_MAX_INPUT_BYTES} bytes.",
                requirement_ids=EDIT_DOCX_REQUIREMENT_IDS,
            )
        output_check = self._resolve_output_path(output_path, ".docx", overwrite=overwrite, requirement_ids=EDIT_DOCX_REQUIREMENT_IDS)
        if isinstance(output_check, DocumentWorkerResult):
            return output_check
        host_output, worker_output = output_check
        edits_json = json.dumps(list((content or {}).get("edits", [])))
        command = [
            WORKER_COMMANDS["edit_docx"],
            "--input",
            worker_input,
            "--output",
            worker_output,
            "--edits-json",
            edits_json,
            "--max-input-bytes",
            str(EDIT_DOCX_MAX_INPUT_BYTES),
            "--max-xml-part-bytes",
            str(EDIT_DOCX_MAX_XML_PART_BYTES),
        ]
        result = self._run_worker("edit_docx", host_output, command, requirement_ids=EDIT_DOCX_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", self._host_path_to_relative(host_input))
            extra.setdefault("input_file_size", input_file_size)
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            if result.file_size is not None and result.file_size > EDIT_DOCX_MAX_OUTPUT_BYTES:
                return self._failure(
                    operation="edit_docx",
                    category="limit_exceeded",
                    error=f"edit_docx output exceeds limit of {EDIT_DOCX_MAX_OUTPUT_BYTES} bytes.",
                    requirement_ids=EDIT_DOCX_REQUIREMENT_IDS,
                )
            return self._with_extra(result, extra)
        return result

    def read_image(
        self,
        input_path: str | Path,
        *,
        max_size_kb: int | None = None,
        resize_to: str = "",
        output_format: str = "png",
    ) -> DocumentWorkerResult:
        effective_max_size_kb = self._bounded_positive_int(
            "max_size_kb",
            max_size_kb,
            default=READ_IMAGE_DEFAULT_MAX_SIZE_KB,
            upper_bound=READ_IMAGE_HARD_MAX_SIZE_KB,
            operation="read_image",
            requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_size_kb, DocumentWorkerResult):
            return effective_max_size_kb
        normalized_format = output_format.strip().casefold() if isinstance(output_format, str) else ""
        if normalized_format not in READ_IMAGE_OUTPUT_FORMATS:
            return self._failure(
                operation="read_image",
                category="validation_error",
                error="read_image format must be png, jpeg or webp.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        if resize_to and not _valid_resize_to(resize_to):
            return self._failure(
                operation="read_image",
                category="validation_error",
                error="resize_to must be WIDTHxHEIGHT or N%.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )

        input_check = self._resolve_image_input_path(input_path)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        hard_max_bytes = READ_IMAGE_HARD_MAX_SIZE_KB * 1024
        max_size_bytes = effective_max_size_kb * 1024
        too_large_extra = {
            "file_size_bytes": file_size,
            "suggestion": "Use resize_to parameter to reduce image size before transfer, e.g. resize_to='1024x1024' or resize_to='50%'",
        }
        if file_size > hard_max_bytes:
            return self._failure(
                operation="read_image",
                category="policy_violation",
                error="file_too_large",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
                extra={**too_large_extra, "max_size_bytes": hard_max_bytes},
            )
        if file_size > max_size_bytes and not resize_to:
            return self._failure(
                operation="read_image",
                category="policy_violation",
                error="file_too_large",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
                extra={**too_large_extra, "max_size_bytes": max_size_bytes},
            )

        command = [
            WORKER_COMMANDS["read_image"],
            "--input",
            worker_input,
            "--max-size-bytes",
            str(max_size_bytes),
            "--hard-max-size-bytes",
            str(hard_max_bytes),
            "--format",
            normalized_format,
        ]
        if resize_to:
            command.extend(["--resize-to", resize_to])
        result = self._run_worker(
            "read_image",
            None,
            command,
            requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            allow_empty_output=True,
        )
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", self._host_path_to_relative(host_input))
            extra.setdefault("source_file_size_bytes", file_size)
            return self._with_extra(result, extra)
        return result

    def inspect_pdf(self, input_path: str | Path) -> DocumentWorkerResult:
        input_check = self._resolve_input_path(input_path, ".pdf")
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        command = [
            WORKER_COMMANDS["inspect_pdf"],
            "--input",
            worker_input,
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
        ]
        result = self._run_worker("inspect_pdf", None, command, requirement_ids=PDF_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            return self._with_extra(result, extra)
        return result

    def merge_pdf(
        self,
        input_paths: Sequence[str | Path],
        output_path: str | Path,
        *,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        if len(input_paths) < 2:
            return self._failure(
                operation="merge_pdf",
                category="validation_error",
                error="merge_pdf requires at least two input PDFs.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        if len(input_paths) > PDF_MAX_INPUT_FILES:
            return self._failure(
                operation="merge_pdf",
                category="limit_exceeded",
                error=f"merge_pdf supports at most {PDF_MAX_INPUT_FILES} input PDFs.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        resolved_inputs = self._resolve_input_paths(input_paths)
        if isinstance(resolved_inputs, DocumentWorkerResult):
            return resolved_inputs
        host_inputs, worker_inputs, total_size = resolved_inputs
        output_check = self._resolve_output_path(output_path, ".pdf", overwrite=overwrite)
        if isinstance(output_check, DocumentWorkerResult):
            return output_check
        host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS["merge_pdf"],
            "--inputs-json",
            json.dumps(worker_inputs),
            "--output",
            worker_output,
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-pages",
            str(PDF_MAX_MERGE_OUTPUT_PAGES),
        ]
        result = self._run_worker("merge_pdf", host_output, command, requirement_ids=PDF_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_paths", [str(path) for path in host_inputs])
            extra.setdefault("input_file_count", len(host_inputs))
            extra.setdefault("total_input_size", total_size)
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def split_pdf(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        *,
        mode: str = "pages",
    ) -> DocumentWorkerResult:
        if mode != "pages":
            return self._failure(
                operation="split_pdf",
                category="unsupported_mode",
                error="split_pdf currently supports mode=pages only.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        input_check = self._resolve_input_path(input_path, ".pdf")
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, _file_size = input_check
        dir_check = self._resolve_output_dir(output_dir)
        if isinstance(dir_check, DocumentWorkerResult):
            return dir_check
        host_output_dir, worker_output_dir = dir_check
        command = [
            WORKER_COMMANDS["split_pdf"],
            "--input",
            worker_input,
            "--output-dir",
            worker_output_dir,
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-output-files",
            str(PDF_MAX_SPLIT_OUTPUT_FILES),
        ]
        result = self._run_worker("split_pdf", None, command, requirement_ids=PDF_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            created_files = [
                self._worker_path_to_relative(str(path))
                for path in extra.get("created_files", [])
            ]
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("output_dir", str(host_output_dir))
            extra["created_files"] = created_files
            extra["changed_files"] = created_files
            return self._with_extra(result, extra)
        return result

    def extract_pdf(
        self,
        input_path: str | Path,
        output_path: str | Path,
        pages: Sequence[int | str],
        *,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        normalized_pages = self._normalize_pages(pages, require_non_empty=True)
        if isinstance(normalized_pages, DocumentWorkerResult):
            return normalized_pages
        selected_page_count = self._page_selector_count(normalized_pages)
        if selected_page_count > PDF_MAX_EXTRACT_OUTPUT_PAGES:
            return self._failure(
                operation="extract_pdf",
                category="limit_exceeded",
                error=f"extract_pdf supports at most {PDF_MAX_EXTRACT_OUTPUT_PAGES} output pages.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        input_check = self._resolve_input_path(input_path, ".pdf")
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, _file_size = input_check
        output_check = self._resolve_output_path(output_path, ".pdf", overwrite=overwrite)
        if isinstance(output_check, DocumentWorkerResult):
            return output_check
        host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS["extract_pdf"],
            "--input",
            worker_input,
            "--output",
            worker_output,
            "--pages-json",
            json.dumps(normalized_pages),
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-pages",
            str(PDF_MAX_EXTRACT_OUTPUT_PAGES),
        ]
        result = self._run_worker("extract_pdf", host_output, command, requirement_ids=PDF_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def rotate_pdf(
        self,
        input_path: str | Path,
        output_path: str | Path,
        rotation: int,
        pages: Sequence[int | str] | None = None,
        *,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        if rotation not in {90, 180, 270}:
            return self._failure(
                operation="rotate_pdf",
                category="validation_error",
                error="rotate_pdf rotation must be 90, 180 or 270.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        normalized_pages = self._normalize_pages(pages or (), require_non_empty=False)
        if isinstance(normalized_pages, DocumentWorkerResult):
            return normalized_pages
        selected_page_count = self._page_selector_count(normalized_pages)
        if selected_page_count > PDF_MAX_ROTATE_SELECTED_PAGES:
            return self._failure(
                operation="rotate_pdf",
                category="limit_exceeded",
                error=f"rotate_pdf supports at most {PDF_MAX_ROTATE_SELECTED_PAGES} selected affected pages.",
                requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
            )
        input_check = self._resolve_input_path(input_path, ".pdf")
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, _file_size = input_check
        output_check = self._resolve_output_path(output_path, ".pdf", overwrite=overwrite)
        if isinstance(output_check, DocumentWorkerResult):
            return output_check
        host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS["rotate_pdf"],
            "--input",
            worker_input,
            "--output",
            worker_output,
            "--rotation",
            str(rotation),
            "--pages-json",
            json.dumps(normalized_pages),
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-all-pages",
            str(PDF_MAX_ROTATE_ALL_PAGES),
            "--max-selected-pages",
            str(PDF_MAX_ROTATE_SELECTED_PAGES),
        ]
        result = self._run_worker("rotate_pdf", host_output, command, requirement_ids=PDF_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("rotation", rotation)
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def extract_pdf_text(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        output_format: str = "text",
        pages: Sequence[int | str] | None = None,
        max_pages: int | None = None,
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        normalized_format = output_format.strip().casefold() if isinstance(output_format, str) else ""
        if normalized_format not in {"text", "json"}:
            return self._failure(
                operation="extract_pdf_text",
                category="validation_error",
                error="extract_pdf_text format must be text or json.",
                requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
            )
        normalized_pages = self._normalize_pages(pages or (), require_non_empty=False)
        if isinstance(normalized_pages, DocumentWorkerResult):
            return normalized_pages
        effective_max_pages = self._bounded_positive_int(
            "max_pages",
            max_pages,
            default=PDF_TEXT_MAX_PAGES,
            upper_bound=PDF_TEXT_MAX_PAGES,
            operation="extract_pdf_text",
            requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_pages, DocumentWorkerResult):
            return effective_max_pages
        selected_page_count = self._page_selector_count(normalized_pages)
        if selected_page_count > effective_max_pages:
            return self._failure(
                operation="extract_pdf_text",
                category="limit_exceeded",
                error=f"extract_pdf_text supports at most {effective_max_pages} selected pages.",
                requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
            )
        effective_max_chars = self._bounded_positive_int(
            "max_chars",
            max_chars,
            default=PDF_TEXT_MAX_CHARS,
            upper_bound=PDF_TEXT_MAX_CHARS,
            operation="extract_pdf_text",
            requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_chars, DocumentWorkerResult):
            return effective_max_chars
        effective_preview_chars = self._bounded_positive_int(
            "max_preview_chars",
            max_preview_chars,
            default=PDF_TEXT_MAX_PREVIEW_CHARS,
            upper_bound=PDF_TEXT_MAX_PREVIEW_CHARS,
            operation="extract_pdf_text",
            requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
        )
        if isinstance(effective_preview_chars, DocumentWorkerResult):
            return effective_preview_chars

        input_check = self._resolve_input_path(input_path, ".pdf")
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check

        host_output: Path | None = None
        worker_output = ""
        if output_path:
            suffix = ".txt" if normalized_format == "text" else ".json"
            output_check = self._resolve_output_path(output_path, suffix, overwrite=overwrite)
            if isinstance(output_check, DocumentWorkerResult):
                return output_check
            host_output, worker_output = output_check

        command = [
            WORKER_COMMANDS["extract_pdf_text"],
            "--input",
            worker_input,
            "--format",
            normalized_format,
            "--pages-json",
            json.dumps(normalized_pages),
            "--max-input-bytes",
            str(PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-pages",
            str(effective_max_pages),
            "--max-chars",
            str(effective_max_chars),
            "--max-preview-chars",
            str(effective_preview_chars),
        ]
        if worker_output:
            command.extend(["--output", worker_output])
        if include_preview:
            command.append("--include-preview")

        result = self._run_worker(
            "extract_pdf_text",
            host_output,
            command,
            requirement_ids=PDF_TEXT_REQUIREMENT_IDS,
            allow_empty_output=True,
        )
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            extra.setdefault("format", normalized_format)
            if host_output is not None:
                extra.setdefault("output_file_size", result.file_size)
                extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def inspect_zip(self, input_path: str | Path) -> DocumentWorkerResult:
        input_check = self._resolve_input_path(input_path, ".zip", requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        command = [
            WORKER_COMMANDS["inspect_zip"],
            "--input",
            worker_input,
            "--max-input-bytes",
            str(ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-entries",
            str(ZIP_MAX_ENTRIES),
            "--max-total-uncompressed-bytes",
            str(ZIP_MAX_EXTRACTED_BYTES),
            "--max-single-file-bytes",
            str(ZIP_MAX_SINGLE_FILE_BYTES),
            "--max-path-length",
            str(ZIP_MAX_PATH_LENGTH),
            "--max-compression-ratio",
            str(ZIP_MAX_COMPRESSION_RATIO),
            "--max-depth",
            str(ZIP_MAX_NESTED_DEPTH),
        ]
        result = self._run_worker("inspect_zip", None, command, requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            return self._with_extra(result, extra)
        return result

    def extract_zip(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        if overwrite:
            return self._failure(
                operation="extract_zip",
                category="overwrite_not_supported",
                error="ZIP extraction overwrite is not supported in this slice.",
                requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
            )
        input_check = self._resolve_input_path(input_path, ".zip", requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        dir_check = self._resolve_output_dir(output_dir, requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if isinstance(dir_check, DocumentWorkerResult):
            return dir_check
        host_output_dir, worker_output_dir = dir_check
        if host_output_dir.exists() and not host_output_dir.is_dir():
            return self._failure(
                operation="extract_zip",
                category="target_is_file",
                error="ZIP extraction output_dir points at an existing file; expected a directory or a non-existent path.",
                requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
            )
        command = [
            WORKER_COMMANDS["extract_zip"],
            "--input",
            worker_input,
            "--output-dir",
            worker_output_dir,
            "--max-input-bytes",
            str(ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-entries",
            str(ZIP_MAX_ENTRIES),
            "--max-total-uncompressed-bytes",
            str(ZIP_MAX_EXTRACTED_BYTES),
            "--max-single-file-bytes",
            str(ZIP_MAX_SINGLE_FILE_BYTES),
            "--max-path-length",
            str(ZIP_MAX_PATH_LENGTH),
            "--max-compression-ratio",
            str(ZIP_MAX_COMPRESSION_RATIO),
            "--max-depth",
            str(ZIP_MAX_NESTED_DEPTH),
        ]
        result = self._run_worker("extract_zip", None, command, requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            created_files = [
                self._worker_path_to_relative(str(path))
                for path in extra.get("created_files", [])
            ]
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            extra.setdefault("output_dir", str(host_output_dir))
            extra["created_files"] = created_files
            extra["changed_files"] = created_files
            return self._with_extra(result, extra)
        return result

    def create_zip(
        self,
        output_path: str | Path,
        *,
        input_path: str | Path | None = None,
        input_paths: Sequence[str | Path] | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        if overwrite:
            return self._failure(
                operation="create_zip",
                category="overwrite_not_supported",
                error="ZIP creation overwrite is not supported in this slice.",
                requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
            )
        raw_inputs: list[str | Path] = []
        if input_path:
            raw_inputs.append(input_path)
        raw_inputs.extend(input_paths or [])
        if not raw_inputs:
            return self._failure(
                operation="create_zip",
                category="validation_error",
                error="create_zip requires input_path or input_paths.",
                requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
            )
        resolved_inputs = self._resolve_zip_source_paths(raw_inputs)
        if isinstance(resolved_inputs, DocumentWorkerResult):
            return resolved_inputs
        host_inputs, worker_inputs = resolved_inputs
        output_check = self._resolve_output_path(output_path, ".zip", overwrite=overwrite, requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if isinstance(output_check, DocumentWorkerResult):
            return output_check
        host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS["create_zip"],
            "--inputs-json",
            json.dumps(worker_inputs),
            "--output",
            worker_output,
            "--max-files",
            str(ZIP_MAX_ENTRIES),
            "--max-total-input-bytes",
            str(ZIP_MAX_EXTRACTED_BYTES),
            "--max-single-file-bytes",
            str(ZIP_MAX_SINGLE_FILE_BYTES),
            "--max-path-length",
            str(ZIP_MAX_PATH_LENGTH),
            "--max-depth",
            str(ZIP_MAX_NESTED_DEPTH),
        ]
        result = self._run_worker("create_zip", host_output, command, requirement_ids=ZIP_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_paths", [str(path) for path in host_inputs])
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def inspect_docx(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_docx", input_path, ".docx")

    def extract_docx_text(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        output_format: str = "text",
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_text(
            "extract_docx_text",
            input_path,
            ".docx",
            output_path,
            output_format=output_format,
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=overwrite,
        )

    def inspect_xlsx(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_xlsx", input_path, ".xlsx")

    def extract_xlsx_data(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        sheets: Sequence[str | int] | None = None,
        ranges: Mapping[str, str] | Sequence[str] | None = None,
        max_rows: int | None = None,
        max_cells: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_data(
            "extract_xlsx_data",
            input_path,
            ".xlsx",
            output_path,
            sheets=sheets,
            ranges=ranges,
            max_rows=max_rows,
            max_cells=max_cells,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=overwrite,
        )

    def inspect_pptx(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_pptx", input_path, ".pptx")

    def extract_pptx_text(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        slides: Sequence[int | str] | None = None,
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        include_notes: bool = False,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_text(
            "extract_pptx_text",
            input_path,
            ".pptx",
            output_path,
            pages=slides,
            output_format="text",
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            include_notes=include_notes,
            overwrite=overwrite,
        )

    def inspect_odt(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_odt", input_path, ".odt")

    def extract_odt_text(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        output_format: str = "text",
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_text(
            "extract_odt_text",
            input_path,
            ".odt",
            output_path,
            output_format=output_format,
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=overwrite,
        )

    def inspect_ods(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_ods", input_path, ".ods")

    def extract_ods_data(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        sheets: Sequence[str | int] | None = None,
        ranges: Mapping[str, str] | Sequence[str] | None = None,
        max_rows: int | None = None,
        max_cells: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_data(
            "extract_ods_data",
            input_path,
            ".ods",
            output_path,
            sheets=sheets,
            ranges=ranges,
            max_rows=max_rows,
            max_cells=max_cells,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=overwrite,
        )

    def inspect_odp(self, input_path: str | Path) -> DocumentWorkerResult:
        return self._inspect_office("inspect_odp", input_path, ".odp")

    def extract_odp_text(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        slides: Sequence[int | str] | None = None,
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        include_notes: bool = False,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        return self._extract_office_text(
            "extract_odp_text",
            input_path,
            ".odp",
            output_path,
            pages=slides,
            output_format="text",
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=overwrite,
        )

    def _inspect_office(self, operation: str, input_path: str | Path, suffix: str) -> DocumentWorkerResult:
        input_check = self._resolve_input_path(input_path, suffix, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        command = [
            WORKER_COMMANDS[operation],
            "--input",
            worker_input,
            "--max-input-bytes",
            str(OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-xml-part-bytes",
            str(OFFICE_MAX_XML_PART_BYTES),
        ]
        result = self._run_worker(operation, None, command, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            return self._with_extra(result, extra)
        return result

    def _extract_office_text(
        self,
        operation: str,
        input_path: str | Path,
        suffix: str,
        output_path: str | Path | None,
        *,
        pages: Sequence[int | str] | None = None,
        output_format: str = "text",
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        include_notes: bool = False,
        overwrite: bool = False,
    ) -> DocumentWorkerResult:
        normalized_format = output_format.strip().casefold() if isinstance(output_format, str) else ""
        if normalized_format not in {"text", "json"}:
            return self._failure(
                operation=operation,
                category="validation_error",
                error=f"{operation} format must be text or json.",
                requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
            )
        normalized_pages = self._normalize_pages(pages or (), require_non_empty=False)
        if isinstance(normalized_pages, DocumentWorkerResult):
            return normalized_pages
        effective_max_chars = self._bounded_positive_int(
            "max_chars",
            max_chars,
            default=OFFICE_MAX_TEXT_CHARS,
            upper_bound=OFFICE_MAX_TEXT_CHARS,
            operation=operation,
            requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_chars, DocumentWorkerResult):
            return effective_max_chars
        effective_preview_chars = self._bounded_positive_int(
            "max_preview_chars",
            max_preview_chars,
            default=OFFICE_MAX_PREVIEW_CHARS,
            upper_bound=OFFICE_MAX_PREVIEW_CHARS,
            operation=operation,
            requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
        )
        if isinstance(effective_preview_chars, DocumentWorkerResult):
            return effective_preview_chars
        slide_limit = OFFICE_MAX_PPTX_SLIDES if suffix in {".pptx", ".odp"} else None
        if slide_limit is not None and self._page_selector_count(normalized_pages) > slide_limit:
            return self._failure(
                operation=operation,
                category="limit_exceeded",
                error=f"{operation} supports at most {slide_limit} selected slides/pages.",
                requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
            )
        input_check = self._resolve_input_path(input_path, suffix, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        host_output: Path | None = None
        worker_output = ""
        if output_path:
            expected_output_suffix = ".txt" if normalized_format == "text" else ".json"
            output_check = self._resolve_output_path(output_path, expected_output_suffix, overwrite=overwrite, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
            if isinstance(output_check, DocumentWorkerResult):
                return output_check
            host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS[operation],
            "--input",
            worker_input,
            "--format",
            normalized_format,
            "--pages-json",
            json.dumps(normalized_pages),
            "--max-input-bytes",
            str(OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-chars",
            str(effective_max_chars),
            "--max-preview-chars",
            str(effective_preview_chars),
            "--max-xml-part-bytes",
            str(OFFICE_MAX_XML_PART_BYTES),
        ]
        if worker_output:
            command.extend(["--output", worker_output])
        if include_preview:
            command.append("--include-preview")
        if include_notes:
            command.append("--include-notes")
        result = self._run_worker(operation, host_output, command, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS, allow_empty_output=True)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            extra.setdefault("format", normalized_format)
            if host_output is not None:
                extra.setdefault("output_file_size", result.file_size)
                extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def _extract_office_data(
        self,
        operation: str,
        input_path: str | Path,
        suffix: str,
        output_path: str | Path | None,
        *,
        sheets: Sequence[str | int] | None,
        ranges: Mapping[str, str] | Sequence[str] | None,
        max_rows: int | None,
        max_cells: int | None,
        include_preview: bool,
        max_preview_chars: int | None,
        overwrite: bool,
    ) -> DocumentWorkerResult:
        effective_max_rows = self._bounded_positive_int(
            "max_rows",
            max_rows,
            default=OFFICE_MAX_XLSX_ROWS,
            upper_bound=OFFICE_MAX_XLSX_ROWS,
            operation=operation,
            requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_rows, DocumentWorkerResult):
            return effective_max_rows
        effective_max_cells = self._bounded_positive_int(
            "max_cells",
            max_cells,
            default=OFFICE_MAX_XLSX_CELLS,
            upper_bound=OFFICE_MAX_XLSX_CELLS,
            operation=operation,
            requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
        )
        if isinstance(effective_max_cells, DocumentWorkerResult):
            return effective_max_cells
        effective_preview_chars = self._bounded_positive_int(
            "max_preview_chars",
            max_preview_chars,
            default=OFFICE_MAX_PREVIEW_CHARS,
            upper_bound=OFFICE_MAX_PREVIEW_CHARS,
            operation=operation,
            requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS,
        )
        if isinstance(effective_preview_chars, DocumentWorkerResult):
            return effective_preview_chars
        input_check = self._resolve_input_path(input_path, suffix, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
        if isinstance(input_check, DocumentWorkerResult):
            return input_check
        host_input, worker_input, file_size = input_check
        host_output: Path | None = None
        worker_output = ""
        if output_path:
            output_check = self._resolve_output_path(output_path, ".json", overwrite=overwrite, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS)
            if isinstance(output_check, DocumentWorkerResult):
                return output_check
            host_output, worker_output = output_check
        command = [
            WORKER_COMMANDS[operation],
            "--input",
            worker_input,
            "--sheets-json",
            json.dumps(list(sheets or [])),
            "--ranges-json",
            json.dumps(ranges or {}),
            "--max-input-bytes",
            str(OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE),
            "--max-rows",
            str(effective_max_rows),
            "--max-cells",
            str(effective_max_cells),
            "--max-preview-chars",
            str(effective_preview_chars),
            "--max-xml-part-bytes",
            str(OFFICE_MAX_XML_PART_BYTES),
        ]
        if worker_output:
            command.extend(["--output", worker_output])
        if include_preview:
            command.append("--include-preview")
        result = self._run_worker(operation, host_output, command, requirement_ids=OFFICE_WORKER_REQUIREMENT_IDS, allow_empty_output=True)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("input_path", str(host_input))
            extra.setdefault("file_size", file_size)
            extra.setdefault("format", "json")
            if host_output is not None:
                extra.setdefault("output_file_size", result.file_size)
                extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            return self._with_extra(result, extra)
        return result

    def _create(
        self,
        operation: str,
        output_path: str | Path,
        *,
        title: str,
        body: str,
        content: Mapping[str, Any] | None,
        input_path: str | Path | None = None,
        overwrite: bool,
    ) -> DocumentWorkerResult:
        if operation not in SUPPORTED_CREATE_OPERATIONS:
            return self._failure(operation=operation, category="unsupported_operation", error="Unsupported document worker operation.")
        creation_profiles = {
            "create_docx": (DOCX_V2_REQUIREMENT_IDS, DOCX_V2_MAX_JSON_INPUT_BYTES, DOCX_V2_MAX_OUTPUT_BYTES, "DOCX"),
            "create_xlsx": (XLSX_V2_REQUIREMENT_IDS, XLSX_V2_MAX_JSON_INPUT_BYTES, XLSX_V2_MAX_OUTPUT_BYTES, "XLSX"),
            "create_pptx": (PPTX_V2_REQUIREMENT_IDS, PPTX_V2_MAX_JSON_INPUT_BYTES, PPTX_V2_MAX_OUTPUT_BYTES, "PPTX"),
            "create_pdf": (PDF_V2_REQUIREMENT_IDS, PDF_V2_MAX_JSON_INPUT_BYTES, PDF_V2_MAX_OUTPUT_BYTES, "PDF"),
        }
        requirement_ids, json_limit, output_limit, label = creation_profiles.get(
            operation,
            (DOCUMENT_WORKER_REQUIREMENT_IDS, DOCX_V2_MAX_JSON_INPUT_BYTES, DOCX_V2_MAX_OUTPUT_BYTES, operation.upper()),
        )
        host_input: Path | None = None
        worker_input = ""
        input_file_size: int | None = None
        if input_path:
            if operation not in {"create_docx", "create_xlsx", "create_pptx", "create_pdf"}:
                return self._failure(
                    operation=operation,
                    category="validation_error",
                    error="Only create_docx, create_xlsx, create_pptx and create_pdf support JSON input_path in this slice.",
                    requirement_ids=requirement_ids,
                )
            input_check = self._resolve_input_path(input_path, ".json", requirement_ids=requirement_ids)
            if isinstance(input_check, DocumentWorkerResult):
                return input_check
            host_input, worker_input, input_file_size = input_check
            if input_file_size > json_limit:
                return self._failure(
                    operation=operation,
                    category="limit_exceeded",
                    error=f"{label} JSON input exceeds limit of {json_limit} bytes.",
                    requirement_ids=requirement_ids,
                )

        path_check = self._resolve_output_path(output_path, SUPPORTED_CREATE_OPERATIONS[operation], overwrite=overwrite, requirement_ids=requirement_ids)
        if isinstance(path_check, DocumentWorkerResult):
            return path_check

        host_output, worker_output = path_check
        command = [
            WORKER_COMMANDS[operation],
            "--output",
            worker_output,
            "--title",
            title,
            "--body",
            body,
            "--content-json",
            json.dumps(dict(content or {}), sort_keys=True),
        ]
        if worker_input:
            command.extend(
                [
                    "--input-json",
                    worker_input,
                    "--max-json-input-bytes",
                    str(json_limit),
                ]
            )
        result = self._run_worker(operation, host_output, command, requirement_ids=requirement_ids)
        if result.ok:
            extra = dict(result.extra or {})
            extra.setdefault("output_file_size", result.file_size)
            extra.setdefault("changed_files", [self._host_path_to_relative(host_output)])
            if host_input is not None:
                extra.setdefault("input_path", self._host_path_to_relative(host_input))
                extra.setdefault("input_file_size", input_file_size)
            if result.file_size is not None and result.file_size > output_limit:
                return self._failure(
                    operation=operation,
                    category="limit_exceeded",
                    error=f"{label} output exceeds limit of {output_limit} bytes.",
                    requirement_ids=requirement_ids,
                )
            return self._with_extra(result, extra)
        return result

    def _resolve_output_path(
        self,
        raw_path: str | Path,
        expected_suffix: str,
        *,
        overwrite: bool,
        requirement_ids: tuple[str, ...] = DOCUMENT_WORKER_REQUIREMENT_IDS,
    ) -> tuple[Path, str] | DocumentWorkerResult:
        raw = Path(raw_path)
        if raw.is_absolute():
            return self._failure(
                operation="path_validation",
                category="absolute_path_rejected",
                error="Document worker output paths must be workspace-relative.",
                requirement_ids=requirement_ids,
            )

        if raw.suffix.lower() != expected_suffix:
            return self._failure(
                operation="path_validation",
                category="unsupported_extension",
                error=f"Output path must use the {expected_suffix} extension.",
                requirement_ids=requirement_ids,
            )

        if any(part in {"..", ""} for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="path_traversal_rejected",
                error="Document worker output paths must not contain parent traversal.",
                requirement_ids=requirement_ids,
            )

        if any(part.casefold() in PROTECTED_OUTPUT_SEGMENTS for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="protected_path_rejected",
                error="Document worker outputs must not target profile or governance paths.",
                requirement_ids=requirement_ids,
            )

        decision = guard_path(
            raw,
            self.workspace_roots,
            base_dir=self.workspace_root,
            operation="write",
        )
        if not decision.allowed or decision.absolute_path is None:
            return self._failure(
                operation="path_validation",
                category=decision.reason,
                error=decision.reason,
                requirement_ids=requirement_ids,
            )

        host_path = Path(decision.absolute_path)
        if host_path.exists() and not overwrite:
            return self._failure(
                operation="path_validation",
                category="output_exists",
                error="Document worker output already exists and overwrite is false.",
                requirement_ids=requirement_ids,
            )
        try:
            relative = host_path.relative_to(self.workspace_root)
        except ValueError:
            return self._failure(
                operation="path_validation",
                category="workspace_boundary_rejected",
                error="Document worker output must stay inside the selected workspace root.",
                requirement_ids=requirement_ids,
            )

        worker_path = f"{WORKER_CONTAINER_WORKDIR}/{relative.as_posix()}"
        return host_path, worker_path

    def _resolve_input_path(
        self,
        raw_path: str | Path,
        expected_suffix: str,
        *,
        requirement_ids: tuple[str, ...] = PDF_WORKER_REQUIREMENT_IDS,
    ) -> tuple[Path, str, int] | DocumentWorkerResult:
        raw = Path(raw_path)
        if raw.is_absolute():
            return self._failure(
                operation="path_validation",
                category="absolute_path_rejected",
                error="Document worker input paths must be workspace-relative.",
                requirement_ids=requirement_ids,
            )
        if raw.suffix.lower() != expected_suffix:
            return self._failure(
                operation="path_validation",
                category="unsupported_extension",
                error=f"Input path must use the {expected_suffix} extension.",
                requirement_ids=requirement_ids,
            )
        if any(part in {"..", ""} for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="path_traversal_rejected",
                error="Document worker input paths must not contain parent traversal.",
                requirement_ids=requirement_ids,
            )
        if any(part.casefold() in PROTECTED_OUTPUT_SEGMENTS for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="protected_path_rejected",
                error="Document worker inputs must not target profile or governance paths.",
                requirement_ids=requirement_ids,
            )
        decision = guard_path(
            raw,
            self.workspace_roots,
            base_dir=self.workspace_root,
            operation="read",
        )
        if not decision.allowed or decision.absolute_path is None:
            return self._failure(
                operation="path_validation",
                category=decision.reason,
                error=decision.reason,
                requirement_ids=requirement_ids,
            )
        host_path = Path(decision.absolute_path)
        if not host_path.is_file():
            return self._failure(
                operation="path_validation",
                category="not_found",
                error="Document worker input file does not exist.",
                requirement_ids=requirement_ids,
            )
        file_size = host_path.stat().st_size
        if expected_suffix == ".zip":
            max_size = ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE
        elif expected_suffix == ".pdf":
            max_size = PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE
        else:
            max_size = OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE
        if file_size > max_size:
            return self._failure(
                operation="path_validation",
                category="limit_exceeded",
                error=f"Document worker input file exceeds structural safety limit of {max_size} bytes.",
                requirement_ids=requirement_ids,
            )
        try:
            relative = host_path.relative_to(self.workspace_root)
        except ValueError:
            return self._failure(
                operation="path_validation",
                category="workspace_boundary_rejected",
                error="Document worker input must stay inside the selected workspace root.",
                requirement_ids=requirement_ids,
            )
        worker_path = f"{WORKER_CONTAINER_WORKDIR}/{relative.as_posix()}"
        return host_path, worker_path, file_size

    def _resolve_image_input_path(
        self,
        raw_path: str | Path,
    ) -> tuple[Path, str, int] | DocumentWorkerResult:
        if isinstance(raw_path, str) and _looks_like_external_url(raw_path):
            return self._failure(
                operation="read_image",
                category="validation_error",
                error="external_url_forbidden",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        raw = Path(raw_path)
        detected_extension = raw.suffix.casefold()
        if raw.is_absolute():
            return self._failure(
                operation="read_image",
                category="absolute_path_rejected",
                error="read_image input_path must be workspace-relative.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        if any(part in {"..", ""} for part in raw.parts):
            return self._failure(
                operation="read_image",
                category="path_traversal_denied",
                error="path_traversal_denied",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        if any(part.casefold() in PROTECTED_OUTPUT_SEGMENTS for part in raw.parts):
            return self._failure(
                operation="read_image",
                category="protected_path_rejected",
                error="read_image inputs must not target profile or governance paths.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        if detected_extension not in READ_IMAGE_SUPPORTED_INPUT_SUFFIXES:
            return self._failure(
                operation="read_image",
                category="validation_error",
                error="unsupported_format",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
                extra={
                    "detected_extension": detected_extension,
                    "supported_formats": list(READ_IMAGE_SUPPORTED_INPUT_FORMATS),
                },
            )
        decision = guard_path(
            raw,
            self.workspace_roots,
            base_dir=self.workspace_root,
            operation="read",
        )
        if not decision.allowed or decision.absolute_path is None:
            return self._failure(
                operation="read_image",
                category=decision.reason,
                error=decision.reason,
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        host_path = Path(decision.absolute_path)
        if not host_path.is_file():
            return self._failure(
                operation="read_image",
                category="not_found",
                error="read_image input file does not exist.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        try:
            relative = host_path.relative_to(self.workspace_root)
        except ValueError:
            return self._failure(
                operation="read_image",
                category="workspace_boundary_rejected",
                error="read_image input must stay inside the selected workspace root.",
                requirement_ids=IMAGE_READ_REQUIREMENT_IDS,
            )
        worker_path = f"{WORKER_CONTAINER_WORKDIR}/{relative.as_posix()}"
        return host_path, worker_path, host_path.stat().st_size

    def _resolve_input_paths(
        self,
        raw_paths: Sequence[str | Path],
    ) -> tuple[list[Path], list[str], int] | DocumentWorkerResult:
        host_paths: list[Path] = []
        worker_paths: list[str] = []
        total_size = 0
        for raw_path in raw_paths:
            resolved = self._resolve_input_path(raw_path, ".pdf")
            if isinstance(resolved, DocumentWorkerResult):
                return resolved
            host_path, worker_path, file_size = resolved
            host_paths.append(host_path)
            worker_paths.append(worker_path)
            total_size += file_size
        return host_paths, worker_paths, total_size

    def _resolve_zip_source_paths(
        self,
        raw_paths: Sequence[str | Path],
    ) -> tuple[list[Path], list[str]] | DocumentWorkerResult:
        host_paths: list[Path] = []
        worker_paths: list[str] = []
        seen: set[Path] = set()
        for raw_path in raw_paths:
            raw = Path(raw_path)
            if raw.is_absolute():
                return self._failure(
                    operation="path_validation",
                    category="absolute_path_rejected",
                    error="ZIP source paths must be workspace-relative.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            if any(part in {"..", ""} for part in raw.parts):
                return self._failure(
                    operation="path_validation",
                    category="path_traversal_rejected",
                    error="ZIP source paths must not contain parent traversal.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            if any(part.casefold() in PROTECTED_OUTPUT_SEGMENTS for part in raw.parts):
                return self._failure(
                    operation="path_validation",
                    category="protected_path_rejected",
                    error="ZIP source paths must not target profile or governance paths.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            decision = guard_path(
                raw,
                self.workspace_roots,
                base_dir=self.workspace_root,
                operation="read",
            )
            if not decision.allowed or decision.absolute_path is None:
                return self._failure(
                    operation="path_validation",
                    category=decision.reason,
                    error=decision.reason,
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            host_path = Path(decision.absolute_path)
            if not host_path.exists():
                return self._failure(
                    operation="path_validation",
                    category="not_found",
                    error="ZIP source path does not exist.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            if host_path.is_symlink():
                return self._failure(
                    operation="path_validation",
                    category="symlink_not_supported",
                    error="ZIP creation does not support symlink sources in the MVP.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            try:
                relative = host_path.relative_to(self.workspace_root)
            except ValueError:
                return self._failure(
                    operation="path_validation",
                    category="workspace_boundary_rejected",
                    error="ZIP source path must stay inside the selected workspace root.",
                    requirement_ids=ZIP_WORKER_REQUIREMENT_IDS,
                )
            if host_path not in seen:
                seen.add(host_path)
                host_paths.append(host_path)
                worker_paths.append(f"{WORKER_CONTAINER_WORKDIR}/{relative.as_posix()}")
        return host_paths, worker_paths

    def _resolve_output_dir(
        self,
        raw_path: str | Path,
        *,
        requirement_ids: tuple[str, ...] = PDF_WORKER_REQUIREMENT_IDS,
    ) -> tuple[Path, str] | DocumentWorkerResult:
        raw = Path(raw_path)
        if raw.is_absolute():
            return self._failure(
                operation="path_validation",
                category="absolute_path_rejected",
                error="Document worker output directories must be workspace-relative.",
                requirement_ids=requirement_ids,
            )
        if any(part in {"..", ""} for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="path_traversal_rejected",
                error="Document worker output directories must not contain parent traversal.",
                requirement_ids=requirement_ids,
            )
        if any(part.casefold() in PROTECTED_OUTPUT_SEGMENTS for part in raw.parts):
            return self._failure(
                operation="path_validation",
                category="protected_path_rejected",
                error="Document worker outputs must not target profile or governance paths.",
                requirement_ids=requirement_ids,
            )
        decision = guard_path(
            raw,
            self.workspace_roots,
            base_dir=self.workspace_root,
            operation="write",
        )
        if not decision.allowed or decision.absolute_path is None:
            return self._failure(
                operation="path_validation",
                category=decision.reason,
                error=decision.reason,
                requirement_ids=requirement_ids,
            )
        host_path = Path(decision.absolute_path)
        try:
            relative = host_path.relative_to(self.workspace_root)
        except ValueError:
            return self._failure(
                operation="path_validation",
                category="workspace_boundary_rejected",
                error="Document worker output directory must stay inside the selected workspace root.",
                requirement_ids=requirement_ids,
            )
        worker_path = f"{WORKER_CONTAINER_WORKDIR}/{relative.as_posix()}"
        return host_path, worker_path

    def _normalize_pages(
        self,
        pages: Sequence[int | str],
        *,
        require_non_empty: bool,
    ) -> list[int | str] | DocumentWorkerResult:
        if require_non_empty and not pages:
            return self._invalid_page()
        normalized: list[int | str] = []
        for page in pages:
            if isinstance(page, bool):
                return self._invalid_page()
            if isinstance(page, int):
                if page < 1:
                    return self._invalid_page()
                normalized.append(page)
                continue
            if isinstance(page, str):
                stripped = page.strip()
                if not stripped:
                    return self._invalid_page()
                if "-" in stripped:
                    start_text, end_text = stripped.split("-", 1)
                    if not start_text.isdigit() or not end_text.isdigit():
                        return self._invalid_page()
                    start = int(start_text)
                    end = int(end_text)
                    if start < 1 or end < start:
                        return self._invalid_page()
                    normalized.append(f"{start}-{end}")
                    continue
                if stripped.isdigit() and int(stripped) >= 1:
                    normalized.append(int(stripped))
                    continue
            return self._invalid_page()
        return normalized

    def _invalid_page(self) -> DocumentWorkerResult:
        return self._failure(
            operation="page_validation",
            category="validation_error",
            error="PDF pages are 1-based and must be positive numbers or ascending ranges.",
            requirement_ids=PDF_WORKER_REQUIREMENT_IDS,
        )

    @staticmethod
    def _page_selector_count(pages: Sequence[int | str]) -> int:
        count = 0
        for page in pages:
            if isinstance(page, int):
                count += 1
                continue
            if isinstance(page, str) and "-" in page:
                start_text, end_text = page.split("-", 1)
                count += int(end_text) - int(start_text) + 1
                continue
            count += 1
        return count

    def _bounded_positive_int(
        self,
        field_name: str,
        value: int | None,
        *,
        default: int,
        upper_bound: int,
        operation: str,
        requirement_ids: tuple[str, ...],
    ) -> int | DocumentWorkerResult:
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            return self._failure(
                operation=operation,
                category="validation_error",
                error=f"{field_name} must be a positive integer.",
                requirement_ids=requirement_ids,
            )
        if value < 1:
            return self._failure(
                operation=operation,
                category="validation_error",
                error=f"{field_name} must be a positive integer.",
                requirement_ids=requirement_ids,
            )
        if value > upper_bound:
            return self._failure(
                operation=operation,
                category="limit_exceeded",
                error=f"{field_name} must not exceed {upper_bound}.",
                requirement_ids=requirement_ids,
            )
        return value

    @staticmethod
    def _worker_path_to_relative(path_value: str) -> str:
        prefix = f"{WORKER_CONTAINER_WORKDIR}/"
        return path_value.removeprefix(prefix)

    def _host_path_to_relative(self, path_value: Path) -> str:
        try:
            return path_value.relative_to(self.workspace_root).as_posix()
        except ValueError:
            return str(path_value)

    def _run_worker(
        self,
        operation: str,
        host_output: Path | None,
        worker_command: Sequence[str],
        *,
        requirement_ids: tuple[str, ...] = DOCUMENT_WORKER_REQUIREMENT_IDS,
        allow_empty_output: bool = False,
    ) -> DocumentWorkerResult:
        inspect = self._inspect_image()
        if inspect.returncode != 0:
            return self._failure(
                operation=operation,
                category=_worker_status_category(inspect.stderr or inspect.stdout),
                error=self._combined_error(inspect) or "Document worker image is not available locally.",
                exit_code=inspect.returncode,
                stdout=inspect.stdout or "",
                stderr=inspect.stderr or "",
                requirement_ids=requirement_ids,
            )

        args = self._docker_args(worker_command)
        completed = self.runner(
            args,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        worker_payload = self._parse_worker_stdout(stdout)
        if completed.returncode != 0:
            category = str(worker_payload.get("error_category") or "")
            if not category:
                category = "engine_missing" if "ModuleNotFoundError" in stderr or "ImportError" in stderr else "worker_error"
            worker_error = str(worker_payload.get("error") or "").strip()
            extra = {
                key: value
                for key, value in worker_payload.items()
                if key not in {"ok", "operation", "error", "error_category", "message"}
            }
            return self._failure(
                operation=operation,
                category=category,
                error=self._combined_error(completed) or worker_error or "Document worker execution failed.",
                exit_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                docker_args=tuple(args),
                requirement_ids=requirement_ids,
                extra=extra,
            )

        file_size = None
        output_path = None
        if host_output is not None:
            if not host_output.exists():
                return self._failure(
                    operation=operation,
                    category="output_missing",
                    error="Document worker completed but did not create the requested output file.",
                    exit_code=completed.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    docker_args=tuple(args),
                    requirement_ids=requirement_ids,
                )
            file_size = host_output.stat().st_size
            if file_size <= 0 and not allow_empty_output:
                return self._failure(
                    operation=operation,
                    category="empty_output",
                    error="Document worker created an empty output file.",
                    exit_code=completed.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    docker_args=tuple(args),
                    requirement_ids=requirement_ids,
                )
            output_path = str(host_output)

        status = "created" if host_output is not None else ("available" if operation == "probe_dependencies" else "completed")
        extra = {
            key: value
            for key, value in worker_payload.items()
            if key not in {"ok", "operation", "output_path", "file_size", "error", "message"}
        }
        return DocumentWorkerResult(
            ok=True,
            operation=operation,
            status=status,
            worker_image=self.worker_image,
            policy_decision="allow",
            output_path=output_path,
            file_size=file_size,
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            docker_args=tuple(args),
            requirement_ids=requirement_ids,
            extra=extra,
        )

    def _docker_args(self, worker_command: Sequence[str]) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            WORKER_TMPFS_SPEC,
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            WORKER_CONTAINER_USER,
            "--memory",
            self.memory,
            "--cpus",
            self.cpus,
            "--pids-limit",
            str(self.pids_limit),
            "--workdir",
            WORKER_CONTAINER_WORKDIR,
            "--mount",
            f"type=bind,source={self.workspace_root},target={WORKER_CONTAINER_WORKDIR},readonly=false",
            self.worker_image,
            *worker_command,
        ]

    def _inspect_image(self) -> subprocess.CompletedProcess[str]:
        args = ["docker", "image", "inspect", self.worker_image]
        try:
            return self.runner(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return subprocess.CompletedProcess(
                args,
                127,
                stdout="",
                stderr=f"Docker not detected. Document-worker operations may be unavailable until Docker is installed/running. Detail: {exc}",
            )

    def _failure(
        self,
        *,
        operation: str,
        category: str,
        error: str,
        exit_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
        docker_args: tuple[str, ...] = (),
        requirement_ids: tuple[str, ...] = DOCUMENT_WORKER_REQUIREMENT_IDS,
        extra: Mapping[str, Any] | None = None,
    ) -> DocumentWorkerResult:
        return DocumentWorkerResult(
            ok=False,
            operation=operation,
            status="failed",
            worker_image=self.worker_image,
            policy_decision="deny",
            error_category=category,
            error=error,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            docker_args=docker_args,
            requirement_ids=requirement_ids,
            extra=extra,
        )

    @staticmethod
    def _combined_error(completed: subprocess.CompletedProcess[str]) -> str:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        if stderr:
            return stderr
        if stdout:
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                return stdout
            if isinstance(parsed, dict):
                return str(parsed.get("error") or parsed.get("message") or stdout)
            return stdout
        return ""

    @staticmethod
    def _parse_worker_stdout(stdout: str) -> dict[str, Any]:
        text = (stdout or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text.splitlines()[-1])
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _with_extra(result: DocumentWorkerResult, extra: Mapping[str, Any]) -> DocumentWorkerResult:
        return DocumentWorkerResult(
            ok=result.ok,
            operation=result.operation,
            status=result.status,
            worker_image=result.worker_image,
            policy_decision=result.policy_decision,
            output_path=result.output_path,
            file_size=result.file_size,
            error_category=result.error_category,
            error=result.error,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            docker_args=result.docker_args,
            requirement_ids=result.requirement_ids,
            extra=extra,
        )


def _worker_status_category(output: str) -> str:
    text = output.casefold()
    if "docker not detected" in text or "no such file" in text or "not recognized" in text:
        return "docker_missing"
    daemon_markers = (
        "cannot connect to the docker daemon",
        "is the docker daemon running",
        "docker daemon",
        "pipe/docker_engine",
        "error during connect",
    )
    if any(marker in text for marker in daemon_markers):
        return "docker_daemon_not_running"
    if "no such image" in text or "pull access denied" in text or "image not found" in text:
        return "worker_missing"
    return "worker_missing"


def _looks_like_external_url(value: str) -> bool:
    text = value.strip().casefold()
    return "://" in text or text.startswith(("data:", "file:"))


def _valid_resize_to(value: str) -> bool:
    text = value.strip().casefold()
    if not text:
        return True
    if text.endswith("%") and text[:-1].isdigit():
        percent = int(text[:-1])
        return 1 <= percent <= 100
    if "x" not in text:
        return False
    width_text, height_text = text.split("x", 1)
    if not width_text.isdigit() or not height_text.isdigit():
        return False
    width = int(width_text)
    height = int(height_text)
    return 1 <= width <= 8192 and 1 <= height <= 8192
