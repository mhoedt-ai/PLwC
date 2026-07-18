"""Public MCP entry point for PLwC Gateway."""

from __future__ import annotations

import anyio
import concurrent.futures
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from plwc_gateway import __version__
from plwc_gateway.adapters import DockerSandboxAdapter, PBAProfileAdapter, SafeFilesystemAdapter
from plwc_gateway.adapters import pba
from plwc_gateway.adapters import qdrant_index
from plwc_gateway.adapters.document_worker import (
    DOCX_V2_MAX_CONTENT_ELEMENTS,
    DOCX_V2_MAX_IMAGE_BYTES,
    DOCX_V2_MAX_IMAGES,
    DOCX_V2_MAX_JSON_INPUT_BYTES,
    DOCX_V2_MAX_OUTPUT_BYTES,
    DOCX_V2_MAX_PARAGRAPHS,
    DOCX_V2_MAX_TABLE_CELLS,
    DOCX_V2_MAX_TABLES,
    DOCX_V2_REQUIREMENT_IDS,
    DOCUMENT_WORKER_IMAGE,
    OFFICE_MAX_ODF_CELLS,
    OFFICE_MAX_ODF_ROWS,
    OFFICE_MAX_ODF_TABLES,
    OFFICE_MAX_PREVIEW_CHARS,
    OFFICE_MAX_PPTX_SLIDES,
    OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE,
    OFFICE_MAX_TEXT_CHARS,
    OFFICE_MAX_XML_PART_BYTES,
    OFFICE_MAX_XLSX_CELLS,
    OFFICE_MAX_XLSX_ROWS,
    PDF_MAX_EXTRACT_OUTPUT_PAGES,
    PDF_MAX_INPUT_FILES,
    PDF_MAX_MERGE_OUTPUT_PAGES,
    PDF_MAX_ROTATE_ALL_PAGES,
    PDF_MAX_ROTATE_SELECTED_PAGES,
    PDF_MAX_SPLIT_OUTPUT_FILES,
    PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE,
    PDF_TEXT_MAX_PAGES,
    PDF_TEXT_MAX_CHARS,
    PDF_TEXT_MAX_PREVIEW_CHARS,
    READ_IMAGE_DEFAULT_MAX_SIZE_KB,
    READ_IMAGE_HARD_MAX_SIZE_KB,
    READ_IMAGE_OUTPUT_FORMATS,
    READ_IMAGE_SUPPORTED_INPUT_FORMATS,
    READ_IMAGE_SUPPORTED_INPUT_SUFFIXES,
    ZIP_MAX_COMPRESSION_RATIO,
    ZIP_MAX_ENTRIES,
    ZIP_MAX_EXTRACTED_BYTES,
    ZIP_MAX_NESTED_DEPTH,
    ZIP_MAX_PATH_LENGTH,
    ZIP_MAX_SINGLE_FILE_BYTES,
    ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE,
    WORKER_CONTAINER_WORKDIR,
    DocumentWorkerAdapter,
    XLSX_V2_MAX_CELLS_PER_SHEET,
    XLSX_V2_MAX_COLUMNS_PER_SHEET,
    XLSX_V2_MAX_JSON_INPUT_BYTES,
    XLSX_V2_MAX_MERGED_RANGES,
    XLSX_V2_MAX_OUTPUT_BYTES,
    XLSX_V2_MAX_ROWS_PER_SHEET,
    XLSX_V2_MAX_SHEETS,
    XLSX_V2_MAX_TOTAL_CELLS,
    XLSX_V2_REQUIREMENT_IDS,
    PPTX_V2_MAX_BULLET_ITEMS_PER_SLIDE,
    PPTX_V2_MAX_CONTENT_ELEMENTS_PER_SLIDE,
    PPTX_V2_MAX_IMAGE_BYTES,
    PPTX_V2_MAX_IMAGES,
    PPTX_V2_MAX_JSON_INPUT_BYTES,
    PPTX_V2_MAX_OUTPUT_BYTES,
    PPTX_V2_MAX_SLIDES,
    PPTX_V2_MAX_TABLE_CELLS_PER_SLIDE,
    PPTX_V2_MAX_TABLES_PER_SLIDE,
    PPTX_V2_REQUIREMENT_IDS,
    PDF_V2_MAX_CONTENT_ELEMENTS,
    PDF_V2_MAX_IMAGE_BYTES,
    PDF_V2_MAX_IMAGES,
    PDF_V2_MAX_JSON_INPUT_BYTES,
    PDF_V2_MAX_OUTPUT_BYTES,
    PDF_V2_MAX_PARAGRAPHS,
    PDF_V2_MAX_TABLE_CELLS,
    PDF_V2_MAX_TABLES,
    PDF_V2_REQUIREMENT_IDS,
)
from plwc_gateway.adapters.pba import (
    CONFIDENCE_TO_PBA2_TRUST,
    GOVERNOR_LIFECYCLE_STATES,
    NO_ACTION_RULE_REVIEW_QUESTION,
    PBA2_REFLECTION_MARKERS,
    PBA2_REFLECTION_TRUST_LEVELS,
    REFLECTION_MARKER_RECOMMENDED_VALUES,
    REFLECTION_MARKER_SYNONYMS,
    REFLECTION_TRUST_RECOMMENDED_VALUES,
    PROFILE_CREATION_PLAN_TYPE,
    PROFILE_CREATION_PLAN_TYPES,
    REFLECTION_CONDENSATION_PLAN_TYPE,
    REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
    RETIREMENT_TARGET_FILES,
    profile_onboarding_schema,
    scan_tagebuch_patterns,
)
from plwc_gateway.audit import AuditError, AuditLogger, JsonlAuditLogger
from plwc_gateway.config import (
    ConfigValidationError,
    GatewayConfig,
    PERSONA_LAYER_DISABLED_ENV_VAR,
    PERSONA_LAYER_ENABLED_ENV_VAR,
    load_gateway_config,
)
from plwc_gateway.onboarding import build_first_run_status, generate_claude_config
from plwc_gateway.policy import IntentAction, PolicyIntent, execute_with_policy, is_protected_governance_path
from plwc_gateway.policy.decisions import PolicyDecision

from .server_constants import FORBIDDEN_PUBLIC_SERVER_NAMES, PUBLIC_SERVER_NAME

PUBLIC_STATUS_TOOL = "plwc_status"
PROFILE_TOOL = "plwc_profile"
REFLECTION_TOOL = "plwc_reflection"
GOVERNOR_TOOL = "plwc_governor"
SANDBOX_RUN_TOOL = "plwc_sandbox_run"
WORKSPACE_OPERATION_TOOL = "plwc_workspace_operation"
DOCUMENT_OPERATION_TOOL = "plwc_document_operation"
DESCRIBE_TOOL = "plwc_describe"
SUPPORTED_STATUS_SCOPES = frozenset({"runtime", "sandbox", "first_run", "config"})
SUPPORTED_PROFILE_OPERATIONS = frozenset({"status", "snapshot", "compile", "retrieve", "scan_tagebuch", "doctor"})
SUPPORTED_COMPILE_MODES = frozenset({"boot", "working", "full"})
DEFAULT_PROFILE_COMPILE_MODE = "boot"
DEFAULT_BOOT_COMPILE_MAX_CHARS = 6000
DEFAULT_WORKING_COMPILE_MAX_CHARS = 12000
MIN_COMPACT_COMPILE_MAX_CHARS = 2000
MAX_COMPACT_COMPILE_MAX_CHARS = 50000
BOOT_PROFILE_ENTRY_LIMITS = {
    "TEMPERAMENT.md": 5,
    "PERSONA.md": 5,
    "memory.md": 3,
}
WORKING_PROFILE_ENTRY_LIMITS = {
    "TEMPERAMENT.md": 8,
    "PERSONA.md": 8,
    "memory.md": 14,
}
BOOT_PROFILE_ENTRY_MAX_CHARS = 220
WORKING_PROFILE_ENTRY_MAX_CHARS = 360
DEFAULT_QDRANT_RETRIEVE_TIMEOUT_SECONDS = 5.0
DEFAULT_QDRANT_REINDEX_TIMEOUT_SECONDS = 30.0
RC13_QDRANT_REQUIREMENT_ID = "RC13-QDRANT-001"
RC14_QDRANT_REQUIREMENT_ID = "RC14-QDRANT-001"
RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID = "RC14-QDRANT-002"
RC15_QDRANT_STALENESS_REQUIREMENT_ID = "RC15-QDRANT-001"
RC15_QDRANT_SMOKE_REQUIREMENT_ID = "RC15-QDRANT-002"
RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID = "RC16-QDRANT-001"
RC16_WORKSPACE_PARAMETER_REQUIREMENT_ID = "RC16-WORKSPACE-001"
RC17_CLU_DOCTOR_REQUIREMENT_ID = "RC17-CLU-001"
RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID = "RC18-CLU-001"
RC17_TAGEBUCH_CANONICAL_REQUIREMENT_ID = "RC17-INNER-002"
CLU_SOURCE_PACK_SHA256 = "E653A2DF0C07D915ED46DE7A0E277C9E8CBE36D111614A4DE1F69B6A0F6FED1C"
CLU_SOURCE_PACK_VERSION = "0.1.0"
WORKING_SEMANTIC_MEMORY_HIT_LIMIT = 3
WORKING_SEMANTIC_MEMORY_ENTRY_MAX_CHARS = 420
SUPPORTED_REFLECTION_OPERATIONS = frozenset({"write"})
SUPPORTED_GOVERNOR_OPERATIONS = frozenset({"plan", "apply", "retire", "list_retirable", "reindex", "drop_index"})
SUPPORTED_DOCTOR_MODES = frozenset({"clu"})
SUPPORTED_DOCTOR_SCOPES = frozenset({"general", "profile", "memory", "smoke", "workspace", "release"})
DOCTOR_RUNNER_SCOPES = frozenset({"general", "profile", "smoke"})
SUPPORTED_SANDBOX_LANGS = frozenset({"python", "shell", "node"})
SUPPORTED_WORKSPACE_OPERATIONS = frozenset(
    {
        "list",
        "search",
        "read",
        "write",
        "file_info",
        "create_dir",
        "move",
        "rename",
        "batch_read",
        "exact_replace",
        "copy",
        "read_binary",
        "write_binary",
    }
)
DELETE_LIKE_WORKSPACE_OPERATIONS = frozenset({"delete", "remove", "unlink", "rmdir", "rm", "del"})
WRITE_WORKSPACE_OPERATIONS = frozenset(
    {"write", "create_dir", "move", "rename", "exact_replace", "copy", "write_binary"}
)
BINARY_WORKSPACE_OPERATIONS = frozenset({"copy", "read_binary", "write_binary"})
WORKSPACE_OPERATION_REQUIREMENTS = ("FR-CMD-PUB-001", "FR-CMD-PUB-002", "FR-CMD-PUB-003")
FACADE_REQUIREMENTS = ("FR-FACADE-001", "FR-FACADE-002", "FR-FACADE-003", "NFR-002")
PROFILE_COMPILE_MODE_REQUIREMENTS = ("FR-PROFILE-COMPILE-MODES-001", "FR-003", "NFR-004")
V1_PERSONA_LAYER_REQUIREMENT_ID = "V1-PERSONA-002"
PERSONA_LAYER_CORE_OMIT_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?P<label>"
    r"role|rolle|assistant role|assistant identity|identity|identitaet|"
    r"persona|persona name|name|voice|stimme|working context|arbeitskontext"
    r")\s*:",
    re.IGNORECASE,
)
_QDRANT_RETRIEVE_LOCKS: dict[tuple[str, str], threading.Lock] = {}
_QDRANT_RETRIEVE_LOCKS_GUARD = threading.Lock()
_QDRANT_MAINTENANCE_LOCKS: dict[tuple[str, str], threading.Lock] = {}
_QDRANT_MAINTENANCE_LOCKS_GUARD = threading.Lock()
WORKSPACE_BATCH_MAX_FILES = 10
WORKSPACE_BATCH_MAX_BYTES_PER_FILE = 250_000
WORKSPACE_BATCH_MAX_TOTAL_BYTES = 1_000_000
TAGEBUCH_CANONICAL_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
TAGEBUCH_SUFFIX_FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})(?:[-_. ]+\d+|[-_ ]+(?:copy|kopie|duplicate|dupe)| \(\d+\))\.md$",
    re.IGNORECASE,
)
SUPPORTED_DOCUMENT_CREATE_OPERATIONS = frozenset({"create_docx", "create_xlsx", "create_pptx", "create_pdf"})
SUPPORTED_DOCUMENT_PDF_OPERATIONS = frozenset({"inspect_pdf", "merge_pdf", "split_pdf", "extract_pdf", "rotate_pdf", "extract_pdf_text"})
SUPPORTED_DOCUMENT_ZIP_OPERATIONS = frozenset({"inspect_zip", "extract_zip", "create_zip"})
SUPPORTED_DOCUMENT_IMAGE_OPERATIONS = frozenset({"read_image"})
SUPPORTED_DOCUMENT_OFFICE_OPERATIONS = frozenset(
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
SUPPORTED_DOCUMENT_EDIT_OPERATIONS = frozenset({"edit_docx"})
SUPPORTED_DOCUMENT_OPERATIONS = (
    SUPPORTED_DOCUMENT_CREATE_OPERATIONS
    | SUPPORTED_DOCUMENT_PDF_OPERATIONS
    | SUPPORTED_DOCUMENT_ZIP_OPERATIONS
    | SUPPORTED_DOCUMENT_IMAGE_OPERATIONS
    | SUPPORTED_DOCUMENT_OFFICE_OPERATIONS
    | SUPPORTED_DOCUMENT_EDIT_OPERATIONS
)
PROMOTION_PLAN_TYPES = frozenset({"memory_promotion", "persona_promotion", "temperament_promotion"})
DOCUMENT_OPERATION_EXTENSIONS = {
    "create_docx": ".docx",
    "create_xlsx": ".xlsx",
    "create_pptx": ".pptx",
    "create_pdf": ".pdf",
    "inspect_docx": ".docx",
    "extract_docx_text": ".docx",
    "inspect_xlsx": ".xlsx",
    "extract_xlsx_data": ".xlsx",
    "inspect_pptx": ".pptx",
    "extract_pptx_text": ".pptx",
    "inspect_odt": ".odt",
    "extract_odt_text": ".odt",
    "inspect_ods": ".ods",
    "extract_ods_data": ".ods",
    "inspect_odp": ".odp",
    "extract_odp_text": ".odp",
    "merge_pdf": ".pdf",
    "extract_pdf": ".pdf",
    "rotate_pdf": ".pdf",
    "create_zip": ".zip",
    "edit_docx": ".docx",
}
UNSUPPORTED_DOCUMENT_OPERATION_NAMES = frozenset(
    {
        "convert",
        "html_to_pdf",
        "docx_to_pdf",
        "md_to_pdf",
        "pdf_to_text",
        "pdf_to_images",
        "pdf_to_docx",
        "ocr",
        "compress_pdf",
        "encrypt_pdf",
        "decrypt_pdf",
        "sign_pdf",
        "redact_pdf",
        "watermark_pdf",
        "fill_pdf_form",
        "extract_pdf_embedded_files",
        "create_odt",
        "create_ods",
        "create_odp",
        "archive",
        "zip",
        "extract_archive",
        "extract_zip_file",
        "create_archive",
        "delete",
        "remove",
        "unlink",
        "rmdir",
        "rm",
        "del",
        "shell",
        "command",
    }
)
DOCUMENT_OPERATION_REQUIREMENTS = (
    "FR-DOC-PUB-001",
    "FR-DOC-PUB-002",
    "FR-DOC-PUB-003",
    "FR-DOC-PUB-005",
    "FR-DOC-PUB-007",
    "FR-DOC-PUB-008",
    "FR-DOC-PUB-009",
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
    "FR-PDF-MVP-013",
    "FR-PDF-MVP-014",
    "FR-PDF-TEXT-001",
    "FR-PDF-TEXT-002",
    "FR-PDF-TEXT-003",
    "FR-PDF-TEXT-004",
    "FR-PDF-TEXT-005",
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
DOCX_V2_SCHEMA_VERSION = "docx_v2_1"
DOCX_V2_SUPPORTED_SCHEMA_VERSIONS = frozenset({DOCX_V2_SCHEMA_VERSION})
EDIT_DOCX_SCHEMA_VERSION = "edit_docx_1"
EDIT_DOCX_SUPPORTED_SCHEMA_VERSIONS = frozenset({EDIT_DOCX_SCHEMA_VERSION})
EDIT_DOCX_TOP_LEVEL_FIELDS = frozenset({"schema_version", "edits"})
EDIT_DOCX_OP_TYPES = frozenset({"replace_text", "set_core_property", "append_paragraph", "set_footer_text", "set_header_text"})
EDIT_DOCX_CORE_PROPERTY_NAMES = frozenset({"title", "author", "subject", "keywords"})
EDIT_DOCX_MAX_OPS = 200
EDIT_DOCX_REPLACE_TEXT_FIELDS = frozenset({"type", "find", "replace", "max_replacements"})
EDIT_DOCX_SET_CORE_PROPERTY_FIELDS = frozenset({"type", "name", "value"})
EDIT_DOCX_APPEND_PARAGRAPH_FIELDS = frozenset({"type", "text", "style"})
EDIT_DOCX_SET_HEADER_FOOTER_FIELDS = frozenset({"type", "text", "page_number"})
EDIT_DOCX_REQUIREMENT_IDS = (
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
DOCX_V2_TOP_LEVEL_FIELDS = frozenset({"schema_version", "document", "page", "styles", "content"})
DOCX_V2_DOCUMENT_FIELDS = frozenset({"title", "author", "language"})
DOCX_V2_PAGE_FIELDS = frozenset({"size", "orientation", "margins_mm"})
DOCX_V2_MARGIN_FIELDS = frozenset({"top", "bottom", "left", "right"})
DOCX_V2_STYLE_NAMES = frozenset({"body", "title", "heading1", "heading2", "heading3", "quote", "blockquote"})
DOCX_V2_STYLE_FIELDS = frozenset(
    {
        "font",
        "size_pt",
        "bold",
        "italic",
        "alignment",
        "line_spacing",
        "space_before_pt",
        "space_after_pt",
        "first_line_indent_mm",
        "page_break_before",
    }
)
DOCX_V2_TEXT_TYPES = frozenset({"title", "heading1", "heading2", "heading3", "paragraph", "quote", "blockquote"})
DOCX_V2_TEXT_ELEMENT_FIELDS = frozenset({"type", "text", "runs", "style", "style_overrides"})
DOCX_V2_RUN_FIELDS = frozenset({"text", "bold", "italic", "underline"})
DOCX_V2_LIST_FIELDS = frozenset({"type", "items", "style_overrides"})
DOCX_V2_IMAGE_FIELDS = frozenset({"type", "path", "width_mm", "height_mm", "align"})
DOCX_V2_TABLE_FIELDS = frozenset({"type", "rows"})
DOCX_V2_CONTENT_TYPES = DOCX_V2_TEXT_TYPES | frozenset({"bullet_list", "numbered_list", "page_break", "image", "table"})
DOCX_V2_PAGE_SIZES = frozenset({"A4", "A5"})
DOCX_V2_ORIENTATIONS = frozenset({"portrait", "landscape"})
DOCX_V2_ALIGNMENTS = frozenset({"left", "center", "right", "justify"})
DOCX_V2_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
XLSX_V2_SCHEMA_VERSION = "xlsx_v2_1"
XLSX_V2_SUPPORTED_SCHEMA_VERSIONS = frozenset({XLSX_V2_SCHEMA_VERSION})
XLSX_V2_TOP_LEVEL_FIELDS = frozenset({"schema_version", "workbook", "sheets"})
XLSX_V2_WORKBOOK_FIELDS = frozenset({"title", "author"})
XLSX_V2_SHEET_FIELDS = frozenset({"name", "freeze_panes", "auto_filter", "column_widths", "row_heights", "merge_cells", "rows"})
XLSX_V2_FORMAT_FIELDS = frozenset(
    {
        "bold",
        "italic",
        "underline",
        "font_size",
        "font_color",
        "fill_color",
        "alignment",
        "vertical_alignment",
        "number_format",
        "border",
        "wrap_text",
    }
)
XLSX_V2_CELL_FIELDS = frozenset({"value", "formula"}) | XLSX_V2_FORMAT_FIELDS
XLSX_V2_ALIGNMENTS = frozenset({"left", "center", "right"})
XLSX_V2_VERTICAL_ALIGNMENTS = frozenset({"top", "middle", "bottom"})
XLSX_V2_BORDERS = frozenset({"none", "thin", "medium", "thick"})
XLSX_V2_UNSAFE_FORMULA_TOKENS = ("WEBSERVICE(", "FILTERXML(", "HYPERLINK(", "RTD(", "DDE", "CALL(", "REGISTER.ID(", "EXEC(")
PPTX_V2_SCHEMA_VERSION = "pptx_v2_1"
PPTX_V2_SUPPORTED_SCHEMA_VERSIONS = frozenset({PPTX_V2_SCHEMA_VERSION})
PPTX_V2_TOP_LEVEL_FIELDS = frozenset({"schema_version", "presentation", "slides"})
PPTX_V2_PRESENTATION_FIELDS = frozenset({"title", "author", "slide_size"})
PPTX_V2_SLIDE_FIELDS = frozenset({"layout", "title", "subtitle", "body", "content", "image", "notes"})
PPTX_V2_LAYOUTS = frozenset({"title", "content", "section_header", "image", "blank"})
PPTX_V2_CONTENT_TYPES = frozenset({"bullets", "paragraph", "table", "image", "text_box"})
PPTX_V2_BULLETS_FIELDS = frozenset({"type", "items"})
PPTX_V2_BULLET_ITEM_FIELDS = frozenset({"text", "level", "bold", "italic", "font_size", "color"})
PPTX_V2_PARAGRAPH_FIELDS = frozenset({"type", "text", "bold", "italic", "font_size", "color", "alignment"})
PPTX_V2_TABLE_FIELDS = frozenset({"type", "rows", "header_row"})
PPTX_V2_IMAGE_ELEMENT_FIELDS = frozenset({"type", "path", "width_mm", "height_mm", "align"})
PPTX_V2_TEXT_BOX_FIELDS = frozenset(
    {"type", "text", "left_mm", "top_mm", "width_mm", "height_mm", "bold", "italic", "font_size", "color", "alignment"}
)
PPTX_V2_SLIDE_IMAGE_FIELDS = frozenset({"path", "width_mm", "height_mm", "align"})
PPTX_V2_ALIGNMENTS = frozenset({"left", "center", "right"})
PPTX_V2_BULLET_LEVELS = frozenset({0, 1, 2, 3})
PPTX_V2_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
PPTX_V2_SLIDE_SIZE_PRESETS = frozenset({"16:9", "4:3", "A4_portrait"})
PPTX_V2_CUSTOM_SIZE_FIELDS = frozenset({"name", "width_mm", "height_mm"})
PPTX_V2_CUSTOM_SIZE_MIN_MM = 100
PPTX_V2_CUSTOM_SIZE_MAX_MM = 1200
PDF_V2_SCHEMA_VERSION = "pdf_v2_1"
PDF_V2_SUPPORTED_SCHEMA_VERSIONS = frozenset({PDF_V2_SCHEMA_VERSION})
PDF_V2_TOP_LEVEL_FIELDS = frozenset({"schema_version", "document", "page", "styles", "content"})
PDF_V2_DOCUMENT_FIELDS = frozenset({"title", "author", "language"})
PDF_V2_PAGE_FIELDS = frozenset({"size", "orientation", "margins_mm"})
PDF_V2_MARGIN_FIELDS = frozenset({"top", "bottom", "left", "right"})
PDF_V2_STYLE_NAMES = frozenset({"body", "title", "heading1", "heading2", "heading3", "quote", "blockquote"})
PDF_V2_STYLE_FIELDS = frozenset(
    {
        "font",
        "size_pt",
        "bold",
        "italic",
        "underline",
        "alignment",
        "line_spacing",
        "space_before_pt",
        "space_after_pt",
        "first_line_indent_mm",
        "page_break_before",
    }
)
PDF_V2_TEXT_TYPES = frozenset({"title", "heading1", "heading2", "heading3", "paragraph", "quote", "blockquote"})
PDF_V2_TEXT_ELEMENT_FIELDS = frozenset({"type", "text", "runs", "style", "style_overrides"})
PDF_V2_RUN_FIELDS = frozenset({"text", "bold", "italic", "underline"})
PDF_V2_LIST_FIELDS = frozenset({"type", "items", "style_overrides"})
PDF_V2_IMAGE_FIELDS = frozenset({"type", "path", "width_mm", "height_mm", "align"})
PDF_V2_TABLE_FIELDS = frozenset({"type", "rows", "header_row"})
PDF_V2_CONTENT_TYPES = PDF_V2_TEXT_TYPES | frozenset({"bullet_list", "numbered_list", "page_break", "image", "table"})
PDF_V2_PAGE_SIZES = frozenset({"A4", "A5"})
PDF_V2_ORIENTATIONS = frozenset({"portrait", "landscape"})
PDF_V2_ALIGNMENTS = frozenset({"left", "center", "right", "justify"})
PDF_V2_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg"})
PDF_V2_CUSTOM_SIZE_FIELDS = frozenset({"name", "width_mm", "height_mm"})
PDF_V2_CUSTOM_SIZE_MIN_MM = 100
PDF_V2_CUSTOM_SIZE_MAX_MM = 1200
DESCRIBE_SCOPES = frozenset(
    {
        "tools",
        "status",
        "workspace_operation",
        "document_operation",
        "reflection",
        "governor",
        "sandbox",
        "profiles",
        "describe",
    }
)
# RC12-DESC-001 (A) — tool-name aliases so `describe scope=<tool>` resolves to the
# canonical scope instead of failing with unknown_scope (discoverability).
_DESCRIBE_SCOPE_ALIASES = {
    "workspace": "workspace_operation",
    "workspace_op": "workspace_operation",
    "plwc_workspace_operation": "workspace_operation",
    "document": "document_operation",
    "plwc_document_operation": "document_operation",
    "profile": "profiles",
    "plwc_profile": "profiles",
    "sandbox_run": "sandbox",
    "plwc_sandbox_run": "sandbox",
    "plwc_status": "status",
    "plwc_reflection": "reflection",
    "plwc_governor": "governor",
    "plwc_describe": "describe",
}
DESCRIBE_REQUIREMENTS = (
    "FR-DESC-001",
    "FR-DESC-002",
    "FR-DESC-003",
    "FR-DESC-004",
    "FR-DESC-005",
    "FR-DESC-006",
    "FR-DESC-007",
    "FR-DESC-008",
)

PUBLIC_TOOLS = (
    PUBLIC_STATUS_TOOL,
    DESCRIBE_TOOL,
    PROFILE_TOOL,
    REFLECTION_TOOL,
    GOVERNOR_TOOL,
    SANDBOX_RUN_TOOL,
    WORKSPACE_OPERATION_TOOL,
    DOCUMENT_OPERATION_TOOL,
)
LEGACY_PUBLIC_TOOL_NAMES = (
    "plwc_runtime_status",
    "plwc_sandbox_status",
    "plwc_first_run_status",
    "plwc_generate_claude_config",
    "plwc_profile_status",
    "plwc_profile_snapshot",
    "plwc_compile_profile",
    "plwc_write_reflection",
    "plwc_governor_plan",
    "plwc_governor_apply",
    "plwc_run_python_sandboxed",
    "plwc_run_shell_sandboxed",
    "plwc_list_workspace",
    "plwc_search_workspace",
    "plwc_read_workspace_file",
    "plwc_write_workspace_file",
)


def public_server_metadata() -> dict[str, Any]:
    return {
        "name": PUBLIC_SERVER_NAME,
        "version": __version__,
        "tools": list(PUBLIC_TOOLS),
    }


def _runtime_status_payload(config: GatewayConfig) -> dict[str, Any]:
    tool_count = len(PUBLIC_TOOLS)
    pba_probe = PBAProfileAdapter(
        profile_root=config.profile_root,
        memory_write_threshold=config.governance.memory_write_threshold,
        persona_write_threshold=config.governance.persona_write_threshold,
        temperament_write_threshold=config.governance.temperament_write_threshold,
        active_profile_name=config.active_profile_name,
        configured_active_profile_name=config.configured_active_profile_name,
        active_profile_source=config.active_profile_source,
        active_profile_state_file=config.active_profile_state_file,
        persona_layer_enabled=config.persona_layer_enabled,
    )
    selected_profile = _selected_profile("", config)
    profile_setup = pba_probe.profile_setup_status(selected_profile)
    return {
        "ok": True,
        "server": PUBLIC_SERVER_NAME,
        "version": __version__,
        "phase": "mvp-gateway",
        "public_server_name": PUBLIC_SERVER_NAME,
        "expected_public_tool_count": tool_count,
        "registered_public_tool_count": tool_count,
        "public_tools": list(PUBLIC_TOOLS),
        "workspace_root": str(config.allowed_roots[0]) if config.allowed_roots else None,
        "profile_root": str(config.profile_root),
        "configured_active_profile": profile_setup["configured_active_profile"],
        "resolved_active_profile": profile_setup["resolved_active_profile"],
        "active_profile_name": profile_setup["active_profile_name"],
        "active_profile_source": profile_setup["active_profile_source"],
        "active_state_profile": profile_setup.get("active_state_profile"),
        "mismatch_reason": profile_setup.get("mismatch_reason"),
        "profile_state_note": _profile_state_note(
            mismatch_reason=profile_setup.get("mismatch_reason"),
            configured_profile=profile_setup.get("configured_active_profile"),
            state_profile=profile_setup.get("active_state_profile"),
        ),
        "active_profile_status": profile_setup["status"],
        "onboarding_target_profile": profile_setup["onboarding_target_profile"],
        "profile_exists": profile_setup["profile_exists"],
        "profile_valid": profile_setup["profile_valid"],
        "active_profile_directory": profile_setup["active_profile_directory"],
        "policy_config_source": config.config_source,
        "policy_config_note": _policy_config_note(config.config_source),
        "security_config_path": str(config.config_file) if config.config_file else None,
        "install_mode": _install_mode(),
        "adapters": {
            "pba": "plwc_internal_profile_runtime",
            "hardened_commander": "internal_safe_adapter",
        },
        "profile_governor_reflection_support": {
            "public_tools_registered": True,
            "pba_adapter_boundary": "internal",
            "profile_runtime_source": pba_probe.profile_runtime_source,
            "active_profile_exists": profile_setup["active_profile_exists"],
            "profile_exists": profile_setup["profile_exists"],
            "profile_valid": profile_setup["profile_valid"],
            "status": profile_setup["status"],
            "profile_activation_supported": profile_setup["profile_activation_supported"],
            "profile_runtime_available": profile_setup["profile_runtime_available"],
            "profile_runtime_reason": profile_setup["profile_runtime_reason"],
            "governed_reflection_available": True,
            "separate_visible_pba_mcp_required": False,
            "unavailable_behavior": "tools remain callable and return setup-required or internal-unavailable responses",
        },
        "available_profiles": profile_setup["available_profiles"],
        "available_profile_names": profile_setup["available_profile_names"],
        "required_profile_files": profile_setup["required_files"],
        "missing_profile_files": profile_setup["missing_files"],
        "governance_thresholds": config.governance.as_dict(),
        "profile_compile": {
            "persona_layer_enabled": config.persona_layer_enabled,
            "persona_layer_enabled_source": config.persona_layer_enabled_source,
            "requirement_id": V1_PERSONA_LAYER_REQUIREMENT_ID,
            "extension_config_key": "persona_layer_disabled",
            "env_var": PERSONA_LAYER_DISABLED_ENV_VAR,
            "disable_value": True,
            "legacy_extension_config_key": "persona_layer_enabled",
            "legacy_env_var": PERSONA_LAYER_ENABLED_ENV_VAR,
        },
        "setup_warnings": list(config.setup_warnings),
    }


def _runtime_status_result(loaded: GatewayConfig) -> dict[str, Any]:
    """Policy-checked runtime status payload shared by the plwc_status runtime
    scope and the legacy plwc_runtime_status entry point. (RC2-HYGIENE-002)"""
    execution = execute_with_policy(
        PolicyIntent(tool_name=PUBLIC_STATUS_TOOL, action=IntentAction.STATUS),
        lambda: _runtime_status_payload(loaded),
    )
    if execution.executed:
        return execution.adapter_result
    return {
        "ok": False,
        "server": PUBLIC_SERVER_NAME,
        "error": execution.policy.reason,
        "policy_decision": execution.policy.decision.value,
    }


def plwc_runtime_status(
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    result = _runtime_status_result(loaded)
    _audit_public_result(PUBLIC_STATUS_TOOL, result, config=loaded, audit_logger=audit_logger)
    return result


def _first_run_status_result(
    loaded: GatewayConfig,
    *,
    docker_available: bool | None,
    sandbox_adapter: DockerSandboxAdapter | None,
    document_worker_adapter: DocumentWorkerAdapter | None,
) -> dict[str, Any]:
    """First-run status payload shared by the plwc_status first_run scope and the
    legacy plwc_first_run_status entry point. (RC2-HYGIENE-002)"""
    sandbox_status = _public_payload((sandbox_adapter or _sandbox_adapter(loaded)).status())
    document_worker_status = _public_payload((document_worker_adapter or _document_worker_adapter(loaded)).status())
    return build_first_run_status(
        loaded,
        docker_available=bool(docker_available) if docker_available is not None else bool(sandbox_status.get("ok")),
        sandbox_status=sandbox_status,
        document_worker_status=document_worker_status,
    ).as_dict()


def plwc_first_run_status(
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    docker_available: bool | None = None,
    sandbox_adapter: DockerSandboxAdapter | None = None,
    document_worker_adapter: DocumentWorkerAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    result = _first_run_status_result(
        loaded,
        docker_available=docker_available,
        sandbox_adapter=sandbox_adapter,
        document_worker_adapter=document_worker_adapter,
    )
    _audit_public_result("plwc_first_run_status", result, config=loaded, audit_logger=audit_logger)
    return result


def plwc_generate_claude_config(
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
) -> dict[str, Any]:
    result = generate_claude_config()
    _audit_public_result("plwc_generate_claude_config", result, config=config, audit_logger=audit_logger)
    return result


def plwc_status(
    scope: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    docker_available: bool | None = None,
    sandbox_adapter: DockerSandboxAdapter | None = None,
    document_worker_adapter: DocumentWorkerAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_scope = _normalize_dispatch_value(scope)
    if normalized_scope not in SUPPORTED_STATUS_SCOPES:
        payload = _dispatch_validation_failure(
            PUBLIC_STATUS_TOOL,
            "scope",
            normalized_scope or str(scope),
            sorted(SUPPORTED_STATUS_SCOPES),
        )
        _audit_public_result(PUBLIC_STATUS_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    if normalized_scope == "runtime":
        payload = _runtime_status_result(loaded)
    elif normalized_scope == "sandbox":
        payload = _public_payload((sandbox_adapter or _sandbox_adapter(loaded)).status())
    elif normalized_scope == "first_run":
        payload = _first_run_status_result(
            loaded,
            docker_available=docker_available,
            sandbox_adapter=sandbox_adapter,
            document_worker_adapter=document_worker_adapter,
        )
    else:
        generated_config = generate_claude_config()
        payload = {
            "ok": True,
            "server_name": PUBLIC_SERVER_NAME,
            "config": generated_config,
            **generated_config,
        }

    payload["facade"] = PUBLIC_STATUS_TOOL
    payload["scope"] = normalized_scope
    _audit_public_result(PUBLIC_STATUS_TOOL, payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_read_workspace_file(
    path: str,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: SafeFilesystemAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    filesystem = adapter or _filesystem_adapter(loaded)
    result = filesystem.read_text(path)
    payload = _public_payload(result)
    _audit_public_result("plwc_read_workspace_file", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_write_workspace_file(
    path: str,
    content: str,
    mode: str = "rewrite",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: SafeFilesystemAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    preflight = _audit_preflight(
        "plwc_write_workspace_file",
        {"path": path, "content": content, "mode": mode},
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    filesystem = adapter or _filesystem_adapter(loaded)
    result = filesystem.write_text(path, content, mode=mode.strip().casefold())
    payload = _public_payload(result)
    audit_failure = _audit_public_result(
        "plwc_write_workspace_file",
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_list_workspace(
    path: str,
    depth: int = 1,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: SafeFilesystemAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    filesystem = adapter or _filesystem_adapter(loaded)
    result = filesystem.list_directory(path, depth=depth)
    payload = _public_payload(result)
    _audit_public_result("plwc_list_workspace", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_search_workspace(
    path: str,
    query: str,
    max_results: int | None = None,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: SafeFilesystemAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    filesystem = adapter or _filesystem_adapter(loaded)
    result = filesystem.search_text(path, query, max_results=max_results)
    payload = _public_payload(result)
    _audit_public_result("plwc_search_workspace", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_workspace_operation(
    operation: str,
    path: str = "",
    content: str = "",
    content_base64: str = "",
    mode: str = "rewrite",
    depth: int = 1,
    query: str = "",
    max_results: int | None = None,
    source_path: str = "",
    target_path: str = "",
    paths: list[str] | None = None,
    old_text: str = "",
    new_text: str = "",
    expected_replacements: int | None = None,
    overwrite: bool = False,
    max_files: int | None = None,
    max_bytes_per_file: int | None = None,
    max_total_bytes: int | None = None,
    max_bytes: int | None = None,
    require_content_hash: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: SafeFilesystemAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    filesystem = adapter or _filesystem_adapter(loaded)
    normalized_operation = _normalize_workspace_operation(operation)
    high_risk = normalized_operation in WRITE_WORKSPACE_OPERATIONS

    validation_error = _validate_workspace_operation(
        operation=operation,
        normalized_operation=normalized_operation,
        path=path,
        content=content,
        content_base64=content_base64,
        mode=mode,
        depth=depth,
        query=query,
        max_results=max_results,
        source_path=source_path,
        target_path=target_path,
        paths=paths,
        old_text=old_text,
        new_text=new_text,
        expected_replacements=expected_replacements,
        overwrite=overwrite,
        max_files=max_files,
        max_bytes_per_file=max_bytes_per_file,
        max_total_bytes=max_total_bytes,
        max_bytes=max_bytes,
        require_content_hash=require_content_hash,
    )
    if validation_error is not None:
        _audit_public_result(
            WORKSPACE_OPERATION_TOOL,
            validation_error,
            config=loaded,
            audit_logger=audit_logger,
            high_risk=high_risk,
        )
        return validation_error

    preflight = None
    if high_risk:
        preflight = _audit_preflight(
            WORKSPACE_OPERATION_TOOL,
            _workspace_operation_audit_arguments(
                normalized_operation,
                path=path,
                content=content,
                content_base64=content_base64,
                mode=mode,
                depth=depth,
                query=query,
                max_results=max_results,
                source_path=source_path,
                target_path=target_path,
                paths=paths,
                old_text=old_text,
                new_text=new_text,
                expected_replacements=expected_replacements,
                overwrite=overwrite,
                max_files=max_files,
                max_bytes_per_file=max_bytes_per_file,
                max_total_bytes=max_total_bytes,
                max_bytes=max_bytes,
                require_content_hash=require_content_hash,
            ),
            config=loaded,
            audit_logger=audit_logger,
            high_risk=True,
        )
    if preflight is not None:
        payload = _workspace_operation_payload(
            preflight,
            normalized_operation,
            error_category="audit_error",
        )
        _audit_public_result(
            WORKSPACE_OPERATION_TOOL,
            payload,
            config=loaded,
            audit_logger=audit_logger,
            high_risk=True,
        )
        return payload

    if normalized_operation == "list":
        result = filesystem.list_directory(path, depth=depth)
        payload = _workspace_operation_payload(result, normalized_operation, path=path)
    elif normalized_operation == "search":
        result = filesystem.search_text(path, query, max_results=max_results)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            path=path,
            read_files=(path,) if result.ok else (),
        )
    elif normalized_operation == "read":
        result = filesystem.read_text(path)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            path=path,
            read_files=(path,) if result.ok else (),
        )
    elif normalized_operation == "write":
        result = filesystem.write_text(path, content, mode=mode.strip().casefold())
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            path=path,
            changed_files=(path,) if result.ok else (),
        )
    elif normalized_operation == "file_info":
        result = filesystem.file_info(path)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            read_files=(path,) if result.ok else (),
        )
    elif normalized_operation == "create_dir":
        result = filesystem.create_directory(path)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            changed_files=(path,) if result.ok else (),
        )
    elif normalized_operation in {"move", "rename"}:
        result = filesystem.move_path(source_path, target_path, overwrite=False)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            source_path=source_path,
            target_path=target_path,
            changed_files=(source_path, target_path) if result.ok else (),
        )
    elif normalized_operation == "batch_read":
        effective_max_files = _effective_positive_int(max_files, WORKSPACE_BATCH_MAX_FILES)
        effective_max_bytes_per_file = _effective_positive_int(
            max_bytes_per_file,
            WORKSPACE_BATCH_MAX_BYTES_PER_FILE,
        )
        effective_max_total_bytes = _effective_positive_int(max_total_bytes, WORKSPACE_BATCH_MAX_TOTAL_BYTES)
        result = filesystem.read_multiple_text(
            paths or (),
            max_files=effective_max_files,
            max_file_bytes=effective_max_bytes_per_file,
            max_total_bytes=effective_max_total_bytes,
        )
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            read_files=tuple(item.path for item in result.files if item.error is None) if result.ok else (),
        )
        payload["limits"] = {
            "max_files": effective_max_files,
            "max_bytes_per_file": effective_max_bytes_per_file,
            "max_total_bytes": effective_max_total_bytes,
        }
    elif normalized_operation == "exact_replace":
        payload = _workspace_exact_replace_payload(
            filesystem=filesystem,
            operation=normalized_operation,
            path=path,
            old_text=old_text,
            new_text=new_text,
            expected_replacements=expected_replacements or 0,
            require_content_hash=require_content_hash,
        )
    elif normalized_operation == "copy":
        effective_max = _effective_positive_int(max_bytes, loaded.workspace_binary_max_bytes)
        result = filesystem.copy_path(source_path, target_path, overwrite=False, max_bytes=effective_max)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            source_path=source_path,
            target_path=target_path,
            changed_files=(target_path,) if result.ok else (),
            read_files=(source_path,) if result.ok else (),
        )
        payload["limits"] = {"max_bytes": effective_max}
        if result.binary_data is not None:
            payload["binary_data"] = result.binary_data
    elif normalized_operation == "read_binary":
        effective_max = _effective_positive_int(max_bytes, loaded.workspace_binary_max_bytes)
        result = filesystem.read_binary(path, max_bytes=effective_max)
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            path=path,
            read_files=(path,) if result.ok else (),
        )
        payload["limits"] = {"max_bytes": effective_max}
        if result.binary_data is not None:
            payload["binary_data"] = result.binary_data
    elif normalized_operation == "write_binary":
        effective_max = _effective_positive_int(max_bytes, loaded.workspace_binary_max_bytes)
        result = filesystem.write_binary(
            path,
            content_base64,
            mode=mode.strip().casefold(),
            max_bytes=effective_max,
        )
        payload = _workspace_operation_payload(
            result,
            normalized_operation,
            path=path,
            changed_files=(path,) if result.ok else (),
        )
        payload["limits"] = {"max_bytes": effective_max}
        if result.binary_data is not None:
            payload["binary_data"] = result.binary_data
    else:
        payload = _workspace_operation_failure(
            normalized_operation,
            "Unsupported workspace operation.",
            ("FR-CMD-PUB-002", "NFR-002"),
            error_category="unsupported_operation",
        )

    audit_failure = _audit_public_result(
        WORKSPACE_OPERATION_TOOL,
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=high_risk,
    )
    return audit_failure or payload


def plwc_document_operation(
    operation: str,
    output_path: str = "",
    content: dict[str, Any] | None = None,
    overwrite: bool = False,
    input_path: str = "",
    input_paths: list[str] | None = None,
    output_dir: str = "",
    pages: list[int | str] | None = None,
    rotation: int | None = None,
    mode: str = "pages",
    format: str = "text",
    max_pages: int | None = None,
    max_chars: int | None = None,
    include_preview: bool = False,
    max_preview_chars: int | None = None,
    sheets: list[str | int] | None = None,
    ranges: dict[str, str] | list[str] | None = None,
    slides: list[int | str | dict[str, Any]] | None = None,
    title: str = "",
    include_notes: bool = False,
    max_rows: int | None = None,
    max_cells: int | None = None,
    max_size_kb: int | None = None,
    resize_to: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: DocumentWorkerAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_operation = _normalize_document_operation(operation)
    content_payload = _document_creation_content(
        normalized_operation,
        content,
        title=title,
        slides=slides,
    )
    operation_format = _document_operation_effective_format(normalized_operation, format)
    validation_error = _validate_document_operation(
        operation=operation,
        normalized_operation=normalized_operation,
        output_path=output_path,
        input_path=input_path,
        input_paths=input_paths,
        output_dir=output_dir,
        pages=pages,
        rotation=rotation,
        mode=mode,
        output_format=operation_format,
        max_pages=max_pages,
        max_chars=max_chars,
        include_preview=include_preview,
        max_preview_chars=max_preview_chars,
        sheets=sheets,
        ranges=ranges,
        slides=slides,
        title=title,
        include_notes=include_notes,
        max_rows=max_rows,
        max_cells=max_cells,
        max_size_kb=max_size_kb,
        resize_to=resize_to,
        content=content_payload,
        overwrite=overwrite,
    )
    if validation_error is not None:
        _audit_public_result(
            DOCUMENT_OPERATION_TOOL,
            validation_error,
            config=loaded,
            audit_logger=audit_logger,
            high_risk=True,
        )
        return validation_error

    preflight = _audit_preflight(
        DOCUMENT_OPERATION_TOOL,
        _document_operation_audit_arguments(
            normalized_operation,
            output_path=output_path,
            input_path=input_path,
            input_paths=input_paths,
            output_dir=output_dir,
            pages=pages,
            rotation=rotation,
            mode=mode,
            output_format=operation_format,
            max_pages=max_pages,
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            sheets=sheets,
            ranges=ranges,
            slides=slides,
            include_notes=include_notes,
            max_rows=max_rows,
            max_cells=max_cells,
            max_size_kb=max_size_kb,
            resize_to=resize_to,
            content=content_payload,
            overwrite=overwrite,
        ),
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        payload = _document_operation_payload(
            preflight,
            normalized_operation,
            output_path=output_path,
            input_path=input_path,
            input_paths=input_paths,
            output_dir=output_dir,
            error_category="audit_error",
        )
        _audit_public_result(DOCUMENT_OPERATION_TOOL, payload, config=loaded, audit_logger=audit_logger, high_risk=True)
        return payload

    worker = adapter or _document_worker_adapter(loaded)
    if normalized_operation in SUPPORTED_DOCUMENT_CREATE_OPERATIONS:
        title, body = _document_title_and_body(normalized_operation, content_payload)
        create_kwargs: dict[str, Any] = {
            "title": title,
            "body": body,
            "content": content_payload,
            "overwrite": False,
        }
        if normalized_operation in {"create_docx", "create_xlsx", "create_pptx", "create_pdf"} and input_path:
            create_kwargs["input_path"] = input_path
        result = getattr(worker, normalized_operation)(output_path, **create_kwargs)
    elif normalized_operation == "inspect_pdf":
        result = worker.inspect_pdf(input_path)
    elif normalized_operation == "merge_pdf":
        result = worker.merge_pdf(input_paths or [], output_path, overwrite=False)
    elif normalized_operation == "split_pdf":
        result = worker.split_pdf(input_path, output_dir, mode=mode)
    elif normalized_operation == "extract_pdf":
        result = worker.extract_pdf(input_path, output_path, pages or [], overwrite=False)
    elif normalized_operation == "rotate_pdf":
        result = worker.rotate_pdf(input_path, output_path, rotation or 0, pages=pages or [], overwrite=False)
    elif normalized_operation == "extract_pdf_text":
        result = worker.extract_pdf_text(
            input_path,
            output_path or None,
            output_format=operation_format,
            pages=pages or [],
            max_pages=max_pages,
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=False,
        )
    elif normalized_operation == "inspect_zip":
        result = worker.inspect_zip(input_path)
    elif normalized_operation == "extract_zip":
        result = worker.extract_zip(input_path, output_dir, overwrite=False)
    elif normalized_operation == "create_zip":
        result = worker.create_zip(
            output_path,
            input_path=input_path or None,
            input_paths=input_paths or [],
            overwrite=False,
        )
    elif normalized_operation == "read_image":
        result = worker.read_image(
            input_path,
            max_size_kb=max_size_kb,
            resize_to=resize_to,
            output_format=operation_format,
        )
    elif normalized_operation in {"inspect_docx", "inspect_xlsx", "inspect_pptx", "inspect_odt", "inspect_ods", "inspect_odp"}:
        result = getattr(worker, normalized_operation)(input_path)
    elif normalized_operation in {"extract_docx_text", "extract_odt_text"}:
        result = getattr(worker, normalized_operation)(
            input_path,
            output_path or None,
            output_format=operation_format,
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=False,
        )
    elif normalized_operation in {"extract_pptx_text", "extract_odp_text"}:
        result = getattr(worker, normalized_operation)(
            input_path,
            output_path or None,
            slides=slides or [],
            max_chars=max_chars,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            include_notes=include_notes,
            overwrite=False,
        )
    elif normalized_operation in {"extract_xlsx_data", "extract_ods_data"}:
        result = getattr(worker, normalized_operation)(
            input_path,
            output_path or None,
            sheets=sheets or [],
            ranges=ranges or {},
            max_rows=max_rows,
            max_cells=max_cells,
            include_preview=include_preview,
            max_preview_chars=max_preview_chars,
            overwrite=False,
        )
    elif normalized_operation == "edit_docx":
        result = worker.edit_docx(
            input_path,
            output_path,
            content=content_payload,
            overwrite=False,
        )
    else:
        result = _document_operation_failure(
            normalized_operation,
            "Unsupported document operation.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=output_path,
            error_category="unsupported_operation",
        )
    payload = _document_operation_payload(
        result,
        normalized_operation,
        output_path=output_path,
        input_path=input_path,
        input_paths=input_paths,
        output_dir=output_dir,
    )
    audit_failure = _audit_public_result(
        DOCUMENT_OPERATION_TOOL,
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_describe(
    scope: str = "tools",
    detail: str = "short",
    format: str = "json",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_scope = _normalize_describe_scope(scope)
    normalized_detail = detail.strip().casefold() if isinstance(detail, str) else ""
    normalized_format = format.strip().casefold() if isinstance(format, str) else ""

    if normalized_scope not in DESCRIBE_SCOPES:
        payload = {
            "ok": False,
            "operation": "describe",
            "scope": normalized_scope or str(scope),
            "policy_decision": PolicyDecision.DENY.value,
            "error": (
                "Unsupported describe scope. Supported scopes: "
                f"{', '.join(sorted(DESCRIBE_SCOPES))}. Tool-name aliases are accepted "
                "(e.g. 'workspace' -> 'workspace_operation', 'profile' -> 'profiles')."
            ),
            "error_category": "unknown_scope",
            "supported_scopes": sorted(DESCRIBE_SCOPES),
            "scope_aliases": dict(sorted(_DESCRIBE_SCOPE_ALIASES.items())),
            "requirement_ids": list(DESCRIBE_REQUIREMENTS),
        }
        _audit_public_result(DESCRIBE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_detail not in {"short", "full"}:
        payload = _describe_validation_failure(
            normalized_scope,
            normalized_detail,
            normalized_format,
            "detail must be short or full.",
            "validation_error",
        )
        _audit_public_result(DESCRIBE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_format not in {"json", "markdown"}:
        payload = _describe_validation_failure(
            normalized_scope,
            normalized_detail,
            normalized_format,
            "format must be json or markdown.",
            "validation_error",
        )
        _audit_public_result(DESCRIBE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    data = _describe_data(normalized_scope, normalized_detail, loaded)
    if normalized_format == "markdown":
        data = {"markdown": _describe_markdown(normalized_scope, data)}
    payload = {
        "ok": True,
        "operation": "describe",
        "scope": normalized_scope,
        "detail": normalized_detail,
        "format": normalized_format,
        "policy_decision": PolicyDecision.ALLOW.value,
        "data": data,
        "requirement_ids": list(DESCRIBE_REQUIREMENTS),
    }
    _audit_public_result(DESCRIBE_TOOL, payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_profile_status(
    profile: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.runtime_status(_selected_profile(profile, loaded))
    payload = _public_payload(result)
    _audit_public_result("plwc_profile_status", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_profile_snapshot(
    profile: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.snapshot(_selected_profile(profile, loaded))
    payload = _public_payload(result)
    _audit_public_result("plwc_profile_snapshot", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_compile_profile(
    profile: str = "",
    task_context: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.compile_profile(_selected_profile(profile, loaded), task_context=task_context)
    payload = _public_payload(result)
    _audit_public_result("plwc_compile_profile", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_profile(
    operation: str = "",
    profile: str = "",
    task_context: str = "",
    query: str = "",
    limit: int = 5,
    include_retired: bool = False,
    require_fresh: bool = False,
    min_dates: int = 2,
    compile_mode: str = DEFAULT_PROFILE_COMPILE_MODE,
    compile_max_chars: int = 0,
    doctor_mode: str = "clu",
    doctor_scope: str = "general",
    persona_layer: bool | None = None,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_operation = _normalize_dispatch_value(operation)
    if normalized_operation not in SUPPORTED_PROFILE_OPERATIONS:
        payload = _dispatch_validation_failure(
            PROFILE_TOOL,
            "operation",
            normalized_operation or str(operation),
            sorted(SUPPORTED_PROFILE_OPERATIONS),
        )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    normalized_compile_mode = _normalize_dispatch_value(compile_mode)
    if normalized_operation == "compile" and normalized_compile_mode not in SUPPORTED_COMPILE_MODES:
        payload = _dispatch_validation_failure(
            PROFILE_TOOL,
            "compile_mode",
            normalized_compile_mode or str(compile_mode),
            sorted(SUPPORTED_COMPILE_MODES),
        )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    normalized_compile_max_chars = _normalize_compile_max_chars(compile_max_chars, normalized_compile_mode)
    if (
        normalized_operation == "compile"
        and normalized_compile_mode != "full"
        and normalized_compile_max_chars is None
    ):
        payload = {
            **_dispatch_validation_failure(
                PROFILE_TOOL,
                "compile_max_chars",
                compile_max_chars,
                [f"{MIN_COMPACT_COMPILE_MAX_CHARS}..{MAX_COMPACT_COMPILE_MAX_CHARS}"],
            ),
            "error": (
                "compile_max_chars must be an integer between "
                f"{MIN_COMPACT_COMPILE_MAX_CHARS} and {MAX_COMPACT_COMPILE_MAX_CHARS}; "
                "use 0 to accept the mode default."
            ),
        }
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    persona_layer_source = loaded.persona_layer_enabled_source
    if persona_layer is None:
        normalized_persona_layer = loaded.persona_layer_enabled
    else:
        normalized_persona_layer = _normalize_persona_layer_enabled(persona_layer)
        persona_layer_source = "request_parameter"
        if normalized_operation == "compile" and normalized_persona_layer is None:
            payload = _dispatch_validation_failure(
                PROFILE_TOOL,
                "persona_layer",
                persona_layer,
                ["true", "false", "enabled", "disabled"],
            )
            _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
            return payload
    normalized_doctor_mode = _normalize_dispatch_value(doctor_mode)
    normalized_doctor_scope = _normalize_dispatch_value(doctor_scope)
    if normalized_operation == "doctor" and normalized_doctor_mode not in SUPPORTED_DOCTOR_MODES:
        payload = _dispatch_validation_failure(
            PROFILE_TOOL,
            "doctor_mode",
            normalized_doctor_mode or str(doctor_mode),
            sorted(SUPPORTED_DOCTOR_MODES),
        )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_operation == "doctor" and normalized_doctor_scope not in SUPPORTED_DOCTOR_SCOPES:
        payload = _dispatch_validation_failure(
            PROFILE_TOOL,
            "doctor_scope",
            normalized_doctor_scope or str(doctor_scope),
            sorted(SUPPORTED_DOCTOR_SCOPES),
        )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    profile_adapter = adapter or _profile_adapter(loaded)
    selected_profile = _selected_profile(profile, loaded)
    if normalized_operation == "doctor":
        payload = _clu_doctor_payload(
            loaded,
            profile=selected_profile,
            doctor_scope=normalized_doctor_scope,
            task_context=task_context,
            query=query,
        )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_operation == "retrieve":
        # RC8-FEAT-002 — read-only semantic retrieval (evidence only).
        if not _qdrant_enabled_for(loaded, selected_profile):
            payload = _qdrant_feature_disabled_payload(PROFILE_TOOL, "retrieve")
        else:
            memory_path, storage_dir = _qdrant_paths(loaded, selected_profile)
            payload = _bounded_qdrant_retrieve(
                profile=selected_profile,
                query=query,
                memory_path=memory_path,
                storage_dir=storage_dir,
                limit=limit,
                include_retired=include_retired,
                require_fresh=require_fresh,
            )
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_operation == "scan_tagebuch":
        # V1-INNER-002 — read-only recurrence surfacing over Tagebuch/*.md. Writes
        # nothing; the model reviews + phrases, the governed promotion applies.
        # RC12-INNER-001 — annotate clusters with redundancy vs the ACTIVE entries of
        # memory.md + TEMPERAMENT.md. RC12-FS-004 keeps the public scanner on the
        # deterministic keyword path: optional FastEmbed/Qdrant work must not make a
        # Tagebuch smoke disconnect. Advisory only; nothing is withheld or written.
        tagebuch_dir = (loaded.allowed_roots[0] / "Tagebuch") if loaded.allowed_roots else Path("Tagebuch")
        profile_dir = loaded.profile_root / selected_profile
        existing_active = _active_promotion_entries(profile_dir)
        qdrant_enabled = bool(existing_active and _qdrant_enabled_for(loaded, selected_profile))
        data = scan_tagebuch_patterns(
            tagebuch_dir,
            min_dates=min_dates,
            existing_active=existing_active,
            redundancy_threshold=_inner_redundancy_threshold(loaded, selected_profile),
            use_embeddings=False,
            name_aliases=_inner_name_aliases(loaded, selected_profile),
        )
        if qdrant_enabled:
            data["redundancy_embedding_fallback"] = {
                "active": True,
                "reason": "public_scan_uses_keyword_overlap",
                "detail": (
                    "scan_tagebuch does not run optional FastEmbed/Qdrant embedding work; "
                    "redundancy warnings use deterministic keyword overlap."
                ),
            }
        payload = {
            "ok": True,
            "facade": PROFILE_TOOL,
            "operation": "scan_tagebuch",
            "policy_decision": PolicyDecision.ALLOW.value,
            "data": data,
            "requirement_ids": list(FACADE_REQUIREMENTS) + ["RC12-FS-004"],
        }
        _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload
    if normalized_operation == "status":
        result = profile_adapter.runtime_status(selected_profile)
    elif normalized_operation == "snapshot":
        result = profile_adapter.snapshot(selected_profile)
    else:
        result = profile_adapter.compile_profile(
            selected_profile,
            task_context=task_context,
            record_journal_event=False,
        )
    payload = _public_payload(result)
    if normalized_operation == "compile":
        semantic_memory = (
            _working_compile_semantic_memory(
                loaded,
                profile=selected_profile,
                task_context=task_context,
            )
            if normalized_compile_mode == "working"
            else None
        )
        _apply_profile_compile_mode(
            payload,
            compile_mode=normalized_compile_mode,
            compile_max_chars=normalized_compile_max_chars or _default_compile_max_chars(normalized_compile_mode),
            semantic_memory=semantic_memory,
            persona_layer_enabled=bool(normalized_persona_layer),
            persona_layer_source=persona_layer_source,
        )
    payload["facade"] = PROFILE_TOOL
    payload["operation"] = normalized_operation
    _audit_public_result(PROFILE_TOOL, payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_write_reflection(
    profile: str = "",
    summary: str = "",
    evidence: str = "",
    confidence: str = "",
    marker: str = "observation",
    trust: str = "",
    candidate_for: str = "",
    target: str = "",
    entry_date: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    preflight = _audit_preflight(
        "plwc_write_reflection",
        {
            "profile": profile,
            "summary": summary,
            "evidence": evidence,
            "confidence": confidence,
            "marker": marker,
            "trust": trust,
            "candidate_for": candidate_for,
            "target": target,
            "entry_date": entry_date,
        },
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.write_reflection(
        _selected_profile(profile, loaded),
        summary=summary,
        evidence=evidence,
        confidence=confidence,
        marker=marker,
        trust=trust,
        candidate_for=candidate_for,
        target=target,
        entry_date=entry_date,
    )
    payload = _public_payload(result)
    audit_failure = _audit_public_result(
        "plwc_write_reflection",
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_reflection(
    operation: str = "",
    profile: str = "",
    summary: str = "",
    evidence: str = "",
    confidence: str = "",
    marker: str = "observation",
    trust: str = "",
    candidate_for: str = "",
    target: str = "",
    entry_date: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_operation = _normalize_dispatch_value(operation)
    if normalized_operation not in SUPPORTED_REFLECTION_OPERATIONS:
        payload = _dispatch_validation_failure(
            REFLECTION_TOOL,
            "operation",
            normalized_operation or str(operation),
            sorted(SUPPORTED_REFLECTION_OPERATIONS),
        )
        _audit_public_result(REFLECTION_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    preflight = _audit_preflight(
        REFLECTION_TOOL,
        {
            "operation": normalized_operation,
            "profile": profile,
            "summary": summary,
            "evidence": evidence,
            "confidence": confidence,
            "marker": marker,
            "trust": trust,
            "candidate_for": candidate_for,
            "target": target,
            "entry_date": entry_date,
        },
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.write_reflection(
        _selected_profile(profile, loaded),
        summary=summary,
        evidence=evidence,
        confidence=confidence,
        marker=marker,
        trust=trust,
        candidate_for=candidate_for,
        target=target,
        entry_date=entry_date,
    )
    payload = _public_payload(result)
    payload["facade"] = REFLECTION_TOOL
    payload["operation"] = normalized_operation
    audit_failure = _audit_public_result(
        REFLECTION_TOOL,
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_governor_plan(
    profile: str = "",
    force: bool = False,
    onboarding_answers: dict[str, Any] | None = None,
    plan_type: str = "",
    candidate_summary: str = "",
    evidence: str = "",
    trust: str = "",
    marker: str = "",
    confidence: str = "",
    entry_date: str = "",
    candidate_for: str = "",
    reason: str = "",
    target_section: str = "",
    conflicts_with: str = "",
    source_file: str = "",
    source_heading: str = "",
    source_sha256: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    # RC6-INNER Phase 3 — validate source provenance args when provided.
    # RC7-FIX-001: SHA optional at plan; the gateway returns the canonical SHA.
    provenance_error = _check_tagebuch_source_provenance_args(
        source_file, source_heading, source_sha256, require_sha=False
    )
    if provenance_error:
        payload = _source_provenance_failure("governor_plan", provenance_error)
        _audit_public_result("plwc_governor_plan", payload, config=loaded, audit_logger=audit_logger)
        return payload
    profile_adapter = adapter or _profile_adapter(loaded)
    merged_answers = _merge_promotion_parameters(
        onboarding_answers,
        plan_type=plan_type,
        candidate_summary=candidate_summary,
        evidence=evidence,
        trust=trust,
        marker=marker,
        confidence=confidence,
        entry_date=entry_date,
        candidate_for=candidate_for,
        reason=reason,
        target_section=target_section,
        conflicts_with=conflicts_with,
    )
    result = profile_adapter.governor_plan(
        _selected_governor_profile(profile, loaded, merged_answers, plan_type),
        force=force,
        onboarding_answers=merged_answers,
        plan_type=plan_type,
    )
    payload = _public_payload(result)
    # Attach source provenance to plan payload when provided (RC6-INNER Phase 3).
    # RC7-FIX-001: return the canonical SHA the gateway computes.
    if source_file:
        payload.setdefault("data", {})["source_provenance"] = _plan_source_provenance(
            source_file, source_heading, source_sha256, loaded
        )
    _audit_public_result("plwc_governor_plan", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_governor_apply(
    profile: str = "",
    force: bool = False,
    onboarding_answers: dict[str, Any] | None = None,
    confirmed: bool = False,
    plan_type: str = "",
    plan_id: str = "",
    candidate_summary: str = "",
    evidence: str = "",
    trust: str = "",
    marker: str = "",
    confidence: str = "",
    entry_date: str = "",
    candidate_for: str = "",
    reason: str = "",
    target_section: str = "",
    conflicts_with: str = "",
    source_file: str = "",
    source_heading: str = "",
    source_sha256: str = "",
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    # RC6-INNER Phase 3 — validate source provenance args when provided.
    provenance_error = _check_tagebuch_source_provenance_args(source_file, source_heading, source_sha256)
    if provenance_error:
        payload = _source_provenance_failure("governor_apply", provenance_error)
        _audit_public_result("plwc_governor_apply", payload, config=loaded, audit_logger=audit_logger)
        return payload
    # RC6-INNER Phase 3 — source integrity check at apply time when source provenance provided.
    if source_file:
        integrity_error = _check_source_integrity(source_file, source_heading, source_sha256, loaded)
        if integrity_error:
            payload = _source_provenance_failure("governor_apply", integrity_error)
            _audit_public_result("plwc_governor_apply", payload, config=loaded, audit_logger=audit_logger)
            return payload
    merged_answers = _merge_promotion_parameters(
        onboarding_answers,
        plan_type=plan_type,
        candidate_summary=candidate_summary,
        evidence=evidence,
        trust=trust,
        marker=marker,
        confidence=confidence,
        entry_date=entry_date,
        candidate_for=candidate_for,
        reason=reason,
        target_section=target_section,
        conflicts_with=conflicts_with,
    )
    preflight = _audit_preflight(
        "plwc_governor_apply",
        {
            "profile": profile,
            "force": force,
            "onboarding_answers": merged_answers,
            "confirmed": confirmed,
            "plan_type": plan_type,
            "plan_id": plan_id,
        },
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    profile_adapter = adapter or _profile_adapter(loaded)
    result = profile_adapter.governor_apply(
        _selected_governor_profile(profile, loaded, merged_answers, plan_type),
        force=force,
        onboarding_answers=merged_answers,
        confirmed=confirmed,
        plan_type=plan_type,
        plan_id=plan_id,
    )
    payload = _public_payload(result)
    audit_failure = _audit_public_result(
        "plwc_governor_apply",
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_governor(
    operation: str = "",
    profile: str = "",
    force: bool = False,
    onboarding_answers: dict[str, Any] | None = None,
    confirmed: bool = False,
    plan_type: str = "",
    plan_id: str = "",
    candidate_summary: str = "",
    evidence: str = "",
    trust: str = "",
    marker: str = "",
    confidence: str = "",
    entry_date: str = "",
    candidate_for: str = "",
    reason: str = "",
    target_section: str = "",
    conflicts_with: str = "",
    source_file: str = "",
    source_heading: str = "",
    source_sha256: str = "",
    target_file: str = "",
    heading: str = "",
    directive_id: str = "",
    dedup: bool = False,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: PBAProfileAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_operation = _normalize_dispatch_value(operation)
    if normalized_operation not in SUPPORTED_GOVERNOR_OPERATIONS:
        payload = _dispatch_validation_failure(
            GOVERNOR_TOOL,
            "operation",
            normalized_operation or str(operation),
            sorted(SUPPORTED_GOVERNOR_OPERATIONS),
        )
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    # RC6-INNER Phase 3 — validate source provenance args when provided.
    # RC7-FIX-001: SHA optional at plan (gateway returns canonical), required at apply.
    provenance_error = _check_tagebuch_source_provenance_args(
        source_file,
        source_heading,
        source_sha256,
        require_sha=(normalized_operation == "apply"),
    )
    if provenance_error:
        payload = _source_provenance_failure(f"governor_{normalized_operation}", provenance_error)
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    merged_answers = _merge_promotion_parameters(
        onboarding_answers,
        plan_type=plan_type,
        candidate_summary=candidate_summary,
        evidence=evidence,
        trust=trust,
        marker=marker,
        confidence=confidence,
        entry_date=entry_date,
        candidate_for=candidate_for,
        reason=reason,
        target_section=target_section,
        conflicts_with=conflicts_with,
    )
    profile_adapter = adapter or _profile_adapter(loaded)
    selected_profile = _selected_governor_profile(profile, loaded, merged_answers, plan_type)

    if normalized_operation in {"reindex", "drop_index"}:
        # RC8-FEAT-002 — explicit index maintenance. Writes/deletes derived data
        # only (never the canon); reconstructable; no watcher.
        if not _qdrant_enabled_for(loaded, selected_profile):
            payload = _qdrant_feature_disabled_payload(GOVERNOR_TOOL, normalized_operation)
        else:
            memory_path, storage_dir = _qdrant_paths(loaded, selected_profile)
            if normalized_operation == "reindex":
                payload = _bounded_qdrant_reindex(
                    profile=selected_profile, memory_path=memory_path, storage_dir=storage_dir
                )
            else:
                payload = _bounded_qdrant_drop_index(profile=selected_profile, storage_dir=storage_dir)
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    if normalized_operation == "list_retirable":
        result = profile_adapter.list_retirable(selected_profile, target_file=target_file)
        payload = _public_payload(result)
        payload["facade"] = GOVERNOR_TOOL
        payload["operation"] = normalized_operation
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    if normalized_operation == "retire":
        # confirmed retire is a governed write — gate it like apply.
        if confirmed:
            preflight = _audit_preflight(
                GOVERNOR_TOOL,
                {
                    "operation": normalized_operation,
                    "profile": profile,
                    "target_file": target_file,
                    "heading": heading,
                    "directive_id": directive_id,
                    "dedup": dedup,
                    "reason": reason,
                    "conflicts_with": conflicts_with,
                    "confirmed": confirmed,
                },
                config=loaded,
                audit_logger=audit_logger,
                high_risk=True,
            )
            if preflight is not None:
                return preflight
        result = profile_adapter.governor_retire(
            selected_profile,
            target_file=target_file,
            heading=heading,
            directive_id=directive_id,
            reason=reason,
            conflicts_with=conflicts_with,
            confirmed=confirmed,
            dedup=dedup,
        )
        payload = _public_payload(result)
        payload["facade"] = GOVERNOR_TOOL
        payload["operation"] = normalized_operation
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    if normalized_operation == "plan":
        result = profile_adapter.governor_plan(
            selected_profile,
            force=force,
            onboarding_answers=merged_answers,
            plan_type=plan_type,
        )
        payload = _public_payload(result)
        payload["facade"] = GOVERNOR_TOOL
        payload["operation"] = normalized_operation
        # RC7-FIX-001: return the canonical SHA the gateway computes at plan time.
        if source_file:
            payload.setdefault("data", {})["source_provenance"] = _plan_source_provenance(
                source_file, source_heading, source_sha256, loaded
            )
        _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
        return payload

    # RC6-INNER Phase 3 — source integrity check at apply time.
    if source_file:
        integrity_error = _check_source_integrity(source_file, source_heading, source_sha256, loaded)
        if integrity_error:
            payload = _source_provenance_failure("governor_apply", integrity_error)
            _audit_public_result(GOVERNOR_TOOL, payload, config=loaded, audit_logger=audit_logger)
            return payload

    preflight = _audit_preflight(
        GOVERNOR_TOOL,
        {
            "operation": normalized_operation,
            "profile": profile,
            "force": force,
            "onboarding_answers": merged_answers,
            "confirmed": confirmed,
            "plan_type": plan_type,
            "plan_id": plan_id,
        },
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    result = profile_adapter.governor_apply(
        selected_profile,
        force=force,
        onboarding_answers=merged_answers,
        confirmed=confirmed,
        plan_type=plan_type,
        plan_id=plan_id,
    )
    payload = _public_payload(result)
    payload["facade"] = GOVERNOR_TOOL
    payload["operation"] = normalized_operation
    audit_failure = _audit_public_result(
        GOVERNOR_TOOL,
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_sandbox_status(
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: DockerSandboxAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    sandbox = adapter or _sandbox_adapter(loaded)
    payload = _public_payload(sandbox.status())
    _audit_public_result("plwc_sandbox_status", payload, config=loaded, audit_logger=audit_logger)
    return payload


def plwc_run_python_sandboxed(
    code: str,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: DockerSandboxAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    preflight = _audit_preflight(
        "plwc_run_python_sandboxed",
        {"code": code},
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    sandbox = adapter or _sandbox_adapter(loaded)
    payload = _public_payload(sandbox.run_python(code))
    audit_failure = _audit_public_result(
        "plwc_run_python_sandboxed",
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_run_shell_sandboxed(
    command: str,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: DockerSandboxAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    preflight = _audit_preflight(
        "plwc_run_shell_sandboxed",
        {"command": command},
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    sandbox = adapter or _sandbox_adapter(loaded)
    payload = _public_payload(sandbox.run_shell(command))
    audit_failure = _audit_public_result(
        "plwc_run_shell_sandboxed",
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def plwc_sandbox_run(
    lang: str = "",
    code: str = "",
    timeout: int | None = None,
    *,
    config: GatewayConfig | None = None,
    audit_logger: AuditLogger | None = None,
    adapter: DockerSandboxAdapter | None = None,
) -> dict[str, Any]:
    loaded = _load_config(config)
    normalized_lang = _normalize_dispatch_value(lang)
    if normalized_lang not in SUPPORTED_SANDBOX_LANGS:
        payload = _dispatch_validation_failure(
            SANDBOX_RUN_TOOL,
            "lang",
            normalized_lang or str(lang),
            sorted(SUPPORTED_SANDBOX_LANGS),
        )
        _audit_public_result(SANDBOX_RUN_TOOL, payload, config=loaded, audit_logger=audit_logger, high_risk=True)
        return payload
    if not isinstance(code, str) or not code.strip():
        payload = _dispatch_validation_failure(
            SANDBOX_RUN_TOOL,
            "code",
            "<missing>",
            ["non-empty string"],
        )
        _audit_public_result(SANDBOX_RUN_TOOL, payload, config=loaded, audit_logger=audit_logger, high_risk=True)
        return payload
    if normalized_lang == "node":
        node_path_error = _validate_node_script_path(code.strip())
        if node_path_error:
            payload = {
                "ok": False,
                "operation": SANDBOX_RUN_TOOL,
                "policy_decision": "deny",
                "error": node_path_error,
                "error_category": "validation_error",
                "lang": "node",
                "requirement_ids": list(FACADE_REQUIREMENTS),
            }
            _audit_public_result(SANDBOX_RUN_TOOL, payload, config=loaded, audit_logger=audit_logger, high_risk=True)
            return payload
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1):
        payload = _dispatch_validation_failure(
            SANDBOX_RUN_TOOL,
            "timeout",
            timeout,
            ["positive integer"],
        )
        _audit_public_result(SANDBOX_RUN_TOOL, payload, config=loaded, audit_logger=audit_logger, high_risk=True)
        return payload

    preflight = _audit_preflight(
        SANDBOX_RUN_TOOL,
        {"lang": normalized_lang, "code": code, "timeout": timeout},
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    if preflight is not None:
        return preflight
    sandbox = adapter or _sandbox_adapter(loaded)
    if normalized_lang == "python":
        result = sandbox.run_python(code)
    elif normalized_lang == "shell":
        result = sandbox.run_shell(code)
    else:
        result = sandbox.run_node(code.strip())
    payload = _public_payload(result)
    payload["facade"] = SANDBOX_RUN_TOOL
    payload["lang"] = normalized_lang
    payload["requested_timeout_seconds"] = timeout
    payload["effective_timeout_seconds"] = loaded.docker.timeout_seconds
    # P1 timeout transparency (variant B): the requested timeout is intentionally
    # NOT plumbed into the sandbox runtime — sandbox behaviour is unchanged. Make
    # the actually-used value explicit instead of silently differing from the
    # request. (timeout is None or a positive int here, validated above.)
    timeout_clamped = timeout is not None and timeout > loaded.docker.timeout_seconds
    payload["timeout_clamped"] = timeout_clamped
    if timeout_clamped:
        payload["timeout_clamp_reason"] = "sandbox_config_limit"
    audit_failure = _audit_public_result(
        SANDBOX_RUN_TOOL,
        payload,
        config=loaded,
        audit_logger=audit_logger,
        high_risk=True,
    )
    return audit_failure or payload


def build_mcp_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("The mcp package is required to run plwc-gateway.") from exc

    mcp = FastMCP(PUBLIC_SERVER_NAME)

    # RC12-UX-004 — tools are async + offload the synchronous work to a worker
    # thread (anyio.to_thread.run_sync). FastMCP 1.27 runs sync tools INLINE on the
    # event loop (func_metadata.py: `return fn(**args)`), so a running tool would
    # block every other request — including a second session opened by a chat
    # switch — making the server "unresponsive". Offloading keeps the loop free.
    # run_sync is not cancellable here, so an in-flight write is never abandoned;
    # concurrent writes are serialized by the per-profile write lock (pba).
    @mcp.tool()
    async def plwc_status(scope: str = "") -> dict[str, Any]:
        """Report PLwC runtime, sandbox, first-run onboarding, or config status. Use scope="first_run" at Desktop startup and onboarding."""
        return await anyio.to_thread.run_sync(lambda: globals()["plwc_status"](scope))

    @mcp.tool()
    async def plwc_describe(scope: str = "tools", detail: str = "short", format: str = "json") -> dict[str, Any]:
        """Describe PLwC tools, schemas, dispatch operations, onboarding payloads, and safe plan/apply instructions."""
        return await anyio.to_thread.run_sync(lambda: globals()["plwc_describe"](scope, detail, format))

    @mcp.tool()
    async def plwc_profile(
        operation: str = "",
        profile: str = "",
        task_context: str = "",
        query: str = "",
        limit: int = 5,
        include_retired: bool = False,
        require_fresh: bool = False,
        min_dates: int = 2,
        compile_mode: str = DEFAULT_PROFILE_COMPILE_MODE,
        compile_max_chars: int = 0,
        doctor_mode: str = "clu",
        doctor_scope: str = "general",
        persona_layer: bool | None = None,
    ) -> dict[str, Any]:
        """Inspect, compile, retrieve, scan, or run read-only Doctor diagnostics for PLwC profiles through operation."""
        return await anyio.to_thread.run_sync(
            lambda: globals()["plwc_profile"](
                operation,
                profile,
                task_context,
                query,
                limit,
                include_retired,
                require_fresh,
                min_dates,
                compile_mode,
                compile_max_chars,
                doctor_mode,
                doctor_scope,
                persona_layer,
            ),
            abandon_on_cancel=True,
        )

    @mcp.tool()
    async def plwc_reflection(
        operation: str = "",
        profile: str = "",
        summary: str = "",
        evidence: str = "",
        confidence: str = "",
        marker: str = "observation",
        trust: str = "",
        candidate_for: str = "",
        target: str = "",
        entry_date: str = "",
    ) -> dict[str, Any]:
        """Write governed reflection entries with evidence validation; no direct protected profile-file writes."""
        return await anyio.to_thread.run_sync(
            lambda: globals()["plwc_reflection"](
                operation,
                profile,
                summary,
                evidence,
                confidence,
                marker,
                trust,
                candidate_for,
                target,
                entry_date,
            )
        )

    @mcp.tool()
    async def plwc_governor(
        operation: str = "",
        profile: str = "",
        force: bool = False,
        onboarding_answers: dict[str, Any] | None = None,
        confirmed: bool = False,
        plan_type: str = "",
        plan_id: str = "",
        candidate_summary: str = "",
        evidence: str = "",
        trust: str = "",
        marker: str = "",
        confidence: str = "",
        entry_date: str = "",
        candidate_for: str = "",
        reason: str = "",
        target_section: str = "",
        conflicts_with: str = "",
        source_file: str = "",
        source_heading: str = "",
        source_sha256: str = "",
        target_file: str = "",
        heading: str = "",
        directive_id: str = "",
        dedup: bool = False,
    ) -> dict[str, Any]:
        """Plan or apply governed profile changes, including plan_type=profile_creation onboarding; mutation requires confirmed=true."""
        abandon_on_cancel = _normalize_dispatch_value(operation) == "reindex"
        return await anyio.to_thread.run_sync(
            lambda: globals()["plwc_governor"](
                operation,
                profile,
                force,
                onboarding_answers,
                confirmed,
                plan_type,
                plan_id,
                candidate_summary,
                evidence,
                trust,
                marker,
                confidence,
                entry_date,
                candidate_for,
                reason,
                target_section,
                conflicts_with,
                source_file,
                source_heading,
                source_sha256,
                target_file,
                heading,
                directive_id,
                dedup,
            ),
            abandon_on_cancel=abandon_on_cancel,
        )

    @mcp.tool()
    async def plwc_sandbox_run(lang: str = "", code: str = "", timeout: int | None = None) -> dict[str, Any]:
        """Run bounded Python, shell, or Node code in the configured Docker sandbox; no host-shell fallback."""
        return await anyio.to_thread.run_sync(lambda: globals()["plwc_sandbox_run"](lang, code, timeout))

    @mcp.tool()
    async def plwc_workspace_operation(
        operation: str,
        path: str = "",
        content: str = "",
        content_base64: str = "",
        mode: str = "rewrite",
        depth: int = 1,
        query: str = "",
        max_results: int | None = None,
        source_path: str = "",
        target_path: str = "",
        paths: list[str] | None = None,
        old_text: str = "",
        new_text: str = "",
        expected_replacements: int | None = None,
        overwrite: bool = False,
        max_files: int | None = None,
        max_bytes_per_file: int | None = None,
        max_total_bytes: int | None = None,
        max_bytes: int | None = None,
        require_content_hash: str = "",
    ) -> dict[str, Any]:
        """Run governed workspace operations inside allowed roots. Use list with depth to discover filenames; search scans text contents only. Verify candidate paths with file_info before mutation."""
        # Forward by keyword to prevent positional drift if the public
        # function's signature is reordered (see RC2-BUG-W01 / C01).
        return await anyio.to_thread.run_sync(lambda: globals()["plwc_workspace_operation"](
            operation=operation,
            path=path,
            content=content,
            content_base64=content_base64,
            mode=mode,
            depth=depth,
            query=query,
            max_results=max_results,
            source_path=source_path,
            target_path=target_path,
            paths=paths,
            old_text=old_text,
            new_text=new_text,
            expected_replacements=expected_replacements,
            overwrite=overwrite,
            max_files=max_files,
            max_bytes_per_file=max_bytes_per_file,
            max_total_bytes=max_total_bytes,
            max_bytes=max_bytes,
            require_content_hash=require_content_hash,
        ))

    @mcp.tool()
    async def plwc_document_operation(
        operation: str,
        output_path: str = "",
        content: dict[str, Any] | None = None,
        overwrite: bool = False,
        input_path: str = "",
        input_paths: list[str] | None = None,
        output_dir: str = "",
        pages: list[int | str] | None = None,
        rotation: int | None = None,
        mode: str = "pages",
        format: str = "text",
        max_pages: int | None = None,
        max_chars: int | None = None,
        include_preview: bool = False,
        max_preview_chars: int | None = None,
        sheets: list[str | int] | None = None,
        ranges: dict[str, str] | list[str] | None = None,
        slides: list[int | str | dict[str, Any]] | None = None,
        title: str = "",
        include_notes: bool = False,
        max_rows: int | None = None,
        max_cells: int | None = None,
        max_size_kb: int | None = None,
        resize_to: str = "",
    ) -> Any:
        """Create and inspect governed DOCX, XLSX, PPTX, PDF, ZIP, image, and Office/OpenDocument artifacts."""
        payload = await anyio.to_thread.run_sync(lambda: globals()["plwc_document_operation"](
            operation,
            output_path,
            content,
            overwrite,
            input_path,
            input_paths,
            output_dir,
            pages,
            rotation,
            mode,
            format,
            max_pages,
            max_chars,
            include_preview,
            max_preview_chars,
            sheets,
            ranges,
            slides,
            title,
            include_notes,
            max_rows,
            max_cells,
            max_size_kb,
            resize_to,
        ))
        return _document_operation_mcp_response(payload)

    return mcp


def main() -> None:
    build_mcp_server().run()


def _normalize_workspace_operation(operation: Any) -> str:
    if not isinstance(operation, str):
        return ""
    normalized = operation.strip().casefold().replace("-", "_")
    return {"create_directory": "create_dir"}.get(normalized, normalized)


def _normalize_document_operation(operation: Any) -> str:
    if not isinstance(operation, str):
        return ""
    return operation.strip().casefold().replace("-", "_")


def _document_operation_effective_format(operation: str, output_format: Any) -> Any:
    if operation == "read_image" and output_format == "text":
        return "png"
    return output_format


def _normalize_describe_scope(scope: Any) -> str:
    if not isinstance(scope, str):
        return ""
    normalized = scope.strip().casefold().replace("-", "_")
    # RC12-DESC-001 (A) — resolve tool-name aliases (e.g. "workspace",
    # "plwc_profile") to the canonical scope; canonical names pass through.
    return _DESCRIBE_SCOPE_ALIASES.get(normalized, normalized)


def _normalize_dispatch_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().casefold().replace("-", "_")


def _validate_tagebuch_canonical_file_path(
    path: Any,
    *,
    operation: str,
    role: str = "path",
) -> dict[str, Any] | None:
    if not isinstance(path, str):
        return None
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts = [part for part in normalized.split("/") if part and part != "."]
    if len(parts) != 2 or parts[0].casefold() != "tagebuch":
        return None
    filename = parts[1]
    if TAGEBUCH_CANONICAL_FILENAME_RE.match(filename):
        return None
    suffix_match = TAGEBUCH_SUFFIX_FILENAME_RE.match(filename)
    if suffix_match is None:
        return None
    canonical_path = f"Tagebuch/{suffix_match.group('date')}.md"
    payload = _workspace_operation_failure(
        operation,
        (
            "Tagebuch entries for one date must be appended to the canonical "
            f"{canonical_path} file; date-suffix files are not supported."
        ),
        ("FR-INNER-001..012", RC17_TAGEBUCH_CANONICAL_REQUIREMENT_ID, "NFR-002"),
        path=path if role == "path" else None,
        source_path=path if role == "source_path" else None,
        target_path=path if role == "target_path" else None,
        error_category="tagebuch_canonical_path_required",
    )
    payload.update(
        {
            "canonical_path": canonical_path,
            "attempted_path": path,
            "next_action": (
                f"Call plwc_workspace_operation(operation='write', path='{canonical_path}', "
                "mode='append', content=...)."
            ),
        }
    )
    return payload


def _validate_workspace_operation(
    *,
    operation: Any,
    normalized_operation: str,
    path: Any,
    content: Any,
    content_base64: Any,
    mode: Any,
    depth: Any,
    query: Any,
    max_results: Any,
    source_path: Any,
    target_path: Any,
    paths: Any,
    old_text: Any,
    new_text: Any,
    expected_replacements: Any,
    overwrite: Any,
    max_files: Any,
    max_bytes_per_file: Any,
    max_total_bytes: Any,
    max_bytes: Any,
    require_content_hash: Any,
) -> dict[str, Any] | None:
    if not isinstance(operation, str) or not normalized_operation:
        return _workspace_operation_failure(
            "invalid",
            "Workspace operation is required.",
            ("FR-CMD-PUB-002", "NFR-002"),
            error_category="validation_error",
        )
    if normalized_operation in DELETE_LIKE_WORKSPACE_OPERATIONS:
        return _workspace_operation_failure(
            normalized_operation,
            "Delete-style workspace operations are not supported.",
            ("FR-CMD-PUB-004", "NFR-002"),
            error_category="unsupported_operation",
        )
    if normalized_operation not in SUPPORTED_WORKSPACE_OPERATIONS:
        return _workspace_operation_failure(
            normalized_operation,
            "Unsupported workspace operation.",
            ("FR-CMD-PUB-002", "NFR-002"),
            error_category="unsupported_operation",
        )

    if normalized_operation in {
        "list",
        "search",
        "read",
        "write",
        "file_info",
        "create_dir",
        "exact_replace",
        "read_binary",
        "write_binary",
    }:
        path_error = _validate_workspace_path(path, normalized_operation, role="path")
        if path_error is not None:
            return path_error
    if normalized_operation == "list":
        if isinstance(depth, bool) or not isinstance(depth, int):
            return _workspace_operation_failure(
                normalized_operation,
                "depth must be a positive integer.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if depth < 1:
            return _workspace_operation_failure(
                normalized_operation,
                "depth must be at least 1.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
    if normalized_operation == "search":
        if not isinstance(query, str) or not query:
            return _workspace_operation_failure(
                normalized_operation,
                "query must be a non-empty string.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        max_results_error = _validate_optional_positive_int(normalized_operation, "max_results", max_results)
        if max_results_error is not None:
            return max_results_error
    if normalized_operation == "write":
        if not isinstance(content, str):
            return _workspace_operation_failure(
                normalized_operation,
                "content must be a string.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if not isinstance(mode, str) or mode.strip().casefold() not in {"rewrite", "append"}:
            return _workspace_operation_failure(
                normalized_operation,
                "mode must be rewrite or append.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        tagebuch_error = _validate_tagebuch_canonical_file_path(path, operation=normalized_operation)
        if tagebuch_error is not None:
            return tagebuch_error
        if isinstance(source_path, str) and source_path.strip():
            return _workspace_operation_failure(
                normalized_operation,
                "write does not support source_path. Use operation='copy' for file-to-file copy or operation='write_binary' for base64 binary payloads.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
    if normalized_operation in {"move", "rename"}:
        source_error = _validate_workspace_path(source_path, normalized_operation, role="source_path")
        if source_error is not None:
            return source_error
        target_error = _validate_workspace_path(target_path, normalized_operation, role="target_path")
        if target_error is not None:
            return target_error
        tagebuch_target_error = _validate_tagebuch_canonical_file_path(
            target_path,
            operation=normalized_operation,
            role="target_path",
        )
        if tagebuch_target_error is not None:
            return tagebuch_target_error
        if not isinstance(overwrite, bool):
            return _workspace_operation_failure(
                normalized_operation,
                "overwrite must be a boolean.",
                ("FR-CMD-PUB-002", "NFR-002"),
                source_path=source_path,
                target_path=target_path,
                error_category="validation_error",
            )
        if overwrite:
            return _workspace_operation_failure(
                normalized_operation,
                "Public move/rename overwrite is not supported.",
                ("FR-CMD-PUB-005", "NFR-002"),
                source_path=source_path,
                target_path=target_path,
                error_category="overwrite_not_supported",
            )
    if normalized_operation == "copy":
        source_error = _validate_workspace_path(source_path, normalized_operation, role="source_path")
        if source_error is not None:
            return source_error
        target_error = _validate_workspace_path(target_path, normalized_operation, role="target_path")
        if target_error is not None:
            return target_error
        tagebuch_target_error = _validate_tagebuch_canonical_file_path(
            target_path,
            operation=normalized_operation,
            role="target_path",
        )
        if tagebuch_target_error is not None:
            return tagebuch_target_error
        if not isinstance(overwrite, bool):
            return _workspace_operation_failure(
                normalized_operation,
                "overwrite must be a boolean.",
                ("FR-CMD-PUB-002", "NFR-002"),
                source_path=source_path,
                target_path=target_path,
                error_category="validation_error",
            )
        if overwrite:
            return _workspace_operation_failure(
                normalized_operation,
                "Public copy overwrite is not supported.",
                ("FR-CMD-PUB-005", "NFR-002"),
                source_path=source_path,
                target_path=target_path,
                error_category="overwrite_not_supported",
            )
        max_bytes_error = _validate_optional_positive_int(normalized_operation, "max_bytes", max_bytes)
        if max_bytes_error is not None:
            return max_bytes_error
    if normalized_operation == "read_binary":
        max_bytes_error = _validate_optional_positive_int(normalized_operation, "max_bytes", max_bytes)
        if max_bytes_error is not None:
            return max_bytes_error
    if normalized_operation == "write_binary":
        if not isinstance(content_base64, str) or not content_base64:
            return _workspace_operation_failure(
                normalized_operation,
                "content_base64 must be a non-empty base64 string.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if not isinstance(mode, str) or mode.strip().casefold() not in {"rewrite", "append"}:
            return _workspace_operation_failure(
                normalized_operation,
                "mode must be rewrite or append.",
                ("FR-CMD-PUB-002", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        tagebuch_error = _validate_tagebuch_canonical_file_path(path, operation=normalized_operation)
        if tagebuch_error is not None:
            return tagebuch_error
        max_bytes_error = _validate_optional_positive_int(normalized_operation, "max_bytes", max_bytes)
        if max_bytes_error is not None:
            return max_bytes_error
    if normalized_operation == "batch_read":
        if not isinstance(paths, list) or not paths:
            return _workspace_operation_failure(
                normalized_operation,
                "paths must be a non-empty list of workspace paths.",
                ("FR-CMD-PUB-002", "NFR-002"),
                error_category="validation_error",
            )
        for item in paths:
            path_error = _validate_workspace_path(item, normalized_operation, role="path")
            if path_error is not None:
                return path_error
        for field_name, value in {
            "max_files": max_files,
            "max_bytes_per_file": max_bytes_per_file,
            "max_total_bytes": max_total_bytes,
        }.items():
            limit_error = _validate_optional_positive_int(normalized_operation, field_name, value)
            if limit_error is not None:
                return limit_error
    if normalized_operation == "exact_replace":
        if not isinstance(old_text, str) or not old_text:
            return _workspace_operation_failure(
                normalized_operation,
                "old_text must be a non-empty string.",
                ("FR-CMD-PUB-002", "FR-CMD-PUB-007", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if not isinstance(new_text, str):
            return _workspace_operation_failure(
                normalized_operation,
                "new_text must be a string.",
                ("FR-CMD-PUB-002", "FR-CMD-PUB-007", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if isinstance(expected_replacements, bool) or not isinstance(expected_replacements, int):
            return _workspace_operation_failure(
                normalized_operation,
                "expected_replacements must be an integer.",
                ("FR-CMD-PUB-002", "FR-CMD-PUB-007", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if expected_replacements < 1:
            return _workspace_operation_failure(
                normalized_operation,
                "expected_replacements must be at least 1.",
                ("FR-CMD-PUB-002", "FR-CMD-PUB-007", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
        if not isinstance(require_content_hash, str):
            return _workspace_operation_failure(
                normalized_operation,
                "require_content_hash must be a string when provided.",
                ("FR-CMD-PUB-002", "FR-CMD-PUB-007", "NFR-002"),
                path=path,
                error_category="validation_error",
            )
    return None


def _str_or_empty(value: Any) -> str:
    """Return value if it is a string, else an empty string.

    Replaces the repeated ``value if isinstance(value, str) else ""`` pattern.
    (RC2-HYGIENE-002)"""
    return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class _DocumentValidationRequest:
    """Immutable carrier for the per-operation document validation parameters.

    RC4-HYGIENE-001: bundles the keyword arguments that the individual
    operation validators need so the dispatch table can call every handler with
    a uniform signature. Behaviour is identical to the previous inline if-tree;
    each handler body is the verbatim former branch.
    """

    normalized_operation: str
    output_path: Any
    input_path: Any
    input_paths: Any
    output_dir: Any
    pages: Any
    rotation: Any
    mode: Any
    output_format: Any
    max_pages: Any
    max_chars: Any
    include_preview: Any
    max_preview_chars: Any
    sheets: Any
    ranges: Any
    slides: Any
    title: Any
    include_notes: Any
    max_rows: Any
    max_cells: Any
    max_size_kb: Any
    resize_to: Any
    content: Any


def _validate_document_create_operation(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    content = req.content
    output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=DOCUMENT_OPERATION_EXTENSIONS[normalized_operation])
    if output_error is not None:
        return output_error
    if normalized_operation == "create_docx":
        return _validate_create_docx_contract(content, input_path, _str_or_empty(output_path))
    if normalized_operation == "create_xlsx":
        return _validate_create_xlsx_contract(content, input_path, _str_or_empty(output_path))
    if normalized_operation == "create_pptx":
        return _validate_create_pptx_contract(content, input_path, _str_or_empty(output_path))
    if normalized_operation == "create_pdf":
        return _validate_create_pdf_contract(content, input_path, _str_or_empty(output_path))
    if input_path:
        return _document_operation_failure(
            normalized_operation,
            f"{normalized_operation} does not support input_path in this slice.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    content_error = _validate_document_content(normalized_operation, content)
    if content_error is not None:
        return _document_operation_failure(
            normalized_operation,
            content_error,
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    return None


def _validate_document_edit_docx(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    output_path = req.output_path
    input_path = req.input_path
    content = req.content
    if not isinstance(content, dict):
        return _document_operation_failure(
            "edit_docx",
            "edit_docx content must be an object.",
            ("FR-DOCX-EDIT-001", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    input_error = _validate_document_path_field("edit_docx", input_path, field_name="input_path", expected_suffix=".docx")
    if input_error is not None:
        return input_error
    output_error = _validate_document_path_field("edit_docx", output_path, field_name="output_path", expected_suffix=".docx")
    if output_error is not None:
        return output_error
    return _validate_edit_docx_contract(content, _str_or_empty(output_path))


def _validate_document_inspect_pdf(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    input_path = req.input_path
    return _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".pdf")


def _validate_document_inspect_zip(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    input_path = req.input_path
    return _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".zip")


def _validate_document_merge_pdf(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_paths = req.input_paths
    if not isinstance(input_paths, list) or len(input_paths) < 2:
        return _document_operation_failure(
            normalized_operation,
            "input_paths must contain at least two PDF paths.",
            ("FR-PDF-MVP-003", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    if len(input_paths) > PDF_MAX_INPUT_FILES:
        return _document_operation_failure(
            normalized_operation,
            f"merge_pdf supports at most {PDF_MAX_INPUT_FILES} input PDFs.",
            ("FR-PDF-MVP-003", "FR-PDF-MVP-011", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="limit_exceeded",
        )
    for item in input_paths:
        input_error = _validate_document_path_field(normalized_operation, item, field_name="input_path", expected_suffix=".pdf")
        if input_error is not None:
            return input_error
    return _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".pdf")


def _validate_document_split_pdf(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    input_path = req.input_path
    output_dir = req.output_dir
    mode = req.mode
    if mode != "pages":
        return _document_operation_failure(
            normalized_operation,
            "split_pdf currently supports mode=pages only.",
            ("FR-PDF-MVP-004", "NFR-002"),
            output_path=_str_or_empty(output_dir),
            error_category="unsupported_mode",
        )
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".pdf")
    if input_error is not None:
        return input_error
    return _validate_document_dir_field(normalized_operation, output_dir, field_name="output_dir")


def _validate_document_extract_zip(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    input_path = req.input_path
    output_dir = req.output_dir
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".zip")
    if input_error is not None:
        return input_error
    return _validate_document_dir_field(normalized_operation, output_dir, field_name="output_dir")


def _validate_document_create_zip(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    input_paths = req.input_paths
    output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".zip")
    if output_error is not None:
        return output_error
    has_input_path = isinstance(input_path, str) and bool(input_path.strip())
    has_input_paths = isinstance(input_paths, list) and bool(input_paths)
    if not has_input_path and not has_input_paths:
        return _document_operation_failure(
            normalized_operation,
            "create_zip requires input_path or input_paths.",
            ("FR-ARCH-MVP-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if input_paths is not None and not isinstance(input_paths, list):
        return _document_operation_failure(
            normalized_operation,
            "input_paths must be a list of workspace paths.",
            ("FR-ARCH-MVP-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if has_input_path:
        source_error = _validate_document_source_field(normalized_operation, input_path, field_name="input_path")
        if source_error is not None:
            return source_error
    for item in input_paths or []:
        source_error = _validate_document_source_field(normalized_operation, item, field_name="input_paths")
        if source_error is not None:
            return source_error
    return None


def _validate_document_read_image(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    input_path = req.input_path
    output_format = req.output_format
    max_size_kb = req.max_size_kb
    resize_to = req.resize_to
    input_error = _validate_read_image_path(input_path)
    if input_error is not None:
        return input_error
    if not isinstance(output_format, str) or output_format.strip().casefold() not in READ_IMAGE_OUTPUT_FORMATS:
        return _document_operation_failure(
            normalized_operation,
            "read_image format must be png, jpeg or webp.",
            ("FR-IMG-001", "NFR-002"),
            error_category="validation_error",
        )
    if max_size_kb is not None:
        if isinstance(max_size_kb, bool) or not isinstance(max_size_kb, int) or max_size_kb < 1:
            return _document_operation_failure(
                normalized_operation,
                "max_size_kb must be a positive integer.",
                ("FR-IMG-002", "NFR-002"),
                error_category="validation_error",
            )
        if max_size_kb > READ_IMAGE_HARD_MAX_SIZE_KB:
            return _document_operation_failure(
                normalized_operation,
                f"max_size_kb must not exceed {READ_IMAGE_HARD_MAX_SIZE_KB}.",
                ("FR-IMG-002", "NFR-002"),
                error_category="limit_exceeded",
            )
    if not isinstance(resize_to, str):
        return _document_operation_failure(
            normalized_operation,
            "resize_to must be a string.",
            ("FR-IMG-003", "NFR-002"),
            error_category="validation_error",
        )
    if resize_to and not _valid_read_image_resize_to(resize_to):
        return _document_operation_failure(
            normalized_operation,
            "resize_to must be WIDTHxHEIGHT or N%.",
            ("FR-IMG-003", "NFR-002"),
            error_category="validation_error",
        )
    return None


def _validate_document_extract_pdf(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    pages = req.pages
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".pdf")
    if input_error is not None:
        return input_error
    output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".pdf")
    if output_error is not None:
        return output_error
    page_error = _validate_document_pages(normalized_operation, pages, require_non_empty=True)
    if page_error is not None:
        return page_error
    if _document_page_selector_count(pages or []) > PDF_MAX_EXTRACT_OUTPUT_PAGES:
        return _document_operation_failure(
            normalized_operation,
            f"extract_pdf supports at most {PDF_MAX_EXTRACT_OUTPUT_PAGES} output pages.",
            ("FR-PDF-MVP-005", "FR-PDF-MVP-011", "NFR-002"),
            output_path=output_path,
            error_category="limit_exceeded",
        )
    return None


def _validate_document_rotate_pdf(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    pages = req.pages
    rotation = req.rotation
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".pdf")
    if input_error is not None:
        return input_error
    output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".pdf")
    if output_error is not None:
        return output_error
    if isinstance(rotation, bool) or rotation not in {90, 180, 270}:
        return _document_operation_failure(
            normalized_operation,
            "rotation must be 90, 180 or 270.",
            ("FR-PDF-MVP-006", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    page_error = _validate_document_pages(normalized_operation, pages or [], require_non_empty=False)
    if page_error is not None:
        return page_error
    if pages and _document_page_selector_count(pages) > PDF_MAX_ROTATE_SELECTED_PAGES:
        return _document_operation_failure(
            normalized_operation,
            f"rotate_pdf supports at most {PDF_MAX_ROTATE_SELECTED_PAGES} selected affected pages.",
            ("FR-PDF-MVP-006", "FR-PDF-MVP-011", "NFR-002"),
            output_path=output_path,
            error_category="limit_exceeded",
        )
    return None


def _validate_document_extract_pdf_text(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    pages = req.pages
    output_format = req.output_format
    max_pages = req.max_pages
    max_chars = req.max_chars
    include_preview = req.include_preview
    max_preview_chars = req.max_preview_chars
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=".pdf")
    if input_error is not None:
        return input_error
    if not isinstance(output_format, str) or output_format not in {"text", "json"}:
        return _document_operation_failure(
            normalized_operation,
            "extract_pdf_text format must be text or json.",
            ("FR-PDF-TEXT-001", "FR-PDF-TEXT-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    if output_path:
        expected_suffix = ".txt" if output_format == "text" else ".json"
        output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=expected_suffix)
        if output_error is not None:
            return output_error
    page_error = _validate_document_pages(normalized_operation, pages or [], require_non_empty=False)
    if page_error is not None:
        return page_error
    selected_page_count = _document_page_selector_count(pages or [])
    for field_name, value, upper_bound in (
        ("max_pages", max_pages, PDF_TEXT_MAX_PAGES),
        ("max_chars", max_chars, PDF_TEXT_MAX_CHARS),
        ("max_preview_chars", max_preview_chars, PDF_TEXT_MAX_PREVIEW_CHARS),
    ):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return _document_operation_failure(
                normalized_operation,
                f"{field_name} must be a positive integer.",
                ("FR-PDF-TEXT-001", "FR-PDF-TEXT-004", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="validation_error",
            )
        if value > upper_bound:
            return _document_operation_failure(
                normalized_operation,
                f"{field_name} must not exceed {upper_bound}.",
                ("FR-PDF-TEXT-001", "FR-PDF-TEXT-004", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="limit_exceeded",
            )
    effective_max_pages = max_pages if max_pages is not None else PDF_TEXT_MAX_PAGES
    if selected_page_count > effective_max_pages:
        return _document_operation_failure(
            normalized_operation,
            f"extract_pdf_text supports at most {effective_max_pages} selected pages.",
            ("FR-PDF-TEXT-001", "FR-PDF-TEXT-004", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="limit_exceeded",
        )
    if not isinstance(include_preview, bool):
        return _document_operation_failure(
            normalized_operation,
            "include_preview must be a boolean.",
            ("FR-PDF-TEXT-001", "FR-PDF-TEXT-004", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    return None


def _validate_document_office_operation(req: "_DocumentValidationRequest") -> dict[str, Any] | None:
    normalized_operation = req.normalized_operation
    output_path = req.output_path
    input_path = req.input_path
    output_format = req.output_format
    max_chars = req.max_chars
    include_preview = req.include_preview
    max_preview_chars = req.max_preview_chars
    sheets = req.sheets
    ranges = req.ranges
    slides = req.slides
    include_notes = req.include_notes
    max_rows = req.max_rows
    max_cells = req.max_cells
    expected_suffix = DOCUMENT_OPERATION_EXTENSIONS[normalized_operation]
    input_error = _validate_document_path_field(normalized_operation, input_path, field_name="input_path", expected_suffix=expected_suffix)
    if input_error is not None:
        return input_error
    if normalized_operation.startswith("inspect_"):
        return None
    if normalized_operation in {"extract_docx_text", "extract_odt_text"}:
        if not isinstance(output_format, str) or output_format not in {"text", "json"}:
            return _document_operation_failure(
                normalized_operation,
                f"{normalized_operation} format must be text or json.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="validation_error",
            )
        if output_path:
            expected_output_suffix = ".txt" if output_format == "text" else ".json"
            output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=expected_output_suffix)
            if output_error is not None:
                return output_error
    elif normalized_operation in {"extract_pptx_text", "extract_odp_text"}:
        if output_path:
            output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".txt")
            if output_error is not None:
                return output_error
        page_error = _validate_document_pages(normalized_operation, slides or [], require_non_empty=False)
        if page_error is not None:
            return page_error
        if slides and _document_page_selector_count(slides) > OFFICE_MAX_PPTX_SLIDES:
            return _document_operation_failure(
                normalized_operation,
                f"{normalized_operation} supports at most {OFFICE_MAX_PPTX_SLIDES} selected slides/pages.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="limit_exceeded",
            )
    elif normalized_operation in {"extract_xlsx_data", "extract_ods_data"}:
        if output_path:
            output_error = _validate_document_path_field(normalized_operation, output_path, field_name="output_path", expected_suffix=".json")
            if output_error is not None:
                return output_error
        if sheets is not None and (
            not isinstance(sheets, list)
            or any(isinstance(item, bool) or not isinstance(item, (str, int)) for item in sheets)
        ):
            return _document_operation_failure(
                normalized_operation,
                "sheets must be a list of sheet names or 1-based indexes.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="validation_error",
            )
        if ranges is not None and not isinstance(ranges, (dict, list)):
            return _document_operation_failure(
                normalized_operation,
                "ranges must be an object or list.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="validation_error",
            )
    for field_name, value, upper_bound in (
        ("max_chars", max_chars, OFFICE_MAX_TEXT_CHARS),
        ("max_preview_chars", max_preview_chars, OFFICE_MAX_PREVIEW_CHARS),
        ("max_rows", max_rows, OFFICE_MAX_XLSX_ROWS),
        ("max_cells", max_cells, OFFICE_MAX_XLSX_CELLS),
    ):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return _document_operation_failure(
                normalized_operation,
                f"{field_name} must be a positive integer.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="validation_error",
            )
        if value > upper_bound:
            return _document_operation_failure(
                normalized_operation,
                f"{field_name} must not exceed {upper_bound}.",
                ("FR-OFFICE-MVP-002", "NFR-002"),
                output_path=_str_or_empty(output_path),
                error_category="limit_exceeded",
            )
    if not isinstance(include_preview, bool) or not isinstance(include_notes, bool):
        return _document_operation_failure(
            normalized_operation,
            "include_preview and include_notes must be booleans.",
            ("FR-OFFICE-MVP-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    return None


def _build_document_operation_validators() -> dict[str, Any]:
    validators: dict[str, Any] = {
        "edit_docx": _validate_document_edit_docx,
        "inspect_pdf": _validate_document_inspect_pdf,
        "inspect_zip": _validate_document_inspect_zip,
        "merge_pdf": _validate_document_merge_pdf,
        "split_pdf": _validate_document_split_pdf,
        "extract_zip": _validate_document_extract_zip,
        "create_zip": _validate_document_create_zip,
        "read_image": _validate_document_read_image,
        "extract_pdf": _validate_document_extract_pdf,
        "rotate_pdf": _validate_document_rotate_pdf,
        "extract_pdf_text": _validate_document_extract_pdf_text,
    }
    for operation in SUPPORTED_DOCUMENT_CREATE_OPERATIONS:
        validators[operation] = _validate_document_create_operation
    for operation in SUPPORTED_DOCUMENT_OFFICE_OPERATIONS:
        validators[operation] = _validate_document_office_operation
    return validators


_DOCUMENT_OPERATION_VALIDATORS = _build_document_operation_validators()


def _validate_document_operation(
    *,
    operation: Any,
    normalized_operation: str,
    output_path: Any,
    input_path: Any,
    input_paths: Any,
    output_dir: Any,
    pages: Any,
    rotation: Any,
    mode: Any,
    output_format: Any,
    max_pages: Any,
    max_chars: Any,
    include_preview: Any,
    max_preview_chars: Any,
    sheets: Any,
    ranges: Any,
    slides: Any,
    title: Any,
    include_notes: Any,
    max_rows: Any,
    max_cells: Any,
    max_size_kb: Any,
    resize_to: Any,
    content: Any,
    overwrite: Any,
) -> dict[str, Any] | None:
    if not isinstance(operation, str) or not normalized_operation:
        return _document_operation_failure(
            "invalid",
            "Document operation is required.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    if normalized_operation in UNSUPPORTED_DOCUMENT_OPERATION_NAMES or normalized_operation not in SUPPORTED_DOCUMENT_OPERATIONS:
        return _document_operation_failure(
            normalized_operation,
            "Unsupported document operation.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="unsupported_operation",
        )
    if normalized_operation in SUPPORTED_DOCUMENT_CREATE_OPERATIONS and not isinstance(content, dict):
        return _document_operation_failure(
            normalized_operation,
            "content must be an object.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=_str_or_empty(output_path),
            error_category="validation_error",
        )
    if not isinstance(overwrite, bool):
        return _document_operation_failure(
            normalized_operation,
            "overwrite must be a boolean.",
            ("FR-DOC-PUB-002", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if overwrite:
        return _document_operation_failure(
            normalized_operation,
            "Public document overwrite is not supported in this slice.",
            ("FR-DOC-PUB-006", "NFR-002"),
            output_path=output_path,
            error_category="overwrite_not_supported",
        )
    handler = _DOCUMENT_OPERATION_VALIDATORS.get(normalized_operation)
    if handler is None:
        return None
    request = _DocumentValidationRequest(
        normalized_operation=normalized_operation,
        output_path=output_path,
        input_path=input_path,
        input_paths=input_paths,
        output_dir=output_dir,
        pages=pages,
        rotation=rotation,
        mode=mode,
        output_format=output_format,
        max_pages=max_pages,
        max_chars=max_chars,
        include_preview=include_preview,
        max_preview_chars=max_preview_chars,
        sheets=sheets,
        ranges=ranges,
        slides=slides,
        title=title,
        include_notes=include_notes,
        max_rows=max_rows,
        max_cells=max_cells,
        max_size_kb=max_size_kb,
        resize_to=resize_to,
        content=content,
    )
    return handler(request)


def _validate_document_path_field(
    operation: str,
    value: Any,
    *,
    field_name: str,
    expected_suffix: str,
) -> dict[str, Any] | None:
    output_path = _str_or_empty(value)
    if not isinstance(value, str) or not value.strip():
        return _document_operation_failure(
            operation,
            f"{field_name} is required.",
            ("FR-DOC-PUB-005", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if Path(value).is_absolute():
        return _document_operation_failure(
            operation,
            f"{field_name} must be a relative workspace path.",
            ("FR-DOC-PUB-005", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="absolute_path_rejected",
        )
    if _is_public_workspace_protected_path(value):
        return _document_operation_failure(
            operation,
            "Document operations cannot target profile or governance paths.",
            ("FR-DOC-PUB-005", "FR-PDF-MVP-009", "SR-004", "NFR-002"),
            output_path=output_path,
            error_category="protected_path_rejected",
        )
    if ".." in value.replace("\\", "/").split("/"):
        return _document_operation_failure(
            operation,
            f"{field_name} must not contain parent traversal.",
            ("FR-DOC-PUB-005", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="path_traversal_rejected",
        )
    if Path(value).suffix.casefold() != expected_suffix:
        return _document_operation_failure(
            operation,
            f"{operation} requires a {expected_suffix} path for {field_name}.",
            ("FR-DOC-PUB-005", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="unsupported_extension",
        )
    return None


def _validate_read_image_path(value: Any) -> dict[str, Any] | None:
    output_path = _str_or_empty(value)
    if not isinstance(value, str) or not value.strip():
        return _document_operation_failure(
            "read_image",
            "input_path is required.",
            ("FR-IMG-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if _looks_like_external_url(value):
        return _document_operation_failure(
            "read_image",
            "External URLs are not allowed for read_image input_path.",
            ("FR-IMG-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
            extra={"error": "external_url_forbidden"},
        )
    if Path(value).is_absolute():
        return _document_operation_failure(
            "read_image",
            "input_path must be a relative workspace path.",
            ("FR-IMG-001", "NFR-002"),
            output_path=output_path,
            error_category="absolute_path_rejected",
        )
    if _is_public_workspace_protected_path(value):
        return _document_operation_failure(
            "read_image",
            "Document operations cannot target profile or governance paths.",
            ("FR-IMG-001", "SR-004", "NFR-002"),
            output_path=output_path,
            error_category="protected_path_rejected",
        )
    if ".." in value.replace("\\", "/").split("/"):
        return _document_operation_failure(
            "read_image",
            "path_traversal_denied",
            ("FR-IMG-001", "NFR-002"),
            output_path=output_path,
            error_category="path_traversal_denied",
        )
    detected_extension = Path(value).suffix.casefold()
    if detected_extension not in READ_IMAGE_SUPPORTED_INPUT_SUFFIXES:
        return _document_operation_failure(
            "read_image",
            "unsupported_format",
            ("FR-IMG-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
            extra={
                "detected_extension": detected_extension,
                "supported_formats": list(READ_IMAGE_SUPPORTED_INPUT_FORMATS),
            },
        )
    return None


def _validate_document_dir_field(operation: str, value: Any, *, field_name: str) -> dict[str, Any] | None:
    output_path = _str_or_empty(value)
    if not isinstance(value, str) or not value.strip():
        return _document_operation_failure(
            operation,
            f"{field_name} is required.",
            ("FR-PDF-MVP-004", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if Path(value).is_absolute():
        return _document_operation_failure(
            operation,
            f"{field_name} must be a relative workspace path.",
            ("FR-PDF-MVP-004", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="absolute_path_rejected",
        )
    if _is_public_workspace_protected_path(value):
        return _document_operation_failure(
            operation,
            "Document operations cannot target profile or governance paths.",
            ("FR-PDF-MVP-004", "FR-PDF-MVP-009", "SR-004", "NFR-002"),
            output_path=output_path,
            error_category="protected_path_rejected",
        )
    if ".." in value.replace("\\", "/").split("/"):
        return _document_operation_failure(
            operation,
            f"{field_name} must not contain parent traversal.",
            ("FR-PDF-MVP-004", "FR-PDF-MVP-009", "NFR-002"),
            output_path=output_path,
            error_category="path_traversal_rejected",
        )
    return None


def _validate_document_source_field(operation: str, value: Any, *, field_name: str) -> dict[str, Any] | None:
    output_path = _str_or_empty(value)
    if not isinstance(value, str) or not value.strip():
        return _document_operation_failure(
            operation,
            f"{field_name} must be a non-empty relative workspace path.",
            ("FR-ARCH-MVP-001", "NFR-002"),
            output_path=output_path,
            error_category="validation_error",
        )
    if Path(value).is_absolute():
        return _document_operation_failure(
            operation,
            f"{field_name} must be a relative workspace path.",
            ("FR-ARCH-MVP-001", "NFR-002"),
            output_path=output_path,
            error_category="absolute_path_rejected",
        )
    if _is_public_workspace_protected_path(value):
        return _document_operation_failure(
            operation,
            "Document operations cannot target profile or governance paths.",
            ("FR-ARCH-MVP-001", "SR-004", "NFR-002"),
            output_path=output_path,
            error_category="protected_path_rejected",
        )
    if ".." in value.replace("\\", "/").split("/"):
        return _document_operation_failure(
            operation,
            f"{field_name} must not contain parent traversal.",
            ("FR-ARCH-MVP-001", "NFR-002"),
            output_path=output_path,
            error_category="path_traversal_rejected",
        )
    return None


def _validate_document_pages(operation: str, pages: Any, *, require_non_empty: bool) -> dict[str, Any] | None:
    if pages is None:
        pages = []
    if not isinstance(pages, list):
        return _document_operation_failure(
            operation,
            "pages must be a list of 1-based page numbers or ranges.",
            ("FR-PDF-MVP-005", "FR-PDF-MVP-006", "NFR-002"),
            error_category="validation_error",
        )
    if require_non_empty and not pages:
        return _document_operation_failure(
            operation,
            "pages must be a non-empty list.",
            ("FR-PDF-MVP-005", "NFR-002"),
            error_category="validation_error",
        )
    for item in pages:
        if isinstance(item, bool):
            return _invalid_document_page(operation)
        if isinstance(item, int):
            if item < 1:
                return _invalid_document_page(operation)
            continue
        if isinstance(item, str):
            stripped = item.strip()
            if not stripped:
                return _invalid_document_page(operation)
            if "-" in stripped:
                start_text, end_text = stripped.split("-", 1)
                if start_text.isdigit() and end_text.isdigit() and int(start_text) >= 1 and int(end_text) >= int(start_text):
                    continue
                return _invalid_document_page(operation)
            if stripped.isdigit() and int(stripped) >= 1:
                continue
        return _invalid_document_page(operation)
    return None


def _invalid_document_page(operation: str) -> dict[str, Any]:
    return _document_operation_failure(
        operation,
        "PDF pages are 1-based and must be positive numbers or ascending ranges.",
        ("FR-PDF-MVP-005", "FR-PDF-MVP-006", "NFR-002"),
        error_category="validation_error",
    )


def _document_page_selector_count(pages: list[int | str]) -> int:
    count = 0
    for item in pages:
        if isinstance(item, int):
            count += 1
            continue
        if isinstance(item, str) and "-" in item:
            start_text, end_text = item.split("-", 1)
            count += int(end_text) - int(start_text) + 1
            continue
        count += 1
    return count


def _document_creation_content(
    operation: str,
    content: dict[str, Any] | None,
    *,
    title: str,
    slides: list[int | str | dict[str, Any]] | None,
) -> dict[str, Any]:
    payload = dict(content or {})
    if operation == "create_pptx":
        # Legacy facade shorthand only applies when the payload is not a PPTX V2 spec.
        # PPTX V2 carries its own `presentation.title` and slide schema, so injecting
        # top-level title/slides would create unknown top-level fields and trip the
        # strict V2 validator.
        if not _is_pptx_v2_spec(payload):
            if isinstance(title, str) and title.strip() and "title" not in payload:
                payload["title"] = title.strip()
            if slides is not None and "slides" not in payload:
                payload["slides"] = slides
    return payload


def _validate_create_docx_contract(content: dict[str, Any], input_path: Any, output_path: str) -> dict[str, Any] | None:
    has_input_path = isinstance(input_path, str) and bool(input_path.strip())
    has_inline_content = bool(content)
    accepted_fields = sorted(DOCX_V2_TOP_LEVEL_FIELDS | {"title", "paragraphs", "table"})
    if has_input_path:
        input_error = _validate_document_path_field("create_docx", input_path, field_name="input_path", expected_suffix=".json")
        if input_error is not None:
            return input_error
        if has_inline_content:
            return _document_operation_failure(
                "create_docx",
                "create_docx accepts either input_path or inline content, not both.",
                DOCX_V2_REQUIREMENT_IDS,
                output_path=output_path,
                error_category="validation_error",
                extra={"accepted_fields": accepted_fields, "unsupported_fields": []},
            )
        return None

    if not has_inline_content:
        return _document_operation_failure(
            "create_docx",
            "create_docx requires inline content or input_path.",
            DOCX_V2_REQUIREMENT_IDS,
            output_path=output_path,
            error_category="validation_error",
            extra={"accepted_fields": accepted_fields, "unsupported_fields": []},
        )
    if _is_docx_v2_spec(content):
        return _validate_docx_v2_content(content, output_path)

    content_error = _validate_document_content("create_docx", content)
    if content_error is None:
        return None
    unsupported_fields = sorted(str(key) for key in content if str(key) not in {"title", "paragraphs", "table"})
    return _document_operation_failure(
        "create_docx",
        content_error,
        DOCX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category="validation_error",
        extra={"accepted_fields": sorted({"title", "paragraphs", "table"}), "unsupported_fields": unsupported_fields},
    )


def _is_docx_v2_spec(content: dict[str, Any]) -> bool:
    return any(key in content for key in ("schema_version", "document", "page", "styles", "content"))


def _validate_docx_v2_content(content: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown_top = sorted(str(key) for key in content if str(key) not in DOCX_V2_TOP_LEVEL_FIELDS)
    if unknown_top:
        return _docx_v2_failure(
            f"create_docx content has unsupported fields: {', '.join(unknown_top)}.",
            output_path,
            unsupported_fields=unknown_top,
            accepted_fields=sorted(DOCX_V2_TOP_LEVEL_FIELDS),
        )

    schema_version = content.get("schema_version", DOCX_V2_SCHEMA_VERSION)
    if not isinstance(schema_version, str) or schema_version not in DOCX_V2_SUPPORTED_SCHEMA_VERSIONS:
        return _docx_v2_failure(
            f"create_docx schema_version must be one of: {', '.join(sorted(DOCX_V2_SUPPORTED_SCHEMA_VERSIONS))}.",
            output_path,
        )

    document_meta = content.get("document")
    if document_meta is not None:
        if not isinstance(document_meta, dict):
            return _docx_v2_failure("create_docx document must be an object.", output_path)
        unknown = sorted(str(key) for key in document_meta if str(key) not in DOCX_V2_DOCUMENT_FIELDS)
        if unknown:
            return _docx_v2_failure(
                f"create_docx document has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(DOCX_V2_DOCUMENT_FIELDS),
            )
        for field_name in DOCX_V2_DOCUMENT_FIELDS:
            value = document_meta.get(field_name)
            if value is not None and not isinstance(value, str):
                return _docx_v2_failure(f"create_docx document.{field_name} must be a string.", output_path)

    page_error = _validate_docx_v2_page(content.get("page"), output_path)
    if page_error is not None:
        return page_error
    styles_error = _validate_docx_v2_styles(content.get("styles"), output_path)
    if styles_error is not None:
        return styles_error

    elements = content.get("content")
    if not isinstance(elements, list) or not elements:
        return _docx_v2_failure("create_docx content.content must be a non-empty list of elements.", output_path)
    if len(elements) > DOCX_V2_MAX_CONTENT_ELEMENTS:
        return _docx_v2_failure(
            f"create_docx supports at most {DOCX_V2_MAX_CONTENT_ELEMENTS} content elements.",
            output_path,
            error_category="limit_exceeded",
        )

    paragraph_count = 0
    table_count = 0
    table_cells = 0
    image_count = 0
    for index, element in enumerate(elements, start=1):
        if not isinstance(element, dict):
            return _docx_v2_failure(f"create_docx content element {index} must be an object.", output_path)
        element_type = element.get("type")
        if not isinstance(element_type, str) or element_type not in DOCX_V2_CONTENT_TYPES:
            return _docx_v2_failure(
                f"create_docx content element {index}.type must be one of: {', '.join(sorted(DOCX_V2_CONTENT_TYPES))}.",
                output_path,
            )
        if element_type in DOCX_V2_TEXT_TYPES:
            paragraph_count += 1
            error = _validate_docx_v2_text_element(index, element_type, element, output_path)
            if error is not None:
                return error
        elif element_type in {"bullet_list", "numbered_list"}:
            error = _validate_docx_v2_list_element(index, element_type, element, output_path)
            if error is not None:
                return error
            paragraph_count += len(element["items"])
        elif element_type == "page_break":
            unknown = sorted(str(key) for key in element if str(key) != "type")
            if unknown:
                return _docx_v2_failure(
                    f"create_docx page_break element {index} has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=["type"],
                )
        elif element_type == "image":
            image_count += 1
            error = _validate_docx_v2_image_element(index, element, output_path)
            if error is not None:
                return error
        elif element_type == "table":
            table_count += 1
            error = _validate_docx_v2_table_element(index, element, output_path)
            if error is not None:
                return error
            rows = element["rows"]
            table_cells += sum(len(row) for row in rows if isinstance(row, list))

    if paragraph_count > DOCX_V2_MAX_PARAGRAPHS:
        return _docx_v2_failure(
            f"create_docx supports at most {DOCX_V2_MAX_PARAGRAPHS} paragraph-like elements.",
            output_path,
            error_category="limit_exceeded",
        )
    if table_count > DOCX_V2_MAX_TABLES:
        return _docx_v2_failure(
            f"create_docx supports at most {DOCX_V2_MAX_TABLES} tables.",
            output_path,
            error_category="limit_exceeded",
        )
    if table_cells > DOCX_V2_MAX_TABLE_CELLS:
        return _docx_v2_failure(
            f"create_docx supports at most {DOCX_V2_MAX_TABLE_CELLS} table cells.",
            output_path,
            error_category="limit_exceeded",
        )
    if image_count > DOCX_V2_MAX_IMAGES:
        return _docx_v2_failure(
            f"create_docx supports at most {DOCX_V2_MAX_IMAGES} images.",
            output_path,
            error_category="limit_exceeded",
        )
    if _contains_active_string(content):
        return _docx_v2_failure("Formulas, macros, raw XML, raw HTML/CSS and active content are not supported.", output_path)
    return None


def _validate_docx_v2_page(page: Any, output_path: str) -> dict[str, Any] | None:
    if page is None:
        return None
    if not isinstance(page, dict):
        return _docx_v2_failure("create_docx page must be an object.", output_path)
    unknown = sorted(str(key) for key in page if str(key) not in DOCX_V2_PAGE_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx page has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_PAGE_FIELDS),
        )
    page_size = page.get("size", "A4")
    if not isinstance(page_size, str) or page_size.upper() not in DOCX_V2_PAGE_SIZES:
        return _docx_v2_failure("create_docx page.size must be A4 or A5.", output_path)
    orientation = page.get("orientation", "portrait")
    if not isinstance(orientation, str) or orientation.casefold() not in DOCX_V2_ORIENTATIONS:
        return _docx_v2_failure("create_docx page.orientation must be portrait or landscape.", output_path)
    margins = page.get("margins_mm")
    if margins is not None:
        if not isinstance(margins, dict):
            return _docx_v2_failure("create_docx page.margins_mm must be an object.", output_path)
        unknown_margins = sorted(str(key) for key in margins if str(key) not in DOCX_V2_MARGIN_FIELDS)
        if unknown_margins:
            return _docx_v2_failure(
                f"create_docx margins_mm has unsupported fields: {', '.join(unknown_margins)}.",
                output_path,
                unsupported_fields=unknown_margins,
                accepted_fields=sorted(DOCX_V2_MARGIN_FIELDS),
            )
        for field_name, value in margins.items():
            if not _is_docx_number(value) or not 0 <= float(value) <= 100:
                return _docx_v2_failure(f"create_docx page.margins_mm.{field_name} must be a number between 0 and 100.", output_path)
    return None


def _validate_docx_v2_styles(styles: Any, output_path: str) -> dict[str, Any] | None:
    if styles is None:
        return None
    if not isinstance(styles, dict):
        return _docx_v2_failure("create_docx styles must be an object.", output_path)
    unknown_styles = sorted(str(key) for key in styles if str(key) not in DOCX_V2_STYLE_NAMES)
    if unknown_styles:
        return _docx_v2_failure(
            f"create_docx styles has unsupported style names: {', '.join(unknown_styles)}.",
            output_path,
            unsupported_fields=unknown_styles,
            accepted_fields=sorted(DOCX_V2_STYLE_NAMES),
        )
    for style_name, style_spec in styles.items():
        if not isinstance(style_spec, dict):
            return _docx_v2_failure(f"create_docx styles.{style_name} must be an object.", output_path)
        style_error = _validate_docx_v2_style_spec(f"styles.{style_name}", style_spec, output_path)
        if style_error is not None:
            return style_error
    return None


def _validate_docx_v2_style_spec(path: str, style_spec: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in style_spec if str(key) not in DOCX_V2_STYLE_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx {path} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_STYLE_FIELDS),
        )
    for field_name, value in style_spec.items():
        if field_name == "font":
            if not isinstance(value, str) or not value.strip() or len(value) > 100:
                return _docx_v2_failure(f"create_docx {path}.font must be a non-empty string up to 100 characters.", output_path)
        elif field_name == "size_pt":
            if not _is_docx_number(value) or not 1 <= float(value) <= 96:
                return _docx_v2_failure(f"create_docx {path}.size_pt must be a number between 1 and 96.", output_path)
        elif field_name in {"bold", "italic", "page_break_before"}:
            if not isinstance(value, bool):
                return _docx_v2_failure(f"create_docx {path}.{field_name} must be a boolean.", output_path)
        elif field_name == "alignment":
            if not isinstance(value, str) or value.casefold() not in DOCX_V2_ALIGNMENTS:
                return _docx_v2_failure(f"create_docx {path}.alignment must be left, center, right or justify.", output_path)
        elif field_name == "line_spacing":
            if not _is_docx_number(value) or not 0.5 <= float(value) <= 3:
                return _docx_v2_failure(f"create_docx {path}.line_spacing must be a number between 0.5 and 3.", output_path)
        elif field_name in {"space_before_pt", "space_after_pt"}:
            if not _is_docx_number(value) or not 0 <= float(value) <= 144:
                return _docx_v2_failure(f"create_docx {path}.{field_name} must be a number between 0 and 144.", output_path)
        elif field_name == "first_line_indent_mm":
            if not _is_docx_number(value) or not 0 <= float(value) <= 50:
                return _docx_v2_failure(f"create_docx {path}.first_line_indent_mm must be a number between 0 and 50.", output_path)
    return None


def _validate_docx_v2_text_element(index: int, element_type: str, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in DOCX_V2_TEXT_ELEMENT_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx {element_type} element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_TEXT_ELEMENT_FIELDS),
        )
    has_text = "text" in element
    has_runs = "runs" in element
    if has_text and has_runs:
        return _docx_v2_failure(f"create_docx {element_type} element {index} must use either text or runs, not both.", output_path)
    if not has_text and not has_runs:
        return _docx_v2_failure(f"create_docx {element_type} element {index} requires text or runs.", output_path)
    if has_text:
        text = element.get("text")
        if not isinstance(text, str):
            return _docx_v2_failure(f"create_docx {element_type} element {index}.text must be a string.", output_path)
        if element_type != "paragraph" and not text.strip():
            return _docx_v2_failure(f"create_docx {element_type} element {index}.text must not be empty.", output_path)
    if has_runs:
        runs = element.get("runs")
        if not isinstance(runs, list) or not runs:
            return _docx_v2_failure(f"create_docx {element_type} element {index}.runs must be a non-empty list.", output_path)
        for run_index, run in enumerate(runs, start=1):
            run_error = _validate_docx_v2_run(index, run_index, run, output_path)
            if run_error is not None:
                return run_error
    style_name = element.get("style")
    if style_name is not None and (not isinstance(style_name, str) or style_name not in DOCX_V2_STYLE_NAMES):
        return _docx_v2_failure(f"create_docx {element_type} element {index}.style is not supported.", output_path)
    style_overrides = element.get("style_overrides")
    if style_overrides is not None:
        if not isinstance(style_overrides, dict):
            return _docx_v2_failure(f"create_docx {element_type} element {index}.style_overrides must be an object.", output_path)
        return _validate_docx_v2_style_spec(f"content[{index}].style_overrides", style_overrides, output_path)
    return None


def _validate_docx_v2_run(element_index: int, run_index: int, run: Any, output_path: str) -> dict[str, Any] | None:
    if not isinstance(run, dict):
        return _docx_v2_failure(f"create_docx content element {element_index} run {run_index} must be an object.", output_path)
    unknown = sorted(str(key) for key in run if str(key) not in DOCX_V2_RUN_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx content element {element_index} run {run_index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_RUN_FIELDS),
        )
    if not isinstance(run.get("text"), str):
        return _docx_v2_failure(f"create_docx content element {element_index} run {run_index}.text must be a string.", output_path)
    for field_name in ("bold", "italic", "underline"):
        value = run.get(field_name)
        if value is not None and not isinstance(value, bool):
            return _docx_v2_failure(f"create_docx content element {element_index} run {run_index}.{field_name} must be a boolean.", output_path)
    return None


def _validate_docx_v2_list_element(index: int, element_type: str, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in DOCX_V2_LIST_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx {element_type} element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_LIST_FIELDS),
        )
    items = element.get("items")
    if not isinstance(items, list) or not items:
        return _docx_v2_failure(f"create_docx {element_type} element {index}.items must be a non-empty list of strings.", output_path)
    for item_index, item in enumerate(items, start=1):
        if not isinstance(item, str) or not item.strip():
            return _docx_v2_failure(f"create_docx {element_type} element {index} item {item_index} must be a non-empty string.", output_path)
    style_overrides = element.get("style_overrides")
    if style_overrides is not None:
        if not isinstance(style_overrides, dict):
            return _docx_v2_failure(f"create_docx {element_type} element {index}.style_overrides must be an object.", output_path)
        return _validate_docx_v2_style_spec(f"content[{index}].style_overrides", style_overrides, output_path)
    return None


def _validate_docx_v2_image_path_string(
    index: int, raw_path: Any, output_path: str
) -> dict[str, Any] | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return _docx_v2_failure(
            f"create_docx image element {index}.path must be a non-empty string.", output_path
        )
    text = raw_path.strip()
    if _looks_like_external_url(text):
        return _docx_v2_failure(
            f"create_docx image element {index}.path must not be an external URL.",
            output_path,
            error_category="external_url_rejected",
        )
    if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]+:", text):
        return _docx_v2_failure(
            f"create_docx image element {index}.path must be a workspace-relative path, not a URL.",
            output_path,
            error_category="external_url_rejected",
        )
    if text.startswith("\\\\") or text.startswith("//"):
        return _docx_v2_failure(
            f"create_docx image element {index}.path must not be a UNC network path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    if re.match(r"^[A-Za-z]:[\\/]", text) or text.startswith("/") or text.startswith("\\"):
        return _docx_v2_failure(
            f"create_docx image element {index}.path must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    if Path(text).is_absolute():
        return _docx_v2_failure(
            f"create_docx image element {index}.path must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    source_error = _validate_document_source_field(
        "create_docx", text, field_name=f"content element {index}.path"
    )
    if source_error is not None:
        return source_error
    if Path(text).suffix.casefold() not in DOCX_V2_IMAGE_SUFFIXES:
        return _docx_v2_failure(
            "create_docx image paths must use .png, .jpg or .jpeg.",
            output_path,
            error_category="unsupported_extension",
        )
    return None


def _validate_docx_v2_image_element(index: int, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in DOCX_V2_IMAGE_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx image element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_IMAGE_FIELDS),
        )
    image_path = element.get("path")
    path_error = _validate_docx_v2_image_path_string(index, image_path, output_path)
    if path_error is not None:
        return path_error
    align = element.get("align", "left")
    if not isinstance(align, str) or align.casefold() not in {"left", "center", "right"}:
        return _docx_v2_failure("create_docx image align must be left, center or right.", output_path)
    for field_name in ("width_mm", "height_mm"):
        value = element.get(field_name)
        if value is not None and (not _is_docx_number(value) or not 1 <= float(value) <= 300):
            return _docx_v2_failure(f"create_docx image {field_name} must be a number between 1 and 300.", output_path)
    return None


def _validate_docx_v2_table_element(index: int, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in DOCX_V2_TABLE_FIELDS)
    if unknown:
        return _docx_v2_failure(
            f"create_docx table element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(DOCX_V2_TABLE_FIELDS),
        )
    rows = element.get("rows")
    if not isinstance(rows, list) or not rows:
        return _docx_v2_failure(f"create_docx table element {index}.rows must be a non-empty list.", output_path)
    for row_index, row in enumerate(rows, start=1):
        if not _is_scalar_row(row):
            return _docx_v2_failure(f"create_docx table element {index} row {row_index} must be a list of scalar cells.", output_path)
    return None


def _is_docx_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _docx_v2_failure(
    reason: str,
    output_path: str,
    *,
    error_category: str = "validation_error",
    unsupported_fields: list[str] | None = None,
    accepted_fields: list[str] | None = None,
) -> dict[str, Any]:
    return _document_operation_failure(
        "create_docx",
        reason,
        DOCX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category=error_category,
        extra={
            "accepted_fields": accepted_fields or sorted(DOCX_V2_TOP_LEVEL_FIELDS),
            "unsupported_fields": unsupported_fields or [],
        },
    )


def _edit_docx_failure(
    reason: str,
    output_path: str,
    *,
    error_category: str = "validation_error",
    unsupported_fields: list[str] | None = None,
    accepted_fields: list[str] | None = None,
) -> dict[str, Any]:
    return _document_operation_failure(
        "edit_docx",
        reason,
        EDIT_DOCX_REQUIREMENT_IDS,
        output_path=output_path,
        error_category=error_category,
        extra={
            "accepted_fields": accepted_fields or sorted(EDIT_DOCX_TOP_LEVEL_FIELDS),
            "unsupported_fields": unsupported_fields or [],
        },
    )


def _validate_edit_docx_contract(content: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown_top = sorted(str(k) for k in content if str(k) not in EDIT_DOCX_TOP_LEVEL_FIELDS)
    if unknown_top:
        return _edit_docx_failure(
            f"edit_docx content has unsupported fields: {', '.join(unknown_top)}.",
            output_path,
            unsupported_fields=unknown_top,
            accepted_fields=sorted(EDIT_DOCX_TOP_LEVEL_FIELDS),
        )
    schema_version = content.get("schema_version")
    if schema_version is not None and schema_version not in EDIT_DOCX_SUPPORTED_SCHEMA_VERSIONS:
        return _edit_docx_failure(
            f"edit_docx schema_version must be one of: {', '.join(sorted(EDIT_DOCX_SUPPORTED_SCHEMA_VERSIONS))}.",
            output_path,
        )
    edits = content.get("edits")
    if not isinstance(edits, list) or not edits:
        return _edit_docx_failure("edit_docx edits must be a non-empty list.", output_path)
    if len(edits) > EDIT_DOCX_MAX_OPS:
        return _edit_docx_failure(
            f"edit_docx supports at most {EDIT_DOCX_MAX_OPS} edit operations.",
            output_path,
            error_category="limit_exceeded",
        )
    for index, edit in enumerate(edits, start=1):
        if not isinstance(edit, dict):
            return _edit_docx_failure(f"edit_docx edits[{index}] must be an object.", output_path)
        op_type = edit.get("type")
        if not isinstance(op_type, str) or op_type not in EDIT_DOCX_OP_TYPES:
            return _edit_docx_failure(
                f"edit_docx edits[{index}].type must be one of: {', '.join(sorted(EDIT_DOCX_OP_TYPES))}.",
                output_path,
            )
        if op_type == "replace_text":
            unknown = sorted(str(k) for k in edit if str(k) not in EDIT_DOCX_REPLACE_TEXT_FIELDS)
            if unknown:
                return _edit_docx_failure(
                    f"edit_docx edits[{index}] has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=sorted(EDIT_DOCX_REPLACE_TEXT_FIELDS),
                )
            find = edit.get("find")
            if not isinstance(find, str) or not find:
                return _edit_docx_failure(f"edit_docx edits[{index}].find must be a non-empty string.", output_path)
            replace = edit.get("replace")
            if not isinstance(replace, str):
                return _edit_docx_failure(f"edit_docx edits[{index}].replace must be a string.", output_path)
            max_replacements = edit.get("max_replacements")
            if max_replacements is not None:
                if isinstance(max_replacements, bool) or not isinstance(max_replacements, int) or max_replacements < 1:
                    return _edit_docx_failure(
                        f"edit_docx edits[{index}].max_replacements must be a positive integer.", output_path
                    )
            if _contains_active_string(find) or _contains_active_string(replace):
                return _edit_docx_failure(
                    "Formulas, macros, raw XML, raw HTML/CSS and active content are not supported.", output_path
                )
        elif op_type == "set_core_property":
            unknown = sorted(str(k) for k in edit if str(k) not in EDIT_DOCX_SET_CORE_PROPERTY_FIELDS)
            if unknown:
                return _edit_docx_failure(
                    f"edit_docx edits[{index}] has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=sorted(EDIT_DOCX_SET_CORE_PROPERTY_FIELDS),
                )
            name = edit.get("name")
            if not isinstance(name, str) or name not in EDIT_DOCX_CORE_PROPERTY_NAMES:
                return _edit_docx_failure(
                    f"edit_docx edits[{index}].name must be one of: {', '.join(sorted(EDIT_DOCX_CORE_PROPERTY_NAMES))}.",
                    output_path,
                )
            value = edit.get("value")
            if not isinstance(value, str):
                return _edit_docx_failure(f"edit_docx edits[{index}].value must be a string.", output_path)
            if _contains_active_string(value):
                return _edit_docx_failure(
                    "Formulas, macros, raw XML, raw HTML/CSS and active content are not supported.", output_path
                )
        elif op_type == "append_paragraph":
            unknown = sorted(str(k) for k in edit if str(k) not in EDIT_DOCX_APPEND_PARAGRAPH_FIELDS)
            if unknown:
                return _edit_docx_failure(
                    f"edit_docx edits[{index}] has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=sorted(EDIT_DOCX_APPEND_PARAGRAPH_FIELDS),
                )
            text = edit.get("text")
            if not isinstance(text, str):
                return _edit_docx_failure(f"edit_docx edits[{index}].text must be a string.", output_path)
            style = edit.get("style")
            if style is not None and (not isinstance(style, str) or style not in DOCX_V2_STYLE_NAMES):
                return _edit_docx_failure(
                    f"edit_docx edits[{index}].style must be one of: {', '.join(sorted(DOCX_V2_STYLE_NAMES))}.",
                    output_path,
                )
            if _contains_active_string(text):
                return _edit_docx_failure(
                    "Formulas, macros, raw XML, raw HTML/CSS and active content are not supported.", output_path
                )
        elif op_type in {"set_footer_text", "set_header_text"}:
            unknown = sorted(str(k) for k in edit if str(k) not in EDIT_DOCX_SET_HEADER_FOOTER_FIELDS)
            if unknown:
                return _edit_docx_failure(
                    f"edit_docx edits[{index}] has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=sorted(EDIT_DOCX_SET_HEADER_FOOTER_FIELDS),
                )
            text = edit.get("text")
            if not isinstance(text, str):
                return _edit_docx_failure(f"edit_docx edits[{index}].text must be a string.", output_path)
            page_number = edit.get("page_number")
            if page_number is not None and not isinstance(page_number, bool):
                return _edit_docx_failure(f"edit_docx edits[{index}].page_number must be a boolean.", output_path)
            if _contains_active_string(text):
                return _edit_docx_failure(
                    "Formulas, macros, raw XML, raw HTML/CSS and active content are not supported.", output_path
                )
    return None


def _validate_create_xlsx_contract(content: dict[str, Any], input_path: Any, output_path: str) -> dict[str, Any] | None:
    has_input_path = isinstance(input_path, str) and bool(input_path.strip())
    has_inline_content = bool(content)
    accepted_fields = sorted(XLSX_V2_TOP_LEVEL_FIELDS | {"sheet_name", "rows"})
    if has_input_path:
        input_error = _validate_document_path_field("create_xlsx", input_path, field_name="input_path", expected_suffix=".json")
        if input_error is not None:
            return input_error
        if has_inline_content:
            return _xlsx_v2_failure(
                "create_xlsx accepts either input_path or inline content, not both.",
                output_path,
                accepted_fields=accepted_fields,
            )
        return None

    if not has_inline_content:
        return _xlsx_v2_failure(
            "create_xlsx requires inline content or input_path.",
            output_path,
            accepted_fields=accepted_fields,
        )
    if _is_xlsx_v2_spec(content):
        return _validate_xlsx_v2_content(content, output_path)

    content_error = _validate_document_content("create_xlsx", content)
    if content_error is None:
        return None
    unsupported_fields = sorted(str(key) for key in content if str(key) not in {"sheet_name", "rows"})
    return _document_operation_failure(
        "create_xlsx",
        content_error,
        XLSX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category="validation_error",
        extra={"accepted_fields": sorted({"sheet_name", "rows"}), "unsupported_fields": unsupported_fields},
    )


def _is_xlsx_v2_spec(content: dict[str, Any]) -> bool:
    return any(key in content for key in ("schema_version", "workbook", "sheets"))


def _validate_xlsx_v2_content(content: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown_top = sorted(str(key) for key in content if str(key) not in XLSX_V2_TOP_LEVEL_FIELDS)
    if unknown_top:
        return _xlsx_v2_failure(
            f"create_xlsx content has unsupported fields: {', '.join(unknown_top)}.",
            output_path,
            unsupported_fields=unknown_top,
            accepted_fields=sorted(XLSX_V2_TOP_LEVEL_FIELDS),
        )

    schema_version = content.get("schema_version", XLSX_V2_SCHEMA_VERSION)
    if not isinstance(schema_version, str) or schema_version not in XLSX_V2_SUPPORTED_SCHEMA_VERSIONS:
        return _xlsx_v2_failure(
            f"create_xlsx schema_version must be one of: {', '.join(sorted(XLSX_V2_SUPPORTED_SCHEMA_VERSIONS))}.",
            output_path,
        )

    workbook = content.get("workbook")
    if workbook is not None:
        if not isinstance(workbook, dict):
            return _xlsx_v2_failure("create_xlsx workbook must be an object.", output_path)
        unknown = sorted(str(key) for key in workbook if str(key) not in XLSX_V2_WORKBOOK_FIELDS)
        if unknown:
            return _xlsx_v2_failure(
                f"create_xlsx workbook has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(XLSX_V2_WORKBOOK_FIELDS),
            )
        for field_name, value in workbook.items():
            if value is not None and not isinstance(value, str):
                return _xlsx_v2_failure(f"create_xlsx workbook.{field_name} must be a string.", output_path)

    sheets = content.get("sheets")
    if not isinstance(sheets, list) or not sheets:
        return _xlsx_v2_failure("create_xlsx sheets must be a non-empty list.", output_path)
    if len(sheets) > XLSX_V2_MAX_SHEETS:
        return _xlsx_v2_failure(
            f"create_xlsx supports at most {XLSX_V2_MAX_SHEETS} sheets.",
            output_path,
            error_category="limit_exceeded",
        )
    seen_names: set[str] = set()
    total_cells = 0
    for index, sheet in enumerate(sheets, start=1):
        if not isinstance(sheet, dict):
            return _xlsx_v2_failure(f"create_xlsx sheet {index} must be an object.", output_path)
        sheet_error, sheet_cell_count = _validate_xlsx_v2_sheet(index, sheet, seen_names, output_path)
        if sheet_error is not None:
            return sheet_error
        total_cells += sheet_cell_count
        if total_cells > XLSX_V2_MAX_TOTAL_CELLS:
            return _xlsx_v2_failure(
                f"create_xlsx supports at most {XLSX_V2_MAX_TOTAL_CELLS} cells across the workbook.",
                output_path,
                error_category="limit_exceeded",
            )
    return None


def _validate_xlsx_v2_sheet(index: int, sheet: dict[str, Any], seen_names: set[str], output_path: str) -> tuple[dict[str, Any] | None, int]:
    unknown = sorted(str(key) for key in sheet if str(key) not in XLSX_V2_SHEET_FIELDS)
    if unknown:
        return (
            _xlsx_v2_failure(
                f"create_xlsx sheet {index} has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(XLSX_V2_SHEET_FIELDS),
            ),
            0,
        )
    name = sheet.get("name")
    if not _is_xlsx_v2_sheet_name(name):
        return _xlsx_v2_failure(f"create_xlsx sheet {index}.name is invalid.", output_path), 0
    normalized_name = str(name).casefold()
    if normalized_name in seen_names:
        return _xlsx_v2_failure(f"create_xlsx duplicate sheet name: {name}.", output_path), 0
    seen_names.add(normalized_name)

    rows = sheet.get("rows")
    if not isinstance(rows, list) or not rows:
        return _xlsx_v2_failure(f"create_xlsx sheet {index}.rows must be a non-empty list.", output_path), 0
    if len(rows) > XLSX_V2_MAX_ROWS_PER_SHEET:
        return (
            _xlsx_v2_failure(
                f"create_xlsx sheet {index} supports at most {XLSX_V2_MAX_ROWS_PER_SHEET} rows.",
                output_path,
                error_category="limit_exceeded",
            ),
            0,
        )
    max_cols = 0
    cell_count = 0
    for row_index, row in enumerate(rows, start=1):
        if not isinstance(row, list):
            return _xlsx_v2_failure(f"create_xlsx sheet {index} row {row_index} must be an array.", output_path), 0
        max_cols = max(max_cols, len(row))
        if max_cols > XLSX_V2_MAX_COLUMNS_PER_SHEET:
            return (
                _xlsx_v2_failure(
                    f"create_xlsx sheet {index} supports at most {XLSX_V2_MAX_COLUMNS_PER_SHEET} columns.",
                    output_path,
                    error_category="limit_exceeded",
                ),
                0,
            )
        cell_count += len(row)
        if cell_count > XLSX_V2_MAX_CELLS_PER_SHEET:
            return (
                _xlsx_v2_failure(
                    f"create_xlsx sheet {index} supports at most {XLSX_V2_MAX_CELLS_PER_SHEET} cells.",
                    output_path,
                    error_category="limit_exceeded",
                ),
                0,
            )
        for col_index, cell in enumerate(row, start=1):
            cell_error = _validate_xlsx_v2_cell(index, row_index, col_index, cell, output_path)
            if cell_error is not None:
                return cell_error, 0
    structure_error = _validate_xlsx_v2_sheet_structure(index, sheet, output_path, row_count=len(rows), max_cols=max_cols)
    if structure_error is not None:
        return structure_error, 0
    return None, cell_count


def _validate_xlsx_v2_cell(sheet_index: int, row_index: int, col_index: int, cell: Any, output_path: str) -> dict[str, Any] | None:
    if not isinstance(cell, dict):
        if _is_xlsx_v2_scalar(cell):
            return None
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index} has an unsupported value type.", output_path)
    unknown = sorted(str(key) for key in cell if str(key) not in XLSX_V2_CELL_FIELDS)
    if unknown:
        return _xlsx_v2_failure(
            f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(XLSX_V2_CELL_FIELDS),
        )
    has_value = "value" in cell
    has_formula = "formula" in cell
    if has_value and has_formula:
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index} must use either value or formula, not both.", output_path)
    if not has_value and not has_formula:
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index} requires value or formula.", output_path)
    if has_value and not _is_xlsx_v2_scalar(cell.get("value")):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.value has an unsupported type.", output_path)
    if has_formula:
        formula = cell.get("formula")
        if not isinstance(formula, str) or not formula.strip():
            return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.formula must be a non-empty string.", output_path)
        formula_error = _validate_xlsx_v2_formula(formula, output_path)
        if formula_error is not None:
            return formula_error
    return _validate_xlsx_v2_cell_format(sheet_index, row_index, col_index, cell, output_path)


def _validate_xlsx_v2_cell_format(sheet_index: int, row_index: int, col_index: int, cell: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    for field_name in ("bold", "italic", "underline", "wrap_text"):
        value = cell.get(field_name)
        if value is not None and not isinstance(value, bool):
            return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.{field_name} must be a boolean.", output_path)
    font_size = cell.get("font_size")
    if font_size is not None and (not _is_xlsx_v2_number(font_size) or not 1 <= float(font_size) <= 96):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.font_size must be a number between 1 and 96.", output_path)
    for field_name in ("font_color", "fill_color"):
        value = cell.get(field_name)
        if value is not None and not _is_xlsx_v2_color(value):
            return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.{field_name} must be #RRGGBB or RRGGBB.", output_path)
    alignment = cell.get("alignment")
    if alignment is not None and (not isinstance(alignment, str) or alignment.casefold() not in XLSX_V2_ALIGNMENTS):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.alignment must be left, center or right.", output_path)
    vertical = cell.get("vertical_alignment")
    if vertical is not None and (not isinstance(vertical, str) or vertical.casefold() not in XLSX_V2_VERTICAL_ALIGNMENTS):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.vertical_alignment must be top, middle or bottom.", output_path)
    number_format = cell.get("number_format")
    if number_format is not None and (not isinstance(number_format, str) or not number_format.strip() or len(number_format) > 100):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.number_format must be a non-empty string up to 100 characters.", output_path)
    border = cell.get("border")
    if border is not None and (not isinstance(border, str) or border.casefold() not in XLSX_V2_BORDERS):
        return _xlsx_v2_failure(f"create_xlsx sheet {sheet_index} cell {row_index}:{col_index}.border must be none, thin, medium or thick.", output_path)
    return None


def _validate_xlsx_v2_sheet_structure(index: int, sheet: dict[str, Any], output_path: str, *, row_count: int, max_cols: int) -> dict[str, Any] | None:
    freeze_panes = sheet.get("freeze_panes")
    if freeze_panes is not None and (not isinstance(freeze_panes, str) or not _is_xlsx_v2_cell_ref(freeze_panes)):
        return _xlsx_v2_failure(f"create_xlsx sheet {index}.freeze_panes must be an A1 cell reference.", output_path)
    auto_filter = sheet.get("auto_filter")
    if auto_filter is not None and not isinstance(auto_filter, bool):
        return _xlsx_v2_failure(f"create_xlsx sheet {index}.auto_filter must be a boolean.", output_path)
    column_widths = sheet.get("column_widths")
    if column_widths is not None:
        if not isinstance(column_widths, dict):
            return _xlsx_v2_failure(f"create_xlsx sheet {index}.column_widths must be an object.", output_path)
        for column, width in column_widths.items():
            if not isinstance(column, str) or not _is_xlsx_v2_column_ref(column):
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.column_widths keys must be Excel columns.", output_path)
            if not _is_xlsx_v2_number(width) or not 1 <= float(width) <= 100:
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.column_widths values must be numbers between 1 and 100.", output_path)
    row_heights = sheet.get("row_heights")
    if row_heights is not None:
        if not isinstance(row_heights, dict):
            return _xlsx_v2_failure(f"create_xlsx sheet {index}.row_heights must be an object.", output_path)
        for row, height in row_heights.items():
            if not isinstance(row, str) or not row.isdigit() or int(row) < 1:
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.row_heights keys must be positive 1-based row numbers.", output_path)
            if not _is_xlsx_v2_number(height) or not 1 <= float(height) <= 300:
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.row_heights values must be numbers between 1 and 300.", output_path)
    merge_cells = sheet.get("merge_cells")
    if merge_cells is not None:
        if not isinstance(merge_cells, list):
            return _xlsx_v2_failure(f"create_xlsx sheet {index}.merge_cells must be a list.", output_path)
        if len(merge_cells) > XLSX_V2_MAX_MERGED_RANGES:
            return _xlsx_v2_failure(
                f"create_xlsx supports at most {XLSX_V2_MAX_MERGED_RANGES} merged ranges.",
                output_path,
                error_category="limit_exceeded",
            )
        occupied: set[tuple[int, int]] = set()
        for item in merge_cells:
            if not isinstance(item, str) or not _is_xlsx_v2_range_ref(item):
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.merge_cells entries must be A1:B2 ranges.", output_path)
            min_col, min_row, max_col, max_row = _xlsx_v2_range_bounds(item)
            if max_row > row_count or max_col > max_cols:
                return _xlsx_v2_failure(f"create_xlsx sheet {index}.merge_cells range exceeds used sheet bounds.", output_path)
            cells_in_range = (max_row - min_row + 1) * (max_col - min_col + 1)
            if cells_in_range <= 10000:
                current = {(row, col) for row in range(min_row, max_row + 1) for col in range(min_col, max_col + 1)}
                if occupied & current:
                    return _xlsx_v2_failure(f"create_xlsx sheet {index}.merge_cells ranges overlap.", output_path)
                occupied.update(current)
    return None


def _is_xlsx_v2_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_xlsx_v2_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_xlsx_v2_sheet_name(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 31 and re.search(r"[:\\/?*\[\]]", value) is None


def _is_xlsx_v2_color(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}|#?[0-9A-Fa-f]{8}", value.strip()) is not None


def _is_xlsx_v2_column_ref(value: str) -> bool:
    text = value.strip()
    return re.fullmatch(r"[A-Za-z]{1,3}", text) is not None and 1 <= _xlsx_v2_column_index(text) <= 16384


def _is_xlsx_v2_cell_ref(value: str) -> bool:
    match = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})", value.strip())
    if not match:
        return False
    return 1 <= _xlsx_v2_column_index(match.group(1)) <= 16384 and 1 <= int(match.group(2)) <= 1_048_576


def _is_xlsx_v2_range_ref(value: str) -> bool:
    parts = value.strip().split(":")
    if len(parts) != 2 or not all(_is_xlsx_v2_cell_ref(part) for part in parts):
        return False
    min_col, min_row, max_col, max_row = _xlsx_v2_range_bounds(value)
    return min_col <= max_col and min_row <= max_row


def _xlsx_v2_range_bounds(value: str) -> tuple[int, int, int, int]:
    start, end = value.strip().split(":", 1)
    start_col, start_row = _xlsx_v2_cell_ref_parts(start)
    end_col, end_row = _xlsx_v2_cell_ref_parts(end)
    return start_col, start_row, end_col, end_row


def _xlsx_v2_cell_ref_parts(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})", value.strip())
    if not match:
        return 0, 0
    return _xlsx_v2_column_index(match.group(1)), int(match.group(2))


def _xlsx_v2_column_index(value: str) -> int:
    index = 0
    for char in value.strip().upper():
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index


def _validate_xlsx_v2_formula(value: str, output_path: str) -> dict[str, Any] | None:
    formula = value.strip().removeprefix("=")
    upper = formula.upper()
    if not formula:
        return _xlsx_v2_failure("create_xlsx formula must not be empty.", output_path)
    if "[" in formula or "]" in formula or "://" in formula or "HTTP://" in upper or "HTTPS://" in upper:
        return _xlsx_v2_failure("create_xlsx formulas must not contain external references or URLs.", output_path)
    if any(token in upper for token in XLSX_V2_UNSAFE_FORMULA_TOKENS):
        return _xlsx_v2_failure("create_xlsx formula uses an unsafe external or macro-like function.", output_path)
    return None


def _xlsx_v2_failure(
    reason: str,
    output_path: str,
    *,
    error_category: str = "validation_error",
    unsupported_fields: list[str] | None = None,
    accepted_fields: list[str] | None = None,
) -> dict[str, Any]:
    return _document_operation_failure(
        "create_xlsx",
        reason,
        XLSX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category=error_category,
        extra={
            "accepted_fields": accepted_fields or sorted(XLSX_V2_TOP_LEVEL_FIELDS),
            "unsupported_fields": unsupported_fields or [],
        },
    )


# ---------------------------------------------------------------------------
# PPTX Creation V2 contract validation
# ---------------------------------------------------------------------------


def _validate_create_pptx_contract(content: dict[str, Any], input_path: Any, output_path: str) -> dict[str, Any] | None:
    has_input_path = isinstance(input_path, str) and bool(input_path.strip())
    has_inline_content = bool(content)
    accepted_fields = sorted(PPTX_V2_TOP_LEVEL_FIELDS | {"title", "slides"})
    if has_input_path:
        input_error = _validate_document_path_field(
            "create_pptx", input_path, field_name="input_path", expected_suffix=".json"
        )
        if input_error is not None:
            return input_error
        if has_inline_content:
            return _pptx_v2_failure(
                "create_pptx accepts either input_path or inline content, not both.",
                output_path,
                accepted_fields=accepted_fields,
            )
        return None

    if not has_inline_content:
        return _pptx_v2_failure(
            "create_pptx requires inline content or input_path.",
            output_path,
            accepted_fields=accepted_fields,
        )
    if _is_pptx_v2_spec(content):
        return _validate_pptx_v2_content(content, output_path)

    content_error = _validate_document_content("create_pptx", content)
    if content_error is None:
        return None
    unsupported_fields = sorted(str(key) for key in content if str(key) not in {"title", "slides"})
    return _document_operation_failure(
        "create_pptx",
        content_error,
        PPTX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category="validation_error",
        extra={
            "accepted_fields": sorted({"title", "slides"}),
            "unsupported_fields": unsupported_fields,
        },
    )


def _is_pptx_v2_spec(content: dict[str, Any]) -> bool:
    if any(key in content for key in ("schema_version", "presentation")):
        return True
    slides = content.get("slides")
    if isinstance(slides, list):
        for slide in slides:
            if isinstance(slide, dict) and any(
                key in slide for key in ("layout", "subtitle", "body", "content", "notes", "image")
            ):
                return True
    return False


def _validate_pptx_v2_content(content: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown_top = sorted(str(key) for key in content if str(key) not in PPTX_V2_TOP_LEVEL_FIELDS)
    if unknown_top:
        return _pptx_v2_failure(
            f"create_pptx content has unsupported fields: {', '.join(unknown_top)}.",
            output_path,
            unsupported_fields=unknown_top,
            accepted_fields=sorted(PPTX_V2_TOP_LEVEL_FIELDS),
        )

    schema_version = content.get("schema_version", PPTX_V2_SCHEMA_VERSION)
    if not isinstance(schema_version, str) or schema_version not in PPTX_V2_SUPPORTED_SCHEMA_VERSIONS:
        return _pptx_v2_failure(
            f"create_pptx schema_version must be one of: {', '.join(sorted(PPTX_V2_SUPPORTED_SCHEMA_VERSIONS))}.",
            output_path,
        )

    presentation_error = _validate_pptx_v2_presentation(content.get("presentation"), output_path)
    if presentation_error is not None:
        return presentation_error

    slides = content.get("slides")
    if not isinstance(slides, list) or not slides:
        return _pptx_v2_failure("create_pptx slides must be a non-empty list.", output_path)
    if len(slides) > PPTX_V2_MAX_SLIDES:
        return _pptx_v2_failure(
            f"create_pptx supports at most {PPTX_V2_MAX_SLIDES} slides.",
            output_path,
            error_category="limit_exceeded",
        )

    counters = {"images": 0}
    for index, slide in enumerate(slides, start=1):
        slide_error = _validate_pptx_v2_slide(index, slide, counters, output_path)
        if slide_error is not None:
            return slide_error

    if counters["images"] > PPTX_V2_MAX_IMAGES:
        return _pptx_v2_failure(
            f"create_pptx supports at most {PPTX_V2_MAX_IMAGES} images across the presentation.",
            output_path,
            error_category="limit_exceeded",
        )
    return None


def _validate_pptx_v2_presentation(presentation: Any, output_path: str) -> dict[str, Any] | None:
    if presentation is None:
        return None
    if not isinstance(presentation, dict):
        return _pptx_v2_failure("create_pptx presentation must be an object.", output_path)
    unknown = sorted(str(key) for key in presentation if str(key) not in PPTX_V2_PRESENTATION_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx presentation has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_PRESENTATION_FIELDS),
        )
    for field_name in ("title", "author"):
        value = presentation.get(field_name)
        if value is not None and not isinstance(value, str):
            return _pptx_v2_failure(f"create_pptx presentation.{field_name} must be a string.", output_path)
    slide_size = presentation.get("slide_size")
    if slide_size is not None:
        size_error = _validate_pptx_v2_slide_size(slide_size, output_path)
        if size_error is not None:
            return size_error
    return None


def _validate_pptx_v2_slide_size(slide_size: Any, output_path: str) -> dict[str, Any] | None:
    if isinstance(slide_size, str):
        if slide_size in PPTX_V2_SLIDE_SIZE_PRESETS:
            return None
        return _pptx_v2_failure(
            "create_pptx presentation.slide_size must be 16:9, 4:3, A4_portrait or a custom object.",
            output_path,
        )
    if isinstance(slide_size, dict):
        unknown = sorted(str(key) for key in slide_size if str(key) not in PPTX_V2_CUSTOM_SIZE_FIELDS)
        if unknown:
            return _pptx_v2_failure(
                f"create_pptx presentation.slide_size has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(PPTX_V2_CUSTOM_SIZE_FIELDS),
            )
        name = slide_size.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip() or len(name) > 50):
            return _pptx_v2_failure(
                "create_pptx presentation.slide_size.name must be a non-empty string up to 50 characters.",
                output_path,
            )
        for field_name in ("width_mm", "height_mm"):
            value = slide_size.get(field_name)
            if not _is_pptx_v2_number(value) or not PPTX_V2_CUSTOM_SIZE_MIN_MM <= float(value) <= PPTX_V2_CUSTOM_SIZE_MAX_MM:
                return _pptx_v2_failure(
                    f"create_pptx presentation.slide_size.{field_name} must be a number between "
                    f"{PPTX_V2_CUSTOM_SIZE_MIN_MM} and {PPTX_V2_CUSTOM_SIZE_MAX_MM}.",
                    output_path,
                )
        return None
    return _pptx_v2_failure(
        "create_pptx presentation.slide_size must be a string preset or a custom object.",
        output_path,
    )


def _validate_pptx_v2_slide(
    index: int, slide: Any, counters: dict[str, int], output_path: str
) -> dict[str, Any] | None:
    if not isinstance(slide, dict):
        return _pptx_v2_failure(f"create_pptx slide {index} must be an object.", output_path)
    unknown = sorted(str(key) for key in slide if str(key) not in PPTX_V2_SLIDE_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx slide {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_SLIDE_FIELDS),
        )
    layout = slide.get("layout")
    if not isinstance(layout, str) or layout not in PPTX_V2_LAYOUTS:
        return _pptx_v2_failure(
            f"create_pptx slide {index}.layout must be one of: {', '.join(sorted(PPTX_V2_LAYOUTS))}.",
            output_path,
            error_category="unsupported_layout",
        )

    for field_name in ("title", "subtitle", "body"):
        value = slide.get(field_name)
        if value is not None and not isinstance(value, str):
            return _pptx_v2_failure(f"create_pptx slide {index}.{field_name} must be a string.", output_path)

    if layout == "title":
        if not isinstance(slide.get("title"), str) or not slide["title"].strip():
            return _pptx_v2_failure(f"create_pptx slide {index} (title layout) requires title.", output_path)
        if "content" in slide:
            return _pptx_v2_failure(
                f"create_pptx slide {index} (title layout) must not use content.", output_path
            )
    elif layout == "section_header":
        if not isinstance(slide.get("title"), str) or not slide["title"].strip():
            return _pptx_v2_failure(
                f"create_pptx slide {index} (section_header layout) requires title.", output_path
            )
        if "content" in slide:
            return _pptx_v2_failure(
                f"create_pptx slide {index} (section_header layout) must not use content.", output_path
            )
    elif layout == "image":
        image_spec = slide.get("image")
        if not isinstance(image_spec, dict):
            return _pptx_v2_failure(
                f"create_pptx slide {index} (image layout) requires an image object.", output_path
            )
        image_error = _validate_pptx_v2_slide_image(index, image_spec, output_path)
        if image_error is not None:
            return image_error
        counters["images"] += 1
    elif layout == "content":
        if not isinstance(slide.get("title"), str) or not slide["title"].strip():
            return _pptx_v2_failure(
                f"create_pptx slide {index} (content layout) requires title.", output_path
            )
        content_error = _validate_pptx_v2_slide_content(index, slide.get("content"), counters, output_path)
        if content_error is not None:
            return content_error
    elif layout == "blank":
        if "content" in slide:
            content_error = _validate_pptx_v2_slide_content(index, slide.get("content"), counters, output_path)
            if content_error is not None:
                return content_error

    if layout != "image" and "image" in slide:
        return _pptx_v2_failure(
            f"create_pptx slide {index}.image is only allowed on the image layout.", output_path
        )

    notes = slide.get("notes")
    if notes is not None:
        if not isinstance(notes, str):
            return _pptx_v2_failure(f"create_pptx slide {index}.notes must be a string.", output_path)
        if len(notes) > 10000:
            return _pptx_v2_failure(
                f"create_pptx slide {index}.notes must be at most 10000 characters.",
                output_path,
                error_category="limit_exceeded",
            )
    return None


def _validate_pptx_v2_slide_content(
    slide_index: int, elements: Any, counters: dict[str, int], output_path: str
) -> dict[str, Any] | None:
    if elements is None:
        return None
    if not isinstance(elements, list) or not elements:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index}.content must be a non-empty list when present.", output_path
        )
    if len(elements) > PPTX_V2_MAX_CONTENT_ELEMENTS_PER_SLIDE:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} supports at most {PPTX_V2_MAX_CONTENT_ELEMENTS_PER_SLIDE} content elements.",
            output_path,
            error_category="limit_exceeded",
        )
    bullet_items = 0
    tables = 0
    table_cells = 0
    for element_index, element in enumerate(elements, start=1):
        if not isinstance(element, dict):
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} content element {element_index} must be an object.", output_path
            )
        element_type = element.get("type")
        if not isinstance(element_type, str) or element_type not in PPTX_V2_CONTENT_TYPES:
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} content element {element_index}.type must be one of: "
                f"{', '.join(sorted(PPTX_V2_CONTENT_TYPES))}.",
                output_path,
            )
        if element_type == "bullets":
            error, item_count = _validate_pptx_v2_bullets(slide_index, element_index, element, output_path)
            if error is not None:
                return error
            bullet_items += item_count
            if bullet_items > PPTX_V2_MAX_BULLET_ITEMS_PER_SLIDE:
                return _pptx_v2_failure(
                    f"create_pptx slide {slide_index} supports at most "
                    f"{PPTX_V2_MAX_BULLET_ITEMS_PER_SLIDE} bullet items.",
                    output_path,
                    error_category="limit_exceeded",
                )
        elif element_type == "paragraph":
            error = _validate_pptx_v2_paragraph(slide_index, element_index, element, output_path)
            if error is not None:
                return error
        elif element_type == "table":
            tables += 1
            if tables > PPTX_V2_MAX_TABLES_PER_SLIDE:
                return _pptx_v2_failure(
                    f"create_pptx slide {slide_index} supports at most {PPTX_V2_MAX_TABLES_PER_SLIDE} tables.",
                    output_path,
                    error_category="limit_exceeded",
                )
            error, cell_count = _validate_pptx_v2_table(slide_index, element_index, element, output_path)
            if error is not None:
                return error
            table_cells += cell_count
            if table_cells > PPTX_V2_MAX_TABLE_CELLS_PER_SLIDE:
                return _pptx_v2_failure(
                    f"create_pptx slide {slide_index} supports at most "
                    f"{PPTX_V2_MAX_TABLE_CELLS_PER_SLIDE} table cells.",
                    output_path,
                    error_category="limit_exceeded",
                )
        elif element_type == "image":
            error = _validate_pptx_v2_image_element(slide_index, element_index, element, output_path)
            if error is not None:
                return error
            counters["images"] += 1
        elif element_type == "text_box":
            error = _validate_pptx_v2_text_box(slide_index, element_index, element, output_path)
            if error is not None:
                return error
    return None


def _validate_pptx_v2_bullets(
    slide_index: int, element_index: int, element: dict[str, Any], output_path: str
) -> tuple[dict[str, Any] | None, int]:
    unknown = sorted(str(key) for key in element if str(key) not in PPTX_V2_BULLETS_FIELDS)
    if unknown:
        return (
            _pptx_v2_failure(
                f"create_pptx slide {slide_index} bullets element {element_index} has unsupported fields: "
                f"{', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(PPTX_V2_BULLETS_FIELDS),
            ),
            0,
        )
    items = element.get("items")
    if not isinstance(items, list) or not items:
        return (
            _pptx_v2_failure(
                f"create_pptx slide {slide_index} bullets element {element_index}.items must be a non-empty list.",
                output_path,
            ),
            0,
        )
    for item_index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index} must be an object.",
                    output_path,
                ),
                0,
            )
        unknown_item = sorted(str(key) for key in item if str(key) not in PPTX_V2_BULLET_ITEM_FIELDS)
        if unknown_item:
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index} has "
                    f"unsupported fields: {', '.join(unknown_item)}.",
                    output_path,
                    unsupported_fields=unknown_item,
                    accepted_fields=sorted(PPTX_V2_BULLET_ITEM_FIELDS),
                ),
                0,
            )
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index}.text "
                    f"must be a non-empty string.",
                    output_path,
                ),
                0,
            )
        level = item.get("level", 0)
        if isinstance(level, bool) or not isinstance(level, int) or level not in PPTX_V2_BULLET_LEVELS:
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index}.level "
                    f"must be one of: {sorted(PPTX_V2_BULLET_LEVELS)}.",
                    output_path,
                ),
                0,
            )
        for flag in ("bold", "italic"):
            value = item.get(flag)
            if value is not None and not isinstance(value, bool):
                return (
                    _pptx_v2_failure(
                        f"create_pptx slide {slide_index} bullets element {element_index} item {item_index}.{flag} "
                        f"must be a boolean.",
                        output_path,
                    ),
                    0,
                )
        font_size = item.get("font_size")
        if font_size is not None and (not _is_pptx_v2_number(font_size) or not 6 <= float(font_size) <= 96):
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index}.font_size "
                    f"must be a number between 6 and 96.",
                    output_path,
                ),
                0,
            )
        color = item.get("color")
        if color is not None and not _is_pptx_v2_color(color):
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} bullets element {element_index} item {item_index}.color "
                    f"must be #RRGGBB or RRGGBB.",
                    output_path,
                ),
                0,
            )
    return None, len(items)


def _validate_pptx_v2_paragraph(
    slide_index: int, element_index: int, element: dict[str, Any], output_path: str
) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PPTX_V2_PARAGRAPH_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} paragraph element {element_index} has unsupported fields: "
            f"{', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_PARAGRAPH_FIELDS),
        )
    text = element.get("text")
    if not isinstance(text, str) or not text.strip():
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} paragraph element {element_index}.text must be a non-empty string.",
            output_path,
        )
    for flag in ("bold", "italic"):
        value = element.get(flag)
        if value is not None and not isinstance(value, bool):
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} paragraph element {element_index}.{flag} must be a boolean.",
                output_path,
            )
    font_size = element.get("font_size")
    if font_size is not None and (not _is_pptx_v2_number(font_size) or not 6 <= float(font_size) <= 96):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} paragraph element {element_index}.font_size must be a number "
            f"between 6 and 96.",
            output_path,
        )
    color = element.get("color")
    if color is not None and not _is_pptx_v2_color(color):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} paragraph element {element_index}.color must be #RRGGBB or RRGGBB.",
            output_path,
        )
    alignment = element.get("alignment")
    if alignment is not None and (not isinstance(alignment, str) or alignment.casefold() not in PPTX_V2_ALIGNMENTS):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} paragraph element {element_index}.alignment must be left, center or right.",
            output_path,
        )
    return None


def _validate_pptx_v2_table(
    slide_index: int, element_index: int, element: dict[str, Any], output_path: str
) -> tuple[dict[str, Any] | None, int]:
    unknown = sorted(str(key) for key in element if str(key) not in PPTX_V2_TABLE_FIELDS)
    if unknown:
        return (
            _pptx_v2_failure(
                f"create_pptx slide {slide_index} table element {element_index} has unsupported fields: "
                f"{', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(PPTX_V2_TABLE_FIELDS),
            ),
            0,
        )
    rows = element.get("rows")
    if not isinstance(rows, list) or not rows:
        return (
            _pptx_v2_failure(
                f"create_pptx slide {slide_index} table element {element_index}.rows must be a non-empty list.",
                output_path,
            ),
            0,
        )
    header_row = element.get("header_row")
    if header_row is not None and not isinstance(header_row, bool):
        return (
            _pptx_v2_failure(
                f"create_pptx slide {slide_index} table element {element_index}.header_row must be a boolean.",
                output_path,
            ),
            0,
        )
    cell_count = 0
    column_count: int | None = None
    for row_index, row in enumerate(rows, start=1):
        if not _is_scalar_row(row):
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} table element {element_index} row {row_index} must be a list "
                    f"of scalar cells.",
                    output_path,
                ),
                0,
            )
        if column_count is None:
            column_count = len(row)
        elif len(row) != column_count:
            return (
                _pptx_v2_failure(
                    f"create_pptx slide {slide_index} table element {element_index} rows must all share the same "
                    f"column count.",
                    output_path,
                ),
                0,
            )
        cell_count += len(row)
    return None, cell_count


def _validate_pptx_v2_image_element(
    slide_index: int, element_index: int, element: dict[str, Any], output_path: str
) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PPTX_V2_IMAGE_ELEMENT_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} image element {element_index} has unsupported fields: "
            f"{', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_IMAGE_ELEMENT_FIELDS),
        )
    return _validate_pptx_v2_image_path_block(
        f"slide {slide_index} image element {element_index}",
        element,
        output_path,
        require_path=True,
    )


def _validate_pptx_v2_slide_image(
    slide_index: int, image_spec: dict[str, Any], output_path: str
) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in image_spec if str(key) not in PPTX_V2_SLIDE_IMAGE_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} image has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_SLIDE_IMAGE_FIELDS),
        )
    return _validate_pptx_v2_image_path_block(
        f"slide {slide_index} image", image_spec, output_path, require_path=True
    )


def _validate_pptx_v2_image_path_block(
    label: str, spec: dict[str, Any], output_path: str, *, require_path: bool
) -> dict[str, Any] | None:
    image_path = spec.get("path")
    if image_path is None and require_path:
        return _pptx_v2_failure(f"create_pptx {label} requires a path.", output_path)
    if image_path is not None:
        path_error = _validate_pptx_v2_image_path_string(label, image_path, output_path)
        if path_error is not None:
            return path_error
    align = spec.get("align", "left")
    if not isinstance(align, str) or align.casefold() not in PPTX_V2_ALIGNMENTS:
        return _pptx_v2_failure(
            f"create_pptx {label}.align must be left, center or right.", output_path
        )
    for field_name in ("width_mm", "height_mm"):
        value = spec.get(field_name)
        if value is not None and (not _is_pptx_v2_number(value) or not 1 <= float(value) <= 600):
            return _pptx_v2_failure(
                f"create_pptx {label}.{field_name} must be a number between 1 and 600.",
                output_path,
            )
    return None


def _validate_pptx_v2_image_path_string(
    label: str, raw_path: Any, output_path: str
) -> dict[str, Any] | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return _pptx_v2_failure(f"create_pptx {label}.path must be a non-empty string.", output_path)
    text = raw_path.strip()
    if _looks_like_external_url(text):
        return _pptx_v2_failure(
            f"create_pptx {label}.path must not be an external URL.",
            output_path,
            error_category="external_url_rejected",
        )
    # Reject URL-like schemes (e.g. http:foo, ftp:foo, custom:foo). URL schemes
    # are at least two characters; a Windows drive letter (e.g. ``C:\foo``) has
    # exactly one alpha character before the colon and falls through to the
    # absolute-path rejection below.
    if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]+:", text):
        return _pptx_v2_failure(
            f"create_pptx {label}.path must be a workspace-relative path, not a URL.",
            output_path,
            error_category="external_url_rejected",
        )
    if text.startswith("\\\\") or text.startswith("//"):
        return _pptx_v2_failure(
            f"create_pptx {label}.path must not be a UNC network path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    # Drive-letter (``C:\foo``) and POSIX absolute (``/foo``) paths are both rejected.
    if re.match(r"^[A-Za-z]:[\\/]", text) or text.startswith("/") or text.startswith("\\"):
        return _pptx_v2_failure(
            f"create_pptx {label}.path must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    if Path(text).is_absolute():
        return _pptx_v2_failure(
            f"create_pptx {label}.path must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    source_error = _validate_document_source_field("create_pptx", text, field_name=f"content.{label}.path")
    if source_error is not None:
        return source_error
    if Path(text).suffix.casefold() not in PPTX_V2_IMAGE_SUFFIXES:
        return _pptx_v2_failure(
            f"create_pptx {label}.path must use .png, .jpg or .jpeg.",
            output_path,
            error_category="unsupported_extension",
        )
    return None


def _is_pptx_v2_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_pptx_v2_color(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", value.strip()) is not None


def _validate_pptx_v2_text_box(
    slide_index: int, element_index: int, element: dict[str, Any], output_path: str
) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PPTX_V2_TEXT_BOX_FIELDS)
    if unknown:
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index} has unsupported fields: "
            f"{', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PPTX_V2_TEXT_BOX_FIELDS),
        )
    text = element.get("text")
    if not isinstance(text, str) or not text.strip():
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index}.text must be a non-empty string.",
            output_path,
        )
    for field_name in ("left_mm", "top_mm", "width_mm"):
        value = element.get(field_name)
        if value is None:
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} text_box element {element_index} requires {field_name}.",
                output_path,
            )
        if not _is_pptx_v2_number(value) or not 0 <= float(value) <= 1200:
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} text_box element {element_index}.{field_name} must be a number "
                f"between 0 and 1200.",
                output_path,
            )
    height_mm = element.get("height_mm")
    if height_mm is not None and (not _is_pptx_v2_number(height_mm) or not 1 <= float(height_mm) <= 1200):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index}.height_mm must be a number "
            f"between 1 and 1200.",
            output_path,
        )
    for flag in ("bold", "italic"):
        value = element.get(flag)
        if value is not None and not isinstance(value, bool):
            return _pptx_v2_failure(
                f"create_pptx slide {slide_index} text_box element {element_index}.{flag} must be a boolean.",
                output_path,
            )
    font_size = element.get("font_size")
    if font_size is not None and (not _is_pptx_v2_number(font_size) or not 6 <= float(font_size) <= 96):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index}.font_size must be a number "
            f"between 6 and 96.",
            output_path,
        )
    color = element.get("color")
    if color is not None and not _is_pptx_v2_color(color):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index}.color must be #RRGGBB or RRGGBB.",
            output_path,
        )
    alignment = element.get("alignment")
    if alignment is not None and (not isinstance(alignment, str) or alignment.casefold() not in PPTX_V2_ALIGNMENTS):
        return _pptx_v2_failure(
            f"create_pptx slide {slide_index} text_box element {element_index}.alignment must be left, center or right.",
            output_path,
        )
    return None


def _pptx_v2_failure(
    reason: str,
    output_path: str,
    *,
    error_category: str = "validation_error",
    unsupported_fields: list[str] | None = None,
    accepted_fields: list[str] | None = None,
) -> dict[str, Any]:
    return _document_operation_failure(
        "create_pptx",
        reason,
        PPTX_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category=error_category,
        extra={
            "accepted_fields": accepted_fields or sorted(PPTX_V2_TOP_LEVEL_FIELDS),
            "unsupported_fields": unsupported_fields or [],
        },
    )


# ---------------------------------------------------------------------------
# PDF Creation V2 contract validation
# ---------------------------------------------------------------------------


def _validate_create_pdf_contract(content: dict[str, Any], input_path: Any, output_path: str) -> dict[str, Any] | None:
    has_input_path = isinstance(input_path, str) and bool(input_path.strip())
    has_inline_content = bool(content)
    accepted_fields = sorted(PDF_V2_TOP_LEVEL_FIELDS | {"title", "lines"})
    if has_input_path:
        input_error = _validate_document_path_field(
            "create_pdf", input_path, field_name="input_path", expected_suffix=".json"
        )
        if input_error is not None:
            return input_error
        if has_inline_content:
            return _pdf_v2_failure(
                "create_pdf accepts either input_path or inline content, not both.",
                output_path,
                accepted_fields=accepted_fields,
            )
        return None

    if not has_inline_content:
        return _pdf_v2_failure(
            "create_pdf requires inline content or input_path.",
            output_path,
            accepted_fields=accepted_fields,
        )
    if _is_pdf_v2_spec(content):
        return _validate_pdf_v2_content(content, output_path)

    content_error = _validate_document_content("create_pdf", content)
    if content_error is None:
        return None
    unsupported_fields = sorted(str(key) for key in content if str(key) not in {"title", "lines"})
    return _document_operation_failure(
        "create_pdf",
        content_error,
        PDF_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category="validation_error",
        extra={
            "accepted_fields": sorted({"title", "lines"}),
            "unsupported_fields": unsupported_fields,
        },
    )


def _is_pdf_v2_spec(content: dict[str, Any]) -> bool:
    return any(key in content for key in ("schema_version", "document", "page", "styles", "content"))


def _validate_pdf_v2_content(content: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown_top = sorted(str(key) for key in content if str(key) not in PDF_V2_TOP_LEVEL_FIELDS)
    if unknown_top:
        return _pdf_v2_failure(
            f"create_pdf content has unsupported fields: {', '.join(unknown_top)}.",
            output_path,
            unsupported_fields=unknown_top,
            accepted_fields=sorted(PDF_V2_TOP_LEVEL_FIELDS),
        )

    schema_version = content.get("schema_version", PDF_V2_SCHEMA_VERSION)
    if not isinstance(schema_version, str) or schema_version not in PDF_V2_SUPPORTED_SCHEMA_VERSIONS:
        return _pdf_v2_failure(
            f"create_pdf schema_version must be one of: {', '.join(sorted(PDF_V2_SUPPORTED_SCHEMA_VERSIONS))}.",
            output_path,
        )

    document_meta = content.get("document")
    if document_meta is not None:
        if not isinstance(document_meta, dict):
            return _pdf_v2_failure("create_pdf document must be an object.", output_path)
        unknown = sorted(str(key) for key in document_meta if str(key) not in PDF_V2_DOCUMENT_FIELDS)
        if unknown:
            return _pdf_v2_failure(
                f"create_pdf document has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(PDF_V2_DOCUMENT_FIELDS),
            )
        for field_name in PDF_V2_DOCUMENT_FIELDS:
            value = document_meta.get(field_name)
            if value is not None and not isinstance(value, str):
                return _pdf_v2_failure(f"create_pdf document.{field_name} must be a string.", output_path)

    page_error = _validate_pdf_v2_page(content.get("page"), output_path)
    if page_error is not None:
        return page_error
    styles_error = _validate_pdf_v2_styles(content.get("styles"), output_path)
    if styles_error is not None:
        return styles_error

    elements = content.get("content")
    if not isinstance(elements, list) or not elements:
        return _pdf_v2_failure("create_pdf content.content must be a non-empty list of elements.", output_path)
    if len(elements) > PDF_V2_MAX_CONTENT_ELEMENTS:
        return _pdf_v2_failure(
            f"create_pdf supports at most {PDF_V2_MAX_CONTENT_ELEMENTS} content elements.",
            output_path,
            error_category="limit_exceeded",
        )

    paragraph_count = 0
    table_count = 0
    table_cells = 0
    image_count = 0
    for index, element in enumerate(elements, start=1):
        if not isinstance(element, dict):
            return _pdf_v2_failure(f"create_pdf content element {index} must be an object.", output_path)
        element_type = element.get("type")
        if not isinstance(element_type, str) or element_type not in PDF_V2_CONTENT_TYPES:
            return _pdf_v2_failure(
                f"create_pdf content element {index}.type must be one of: {', '.join(sorted(PDF_V2_CONTENT_TYPES))}.",
                output_path,
            )
        if element_type in PDF_V2_TEXT_TYPES:
            paragraph_count += 1
            error = _validate_pdf_v2_text_element(index, element_type, element, output_path)
            if error is not None:
                return error
        elif element_type in {"bullet_list", "numbered_list"}:
            error = _validate_pdf_v2_list_element(index, element_type, element, output_path)
            if error is not None:
                return error
            paragraph_count += len(element["items"])
        elif element_type == "page_break":
            unknown = sorted(str(key) for key in element if str(key) != "type")
            if unknown:
                return _pdf_v2_failure(
                    f"create_pdf page_break element {index} has unsupported fields: {', '.join(unknown)}.",
                    output_path,
                    unsupported_fields=unknown,
                    accepted_fields=["type"],
                )
        elif element_type == "image":
            image_count += 1
            error = _validate_pdf_v2_image_element(index, element, output_path)
            if error is not None:
                return error
        elif element_type == "table":
            table_count += 1
            error = _validate_pdf_v2_table_element(index, element, output_path)
            if error is not None:
                return error
            rows = element["rows"]
            table_cells += sum(len(row) for row in rows if isinstance(row, list))

    if paragraph_count > PDF_V2_MAX_PARAGRAPHS:
        return _pdf_v2_failure(
            f"create_pdf supports at most {PDF_V2_MAX_PARAGRAPHS} paragraph-like elements.",
            output_path,
            error_category="limit_exceeded",
        )
    if table_count > PDF_V2_MAX_TABLES:
        return _pdf_v2_failure(
            f"create_pdf supports at most {PDF_V2_MAX_TABLES} tables.",
            output_path,
            error_category="limit_exceeded",
        )
    if table_cells > PDF_V2_MAX_TABLE_CELLS:
        return _pdf_v2_failure(
            f"create_pdf supports at most {PDF_V2_MAX_TABLE_CELLS} table cells.",
            output_path,
            error_category="limit_exceeded",
        )
    if image_count > PDF_V2_MAX_IMAGES:
        return _pdf_v2_failure(
            f"create_pdf supports at most {PDF_V2_MAX_IMAGES} images.",
            output_path,
            error_category="limit_exceeded",
        )
    return None


def _validate_pdf_v2_page(page: Any, output_path: str) -> dict[str, Any] | None:
    if page is None:
        return None
    if not isinstance(page, dict):
        return _pdf_v2_failure("create_pdf page must be an object.", output_path)
    unknown = sorted(str(key) for key in page if str(key) not in PDF_V2_PAGE_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf page has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_PAGE_FIELDS),
        )
    size_error = _validate_pdf_v2_page_size(page.get("size", "A4"), output_path)
    if size_error is not None:
        return size_error
    orientation = page.get("orientation", "portrait")
    if not isinstance(orientation, str) or orientation.casefold() not in PDF_V2_ORIENTATIONS:
        return _pdf_v2_failure("create_pdf page.orientation must be portrait or landscape.", output_path)
    margins = page.get("margins_mm")
    if margins is not None:
        if not isinstance(margins, dict):
            return _pdf_v2_failure("create_pdf page.margins_mm must be an object.", output_path)
        unknown_margins = sorted(str(key) for key in margins if str(key) not in PDF_V2_MARGIN_FIELDS)
        if unknown_margins:
            return _pdf_v2_failure(
                f"create_pdf margins_mm has unsupported fields: {', '.join(unknown_margins)}.",
                output_path,
                unsupported_fields=unknown_margins,
                accepted_fields=sorted(PDF_V2_MARGIN_FIELDS),
            )
        for field_name, value in margins.items():
            if not _is_pdf_v2_number(value) or not 0 <= float(value) <= 100:
                return _pdf_v2_failure(
                    f"create_pdf page.margins_mm.{field_name} must be a number between 0 and 100.",
                    output_path,
                )
    return None


def _validate_pdf_v2_page_size(value: Any, output_path: str) -> dict[str, Any] | None:
    if isinstance(value, str):
        if value.upper() not in PDF_V2_PAGE_SIZES:
            return _pdf_v2_failure("create_pdf page.size must be A4 or A5 (or a custom object).", output_path)
        return None
    if isinstance(value, dict):
        unknown = sorted(str(key) for key in value if str(key) not in PDF_V2_CUSTOM_SIZE_FIELDS)
        if unknown:
            return _pdf_v2_failure(
                f"create_pdf page.size has unsupported fields: {', '.join(unknown)}.",
                output_path,
                unsupported_fields=unknown,
                accepted_fields=sorted(PDF_V2_CUSTOM_SIZE_FIELDS),
            )
        name = value.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip() or len(name) > 50):
            return _pdf_v2_failure(
                "create_pdf page.size.name must be a non-empty string up to 50 characters.",
                output_path,
            )
        for field_name in ("width_mm", "height_mm"):
            number = value.get(field_name)
            if not _is_pdf_v2_number(number) or not PDF_V2_CUSTOM_SIZE_MIN_MM <= float(number) <= PDF_V2_CUSTOM_SIZE_MAX_MM:
                return _pdf_v2_failure(
                    f"create_pdf page.size.{field_name} must be a number between "
                    f"{PDF_V2_CUSTOM_SIZE_MIN_MM} and {PDF_V2_CUSTOM_SIZE_MAX_MM}.",
                    output_path,
                )
        return None
    return _pdf_v2_failure(
        "create_pdf page.size must be A4, A5, or a custom object with width_mm/height_mm.",
        output_path,
    )


def _validate_pdf_v2_styles(styles: Any, output_path: str) -> dict[str, Any] | None:
    if styles is None:
        return None
    if not isinstance(styles, dict):
        return _pdf_v2_failure("create_pdf styles must be an object.", output_path)
    unknown_styles = sorted(str(key) for key in styles if str(key) not in PDF_V2_STYLE_NAMES)
    if unknown_styles:
        return _pdf_v2_failure(
            f"create_pdf styles has unsupported style names: {', '.join(unknown_styles)}.",
            output_path,
            unsupported_fields=unknown_styles,
            accepted_fields=sorted(PDF_V2_STYLE_NAMES),
        )
    for style_name, style_spec in styles.items():
        if not isinstance(style_spec, dict):
            return _pdf_v2_failure(f"create_pdf styles.{style_name} must be an object.", output_path)
        style_error = _validate_pdf_v2_style_spec(f"styles.{style_name}", style_spec, output_path)
        if style_error is not None:
            return style_error
    return None


def _validate_pdf_v2_style_spec(path: str, style_spec: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in style_spec if str(key) not in PDF_V2_STYLE_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf {path} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_STYLE_FIELDS),
        )
    for field_name, value in style_spec.items():
        if field_name == "font":
            if not isinstance(value, str) or not value.strip() or len(value) > 100:
                return _pdf_v2_failure(
                    f"create_pdf {path}.font must be a non-empty string up to 100 characters.",
                    output_path,
                )
        elif field_name == "size_pt":
            if not _is_pdf_v2_number(value) or not 1 <= float(value) <= 96:
                return _pdf_v2_failure(f"create_pdf {path}.size_pt must be a number between 1 and 96.", output_path)
        elif field_name in {"bold", "italic", "underline", "page_break_before"}:
            if not isinstance(value, bool):
                return _pdf_v2_failure(f"create_pdf {path}.{field_name} must be a boolean.", output_path)
        elif field_name == "alignment":
            if not isinstance(value, str) or value.casefold() not in PDF_V2_ALIGNMENTS:
                return _pdf_v2_failure(
                    f"create_pdf {path}.alignment must be left, center, right or justify.",
                    output_path,
                )
        elif field_name == "line_spacing":
            if not _is_pdf_v2_number(value) or not 0.5 <= float(value) <= 3:
                return _pdf_v2_failure(f"create_pdf {path}.line_spacing must be a number between 0.5 and 3.", output_path)
        elif field_name in {"space_before_pt", "space_after_pt"}:
            if not _is_pdf_v2_number(value) or not 0 <= float(value) <= 144:
                return _pdf_v2_failure(
                    f"create_pdf {path}.{field_name} must be a number between 0 and 144.",
                    output_path,
                )
        elif field_name == "first_line_indent_mm":
            if not _is_pdf_v2_number(value) or not 0 <= float(value) <= 50:
                return _pdf_v2_failure(
                    f"create_pdf {path}.first_line_indent_mm must be a number between 0 and 50.",
                    output_path,
                )
    return None


def _validate_pdf_v2_text_element(index: int, element_type: str, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PDF_V2_TEXT_ELEMENT_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf {element_type} element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_TEXT_ELEMENT_FIELDS),
        )
    has_text = "text" in element
    has_runs = "runs" in element
    if has_text and has_runs:
        return _pdf_v2_failure(
            f"create_pdf {element_type} element {index} must use either text or runs, not both.",
            output_path,
        )
    if not has_text and not has_runs:
        return _pdf_v2_failure(
            f"create_pdf {element_type} element {index} requires text or runs.",
            output_path,
        )
    if has_text:
        text = element.get("text")
        if not isinstance(text, str):
            return _pdf_v2_failure(f"create_pdf {element_type} element {index}.text must be a string.", output_path)
        if element_type != "paragraph" and not text.strip():
            return _pdf_v2_failure(
                f"create_pdf {element_type} element {index}.text must not be empty.", output_path
            )
    if has_runs:
        runs = element.get("runs")
        if not isinstance(runs, list) or not runs:
            return _pdf_v2_failure(
                f"create_pdf {element_type} element {index}.runs must be a non-empty list.", output_path
            )
        for run_index, run in enumerate(runs, start=1):
            run_error = _validate_pdf_v2_run(index, run_index, run, output_path)
            if run_error is not None:
                return run_error
    style_name = element.get("style")
    if style_name is not None and (not isinstance(style_name, str) or style_name not in PDF_V2_STYLE_NAMES):
        return _pdf_v2_failure(f"create_pdf {element_type} element {index}.style is not supported.", output_path)
    style_overrides = element.get("style_overrides")
    if style_overrides is not None:
        if not isinstance(style_overrides, dict):
            return _pdf_v2_failure(
                f"create_pdf {element_type} element {index}.style_overrides must be an object.", output_path
            )
        return _validate_pdf_v2_style_spec(f"content[{index}].style_overrides", style_overrides, output_path)
    return None


def _validate_pdf_v2_run(element_index: int, run_index: int, run: Any, output_path: str) -> dict[str, Any] | None:
    if not isinstance(run, dict):
        return _pdf_v2_failure(
            f"create_pdf content element {element_index} run {run_index} must be an object.", output_path
        )
    unknown = sorted(str(key) for key in run if str(key) not in PDF_V2_RUN_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf content element {element_index} run {run_index} has unsupported fields: "
            f"{', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_RUN_FIELDS),
        )
    if not isinstance(run.get("text"), str):
        return _pdf_v2_failure(
            f"create_pdf content element {element_index} run {run_index}.text must be a string.", output_path
        )
    for field_name in ("bold", "italic", "underline"):
        value = run.get(field_name)
        if value is not None and not isinstance(value, bool):
            return _pdf_v2_failure(
                f"create_pdf content element {element_index} run {run_index}.{field_name} must be a boolean.",
                output_path,
            )
    return None


def _validate_pdf_v2_list_element(index: int, element_type: str, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PDF_V2_LIST_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf {element_type} element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_LIST_FIELDS),
        )
    items = element.get("items")
    if not isinstance(items, list) or not items:
        return _pdf_v2_failure(
            f"create_pdf {element_type} element {index}.items must be a non-empty list of strings.", output_path
        )
    for item_index, item in enumerate(items, start=1):
        if not isinstance(item, str) or not item.strip():
            return _pdf_v2_failure(
                f"create_pdf {element_type} element {index} item {item_index} must be a non-empty string.",
                output_path,
            )
    style_overrides = element.get("style_overrides")
    if style_overrides is not None:
        if not isinstance(style_overrides, dict):
            return _pdf_v2_failure(
                f"create_pdf {element_type} element {index}.style_overrides must be an object.", output_path
            )
        return _validate_pdf_v2_style_spec(f"content[{index}].style_overrides", style_overrides, output_path)
    return None


def _validate_pdf_v2_image_element(index: int, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PDF_V2_IMAGE_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf image element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_IMAGE_FIELDS),
        )
    image_path = element.get("path")
    path_error = _validate_pdf_v2_image_path_string(
        f"content element {index}.path", image_path, output_path
    )
    if path_error is not None:
        return path_error
    align = element.get("align", "left")
    if not isinstance(align, str) or align.casefold() not in {"left", "center", "right"}:
        return _pdf_v2_failure("create_pdf image align must be left, center or right.", output_path)
    for field_name in ("width_mm", "height_mm"):
        value = element.get(field_name)
        if value is not None and (not _is_pdf_v2_number(value) or not 1 <= float(value) <= 600):
            return _pdf_v2_failure(
                f"create_pdf image {field_name} must be a number between 1 and 600.",
                output_path,
            )
    return None


def _validate_pdf_v2_table_element(index: int, element: dict[str, Any], output_path: str) -> dict[str, Any] | None:
    unknown = sorted(str(key) for key in element if str(key) not in PDF_V2_TABLE_FIELDS)
    if unknown:
        return _pdf_v2_failure(
            f"create_pdf table element {index} has unsupported fields: {', '.join(unknown)}.",
            output_path,
            unsupported_fields=unknown,
            accepted_fields=sorted(PDF_V2_TABLE_FIELDS),
        )
    rows = element.get("rows")
    if not isinstance(rows, list) or not rows:
        return _pdf_v2_failure(f"create_pdf table element {index}.rows must be a non-empty list.", output_path)
    header_row = element.get("header_row")
    if header_row is not None and not isinstance(header_row, bool):
        return _pdf_v2_failure(f"create_pdf table element {index}.header_row must be a boolean.", output_path)
    column_count: int | None = None
    for row_index, row in enumerate(rows, start=1):
        if not _is_scalar_row(row):
            return _pdf_v2_failure(
                f"create_pdf table element {index} row {row_index} must be a list of scalar cells.",
                output_path,
            )
        if column_count is None:
            column_count = len(row)
        elif len(row) != column_count:
            return _pdf_v2_failure(
                f"create_pdf table element {index} rows must all share the same column count.",
                output_path,
            )
    return None


def _validate_pdf_v2_image_path_string(label: str, raw_path: Any, output_path: str) -> dict[str, Any] | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return _pdf_v2_failure(f"create_pdf {label} must be a non-empty string.", output_path)
    text = raw_path.strip()
    if _looks_like_external_url(text):
        return _pdf_v2_failure(
            f"create_pdf {label} must not be an external URL.",
            output_path,
            error_category="external_url_rejected",
        )
    if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]+:", text):
        return _pdf_v2_failure(
            f"create_pdf {label} must be a workspace-relative path, not a URL.",
            output_path,
            error_category="external_url_rejected",
        )
    if text.startswith("\\\\") or text.startswith("//"):
        return _pdf_v2_failure(
            f"create_pdf {label} must not be a UNC network path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    if re.match(r"^[A-Za-z]:[\\/]", text) or text.startswith("/") or text.startswith("\\"):
        return _pdf_v2_failure(
            f"create_pdf {label} must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    if Path(text).is_absolute():
        return _pdf_v2_failure(
            f"create_pdf {label} must be a workspace-relative path.",
            output_path,
            error_category="absolute_path_rejected",
        )
    source_error = _validate_document_source_field("create_pdf", text, field_name=f"content.{label}")
    if source_error is not None:
        return source_error
    if Path(text).suffix.casefold() not in PDF_V2_IMAGE_SUFFIXES:
        return _pdf_v2_failure(
            f"create_pdf {label} must use .png, .jpg or .jpeg.",
            output_path,
            error_category="unsupported_extension",
        )
    return None


def _is_pdf_v2_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _pdf_v2_failure(
    reason: str,
    output_path: str,
    *,
    error_category: str = "validation_error",
    unsupported_fields: list[str] | None = None,
    accepted_fields: list[str] | None = None,
) -> dict[str, Any]:
    return _document_operation_failure(
        "create_pdf",
        reason,
        PDF_V2_REQUIREMENT_IDS,
        output_path=output_path,
        error_category=error_category,
        extra={
            "accepted_fields": accepted_fields or sorted(PDF_V2_TOP_LEVEL_FIELDS),
            "unsupported_fields": unsupported_fields or [],
        },
    )


def _validate_document_content(operation: str, content: dict[str, Any]) -> str | None:
    allowed_fields = {
        "create_docx": {"title", "paragraphs", "table"},
        "create_xlsx": {"sheet_name", "rows"},
        "create_pptx": {"title", "slides"},
        "create_pdf": {"title", "lines"},
    }.get(operation, set())
    unknown_fields = sorted(str(key) for key in content if str(key) not in allowed_fields)
    if unknown_fields:
        return f"{operation} content has unsupported fields: {', '.join(unknown_fields)}."
    if operation == "create_docx":
        if not isinstance(content.get("title"), str) or not content["title"].strip():
            return "create_docx content.title is required."
        paragraphs = content.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs or not all(isinstance(item, str) for item in paragraphs):
            return "create_docx content.paragraphs must be a non-empty list of strings."
        table = content.get("table")
        if table is not None and not _is_string_table(table):
            return "create_docx content.table must be a list of string rows."
    elif operation == "create_xlsx":
        if not isinstance(content.get("sheet_name"), str) or not content["sheet_name"].strip():
            return "create_xlsx content.sheet_name is required."
        rows = content.get("rows")
        if not isinstance(rows, list) or not rows or not all(_is_scalar_row(row) for row in rows):
            return "create_xlsx content.rows must be a non-empty list of scalar rows."
    elif operation == "create_pptx":
        if not isinstance(content.get("title"), str) or not content["title"].strip():
            return "create_pptx content.title is required."
        slide_error = _validate_pptx_slide_payloads(content.get("slides"))
        if slide_error is not None:
            return slide_error
    elif operation == "create_pdf":
        if not isinstance(content.get("title"), str) or not content["title"].strip():
            return "create_pdf content.title is required."
        lines = content.get("lines")
        if not isinstance(lines, list) or not lines or not all(isinstance(item, str) for item in lines):
            return "create_pdf content.lines must be a non-empty list of strings."
    if _contains_active_string(content, allow_formula_literals=operation == "create_xlsx"):
        return "Formulas, macros, raw XML, raw HTML/CSS and active content are not supported."
    return None


def _is_string_table(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(row, list) and all(isinstance(cell, str) for cell in row) for row in value)


def _is_scalar_row(value: Any) -> bool:
    return isinstance(value, list) and all(item is None or isinstance(item, (str, int, float, bool)) for item in value)


def _is_slide_payload(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("title"), str)
        and isinstance(value.get("bullets"), list)
        and all(isinstance(item, str) for item in value["bullets"])
    )


def _validate_pptx_slide_payloads(value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return "create_pptx content.slides must be a non-empty list of slide objects."
    for index, slide in enumerate(value, start=1):
        if not isinstance(slide, dict):
            return f"create_pptx slide {index} must be an object."
        unknown_fields = sorted(str(key) for key in slide if str(key) not in {"title", "bullets"})
        if unknown_fields:
            return f"create_pptx slide {index} has unsupported fields: {', '.join(unknown_fields)}."
        if not isinstance(slide.get("title"), str) or not slide["title"].strip():
            return f"create_pptx slide {index}.title is required."
        bullets = slide.get("bullets")
        if not isinstance(bullets, list) or not all(isinstance(item, str) for item in bullets):
            return f"create_pptx slide {index}.bullets must be a list of strings."
    return None


def _contains_active_string(value: Any, *, allow_formula_literals: bool = False) -> bool:
    if isinstance(value, str):
        stripped = value.lstrip().casefold()
        formula_like = stripped.startswith("=") and not allow_formula_literals
        return formula_like or "<script" in stripped or "<?xml" in stripped or "<!doctype html" in stripped
    if isinstance(value, list):
        return any(_contains_active_string(item, allow_formula_literals=allow_formula_literals) for item in value)
    if isinstance(value, dict):
        return any(_contains_active_string(item, allow_formula_literals=allow_formula_literals) for item in value.values())
    return False


def _document_title_and_body(operation: str, content: dict[str, Any]) -> tuple[str, str]:
    document_meta = content.get("document") if isinstance(content.get("document"), dict) else {}
    workbook_meta = content.get("workbook") if isinstance(content.get("workbook"), dict) else {}
    presentation_meta = content.get("presentation") if isinstance(content.get("presentation"), dict) else {}
    title = str(
        content.get("title")
        or content.get("sheet_name")
        or document_meta.get("title")
        or workbook_meta.get("title")
        or presentation_meta.get("title")
        or "PLwC Document"
    )
    if operation == "create_docx":
        if isinstance(content.get("content"), list):
            body = "\n".join(_docx_v2_element_text(item) for item in content["content"] if isinstance(item, dict))
        else:
            body = "\n".join(str(item) for item in content.get("paragraphs", []))
    elif operation == "create_xlsx":
        if isinstance(content.get("sheets"), list):
            body = f"Sheets: {len(content['sheets'])}"
        else:
            body = f"Rows: {len(content.get('rows', []))}"
    elif operation == "create_pptx":
        body = f"Slides: {len(content.get('slides', []))}"
    elif operation == "create_pdf":
        if isinstance(content.get("content"), list):
            body = "\n".join(_pdf_v2_element_text(item) for item in content["content"] if isinstance(item, dict))
        else:
            body = "\n".join(str(item) for item in content.get("lines", []))
    else:
        body = ""
    return title, body


def _pdf_v2_element_text(element: dict[str, Any]) -> str:
    if isinstance(element.get("text"), str):
        return element["text"]
    if isinstance(element.get("runs"), list):
        return "".join(str(run.get("text") or "") for run in element["runs"] if isinstance(run, dict))
    if isinstance(element.get("items"), list):
        return "\n".join(str(item) for item in element["items"] if isinstance(item, str))
    return ""


def _docx_v2_element_text(element: dict[str, Any]) -> str:
    if isinstance(element.get("text"), str):
        return element["text"]
    if isinstance(element.get("runs"), list):
        return "".join(str(run.get("text") or "") for run in element["runs"] if isinstance(run, dict))
    if isinstance(element.get("items"), list):
        return "\n".join(str(item) for item in element["items"] if isinstance(item, str))
    return ""


def _validate_workspace_path(value: Any, operation: str, *, role: str) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value.strip():
        return _workspace_operation_failure(
            operation,
            f"{role} must be a non-empty string.",
            ("FR-CMD-PUB-002", "NFR-002"),
            error_category="validation_error",
        )
    if _is_public_workspace_protected_path(value):
        return _workspace_operation_failure(
            operation,
            "Protected profile/governance paths require governed profile tools.",
            ("FR-CMD-PUB-003", "SR-004", "SR-010"),
            path=value if role == "path" else None,
            source_path=value if role == "source_path" else None,
            target_path=value if role == "target_path" else None,
            error_category="policy_denied",
            protected_boundary_decision="rejected",
        )
    return None


def _validate_optional_positive_int(operation: str, field_name: str, value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return _workspace_operation_failure(
            operation,
            f"{field_name} must be a positive integer.",
            ("FR-CMD-PUB-002", "FR-CMD-PUB-006", "NFR-002"),
            error_category="validation_error",
        )
    if value < 1:
        return _workspace_operation_failure(
            operation,
            f"{field_name} must be at least 1.",
            ("FR-CMD-PUB-002", "FR-CMD-PUB-006", "NFR-002"),
            error_category="validation_error",
        )
    return None


def _is_public_workspace_protected_path(path_value: str) -> bool:
    if is_protected_governance_path(path_value):
        return True
    protected_segments = {"governance", "profile", "profiles"}
    normalized = path_value.replace("\\", "/")
    return any(part.strip().casefold() in protected_segments for part in normalized.split("/"))


def _effective_positive_int(value: int | None, maximum: int) -> int:
    if value is None:
        return maximum
    return min(value, maximum)


def _looks_like_external_url(value: str) -> bool:
    text = value.strip().casefold()
    return "://" in text or text.startswith(("data:", "file:"))


def _validate_node_script_path(path: str) -> str | None:
    """Return an error message if path is not a safe workspace-relative .js path, else None."""
    if path.startswith("/") or path.startswith("\\") or re.match(r"^[A-Za-z]:[/\\]", path):
        return "Node script path must be a workspace-relative path, not an absolute path."
    if ".." in Path(path.replace("\\", "/")).parts:
        return "Node script path must not contain parent traversal (..)."
    if not path.lower().endswith(".js"):
        return "Node script path must be a workspace-relative .js file (e.g. scripts/build.js)."
    return None


def _valid_read_image_resize_to(value: str) -> bool:
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


def _workspace_exact_replace_payload(
    *,
    filesystem: SafeFilesystemAdapter,
    operation: str,
    path: str,
    old_text: str,
    new_text: str,
    expected_replacements: int,
    require_content_hash: str,
) -> dict[str, Any]:
    before = filesystem.read_text(path)
    if not before.ok:
        return _workspace_operation_payload(before, operation, path=path, read_files=())

    before_content = before.content or ""
    before_hash = _sha256_text(before_content)
    if require_content_hash and before_hash != require_content_hash.strip().casefold():
        return _workspace_operation_failure(
            operation,
            "Content hash precondition did not match.",
            ("FR-CMD-PUB-007", "NFR-002"),
            path=path,
            read_files=(path,),
            error_category="stale_precondition",
        ) | {"content_hash_before": before_hash}

    result = filesystem.replace_text(
        path,
        old_text,
        new_text,
        expected_replacements=expected_replacements,
    )
    payload = _workspace_operation_payload(
        result,
        operation,
        path=path,
        changed_files=(path,) if result.ok else (),
        read_files=(path,),
    )
    payload["content_hash_before"] = before_hash
    if result.ok:
        after = filesystem.read_text(path)
        if after.ok:
            payload["content_hash_after"] = _sha256_text(after.content or "")
    return payload


def _workspace_operation_audit_arguments(
    operation: str,
    *,
    path: str,
    content: str,
    content_base64: str,
    mode: str,
    depth: int,
    query: str,
    max_results: int | None,
    source_path: str,
    target_path: str,
    paths: list[str] | None,
    old_text: str,
    new_text: str,
    expected_replacements: int | None,
    overwrite: bool,
    max_files: int | None,
    max_bytes_per_file: int | None,
    max_total_bytes: int | None,
    max_bytes: int | None,
    require_content_hash: str,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "path": path or None,
        "content_length": len(content) if isinstance(content, str) else None,
        "content_base64_length": len(content_base64) if isinstance(content_base64, str) else None,
        "mode": mode if isinstance(mode, str) else None,
        "depth": depth,
        "query_length": len(query) if isinstance(query, str) else None,
        "max_results": max_results,
        "source_path": source_path or None,
        "target_path": target_path or None,
        "path_count": len(paths or ()),
        "old_text_length": len(old_text) if isinstance(old_text, str) else None,
        "new_text_length": len(new_text) if isinstance(new_text, str) else None,
        "expected_replacements": expected_replacements,
        "overwrite": overwrite,
        "max_files": max_files,
        "max_bytes_per_file": max_bytes_per_file,
        "max_total_bytes": max_total_bytes,
        "max_bytes": max_bytes,
        "content_hash_precondition": bool(require_content_hash),
    }


def _workspace_operation_payload(
    result: Any,
    operation: str,
    *,
    path: str | None = None,
    source_path: str | None = None,
    target_path: str | None = None,
    changed_files: tuple[str, ...] = (),
    read_files: tuple[str, ...] = (),
    error_category: str | None = None,
    protected_boundary_decision: str | None = None,
) -> dict[str, Any]:
    payload = _public_payload(result)
    payload["operation"] = operation
    if path:
        payload["path"] = path
    if source_path:
        payload["source_path"] = source_path
    if target_path:
        payload["target_path"] = target_path
    payload["decision"] = "allowed" if payload.get("ok") is True else "denied"
    payload["reason"] = "Operation completed." if payload.get("ok") is True else payload.get("error", "Operation denied.")
    payload["changed_files"] = list(changed_files)
    payload["read_files"] = list(read_files)
    payload["error_category"] = None if payload.get("ok") is True else error_category or _error_category(payload.get("error"))
    if protected_boundary_decision:
        payload["protected_boundary_decision"] = protected_boundary_decision
    elif "SR-004" in set(payload.get("requirement_ids") or ()):
        payload["protected_boundary_decision"] = "rejected"
    if isinstance(payload.get("files"), (list, tuple)):
        payload["byte_count"] = sum(int(item.get("size") or 0) for item in payload["files"] if isinstance(item, dict))
    return payload


def _document_operation_payload(
    result: Any,
    operation: str,
    *,
    output_path: str,
    input_path: str = "",
    input_paths: list[str] | None = None,
    output_dir: str = "",
    error_category: str | None = None,
) -> dict[str, Any]:
    raw_payload = _public_payload(result)
    ok = raw_payload.get("ok") is True
    changed_files = list(raw_payload.get("changed_files") or ())
    if ok and not changed_files and output_path:
        changed_files = [output_path]
    read_files = []
    if input_path:
        read_files.append(input_path)
    if input_paths:
        read_files.extend(input_paths)
    reason = "Document operation completed." if ok else raw_payload.get("error", "Document operation denied.")
    payload: dict[str, Any] = {
        "ok": ok,
        "operation": operation,
        "worker_image": raw_payload.get("worker_image", DOCUMENT_WORKER_IMAGE),
        "worker_mount": WORKER_CONTAINER_WORKDIR,
        "status": raw_payload.get("status", "created" if ok else "failed"),
        "policy_decision": PolicyDecision.ALLOW.value if ok else PolicyDecision.DENY.value,
        "decision": "allowed" if ok else "denied",
        "reason": reason,
        "changed_files": changed_files if ok else [],
        "read_files": read_files,
        "requirement_ids": list(raw_payload.get("requirement_ids") or DOCUMENT_OPERATION_REQUIREMENTS),
        "runtime": {
            "pull_policy": "never",
            "network": "none",
            "workspace_mount": WORKER_CONTAINER_WORKDIR,
            "runtime_pip": False,
        },
    }
    if output_path:
        payload["output_path"] = output_path
    if input_path:
        payload["input_path"] = input_path
    if input_paths:
        payload["input_paths"] = list(input_paths)
    if output_dir:
        payload["output_dir"] = output_dir
    for key in (
        "file_size",
        "output_file_size",
        "page_count",
        "output_page_count",
        "total_pages",
        "input_file_count",
        "selected_pages",
        "affected_pages",
        "created_files",
        "encrypted",
        "metadata",
        "rotation",
        "total_input_size",
        "extracted_pages",
        "char_count",
        "truncated",
        "page_scope_truncated",
        "no_text_found",
        "preview",
        "format",
        "entry_count",
        "file_entry_count",
        "directory_entry_count",
        "total_compressed_bytes",
        "total_uncompressed_bytes",
        "largest_entry",
        "compression_ratio",
        "encrypted_entries",
        "symlink_entries",
        "suspicious_entries",
        "path_validation_findings",
        "extraction_allowed",
        "limits",
        "created_file_count",
        "entries",
        "file_type",
        "paragraph_count",
        "table_count",
        "text_char_count",
        "warnings",
        "sheet_count",
        "sheet_names",
        "sheets",
        "total_row_count",
        "total_cell_count",
        "merged_range_count",
        "formula_present",
        "formula_count",
        "formula_policy",
        "extracted_cells",
        "slide_count",
        "text_shape_count",
        "embedded_media_count",
        "section_count",
        "no_text_found",
        "tables",
        "builder_version",
        "document_format",
        "content_element_count",
        "image_count",
        "input_file_size",
        "page_size",
        "orientation",
        "slide_size",
        "slide_width_mm",
        "slide_height_mm",
        "notes_slide_count",
        "bullet_item_count",
        "table_cell_count",
        "text_box_count",
        "accepted_fields",
        "unsupported_fields",
        "media_type",
        "width_px",
        "height_px",
        "file_size_bytes",
        "original_file_size_bytes",
        "source_file_size_bytes",
        "max_size_bytes",
        "resized",
        "image_data",
        "suggestion",
        "detected_extension",
        "supported_formats",
        "fallback_available",
    ):
        if raw_payload.get(key) is not None:
            payload[key] = raw_payload[key]
    if raw_payload.get("file_size") is not None:
        payload["file_size"] = raw_payload["file_size"]
    if not ok:
        payload["error"] = raw_payload.get("error", "Document operation denied.")
        payload["error_category"] = raw_payload.get("error_category") or error_category or _error_category(payload["error"])
    return payload


def _document_operation_mcp_response(payload: dict[str, Any]) -> Any:
    if payload.get("operation") != "read_image" or payload.get("ok") is not True:
        return payload
    image_data = payload.get("image_data")
    media_type = payload.get("media_type")
    if not isinstance(image_data, str) or not image_data or not isinstance(media_type, str) or not media_type:
        return payload
    text_payload = dict(payload)
    text_payload.pop("image_data", None)
    from mcp.types import ImageContent, TextContent

    return [
        TextContent(type="text", text=json.dumps(text_payload, sort_keys=True, indent=2)),
        ImageContent(type="image", data=image_data, mimeType=media_type),
    ]


def _document_operation_failure(
    operation: str,
    reason: str,
    requirement_ids: tuple[str, ...],
    *,
    output_path: str = "",
    error_category: str = "validation_error",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "operation": operation,
        "output_path": output_path,
        "worker_image": DOCUMENT_WORKER_IMAGE,
        "worker_mount": WORKER_CONTAINER_WORKDIR,
        "policy_decision": PolicyDecision.DENY.value,
        "decision": "denied",
        "reason": reason,
        "error": reason,
        "error_category": error_category,
        "changed_files": [],
        "requirement_ids": list(requirement_ids),
    }
    if extra:
        payload.update(extra)
    return payload


def _document_operation_audit_arguments(
    operation: str,
    *,
    output_path: str,
    input_path: str,
    input_paths: list[str] | None,
    output_dir: str,
    pages: list[int | str] | None,
    rotation: int | None,
    mode: str,
    output_format: str,
    max_pages: int | None,
    max_chars: int | None,
    include_preview: bool,
    max_preview_chars: int | None,
    sheets: list[str | int] | None,
    ranges: dict[str, str] | list[str] | None,
    slides: list[int | str] | None,
    include_notes: bool,
    max_rows: int | None,
    max_cells: int | None,
    max_size_kb: int | None,
    resize_to: str,
    content: Any,
    overwrite: bool,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "output_path": output_path,
        "input_path": input_path,
        "input_path_count": len(input_paths or ()),
        "output_dir": output_dir,
        "page_selector_count": len(pages or ()),
        "rotation": rotation,
        "mode": mode,
        "format": output_format,
        "max_pages": max_pages,
        "max_chars": max_chars,
        "include_preview": include_preview,
        "max_preview_chars": max_preview_chars,
        "sheet_selector_count": len(sheets or ()),
        "range_selector_count": len(ranges or {}) if isinstance(ranges, (dict, list)) else 0,
        "slide_selector_count": len(slides or ()),
        "include_notes": include_notes,
        "max_rows": max_rows,
        "max_cells": max_cells,
        "max_size_kb": max_size_kb,
        "resize_to": resize_to or None,
        "content_keys": sorted(str(key) for key in content) if isinstance(content, dict) else [],
        "overwrite": overwrite,
        "worker_image": DOCUMENT_WORKER_IMAGE,
    }


def _describe_validation_failure(
    scope: str,
    detail: str,
    output_format: str,
    reason: str,
    error_category: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": "describe",
        "scope": scope,
        "detail": detail,
        "format": output_format,
        "data": None,
        "error": reason,
        "error_category": error_category,
        "policy_decision": PolicyDecision.DENY.value,
        "requirement_ids": list(DESCRIBE_REQUIREMENTS),
    }


def _dispatch_validation_failure(
    tool_name: str,
    field_name: str,
    value: Any,
    supported_values: list[str],
) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": tool_name,
        "policy_decision": PolicyDecision.DENY.value,
        "error": f"{field_name} must be one of: {', '.join(supported_values)}.",
        "error_category": "validation_error",
        "dispatch_field": field_name,
        "dispatch_value": value,
        "supported_values": supported_values,
        "requirement_ids": list(FACADE_REQUIREMENTS),
    }


def _describe_tool_purposes() -> dict[str, str]:
    return {
        PUBLIC_STATUS_TOOL: (
            'Dispatch runtime, sandbox, first-run and Claude Desktop config status through scope; '
            'start onboarding with scope="first_run".'
        ),
        DESCRIBE_TOOL: "Describe public PLwC facade schemas, allowed operations and common denial reasons.",
        PROFILE_TOOL: "Dispatch profile status, snapshot, compile, retrieve, scan and doctor operations through operation.",
        REFLECTION_TOOL: "Write governed PBA2-compatible reflection entries through operation=write.",
        GOVERNOR_TOOL: (
            'Dispatch governed profile mutation, onboarding and promotion plan/apply operations; '
            'new profiles use plan_type="profile_creation" with onboarding_answers.'
        ),
        SANDBOX_RUN_TOOL: "Run bounded Python, shell or Node.js scripts inside the controlled Docker sandbox through lang.",
        WORKSPACE_OPERATION_TOOL: "Dispatch bounded governed workspace list/search/read/write/file-info/batch/move/copy/replace and binary read/write operations.",
        DOCUMENT_OPERATION_TOOL: "Create document artifacts and run bounded PDF, ZIP, image and Office inspect/extract operations through the governed document worker.",
    }


def _describe_data(scope: str, detail: str, config: GatewayConfig) -> dict[str, Any]:
    if scope == "tools":
        tool_purposes = _describe_tool_purposes()
        return {
            "public_server": PUBLIC_SERVER_NAME,
            "public_tool_count": len(PUBLIC_TOOLS),
            "tool_names": list(PUBLIC_TOOLS),
            "tools": [
                {"name": tool_name, "purpose": tool_purposes[tool_name]}
                for tool_name in PUBLIC_TOOLS
            ],
            "facade_refactor": {
                "from_public_tool_count": len(LEGACY_PUBLIC_TOOL_NAMES) + 3,
                "to_public_tool_count": len(PUBLIC_TOOLS),
                "old_individual_tool_names_public": False,
                "feature_expansion": False,
            },
            "dispatch": {
                PUBLIC_STATUS_TOOL: {"scope": sorted(SUPPORTED_STATUS_SCOPES)},
                PROFILE_TOOL: {"operation": sorted(SUPPORTED_PROFILE_OPERATIONS)},
                REFLECTION_TOOL: {"operation": sorted(SUPPORTED_REFLECTION_OPERATIONS)},
                GOVERNOR_TOOL: {"operation": sorted(SUPPORTED_GOVERNOR_OPERATIONS)},
                SANDBOX_RUN_TOOL: {"lang": sorted(SUPPORTED_SANDBOX_LANGS)},
                WORKSPACE_OPERATION_TOOL: {"operation": sorted(SUPPORTED_WORKSPACE_OPERATIONS)},
                DOCUMENT_OPERATION_TOOL: {"operation": sorted(SUPPORTED_DOCUMENT_OPERATIONS)},
            },
            "legacy_mapping": {
                "plwc_runtime_status": f"{PUBLIC_STATUS_TOOL}(scope=runtime)",
                "plwc_sandbox_status": f"{PUBLIC_STATUS_TOOL}(scope=sandbox)",
                "plwc_first_run_status": f"{PUBLIC_STATUS_TOOL}(scope=first_run)",
                "plwc_generate_claude_config": f"{PUBLIC_STATUS_TOOL}(scope=config)",
                "plwc_profile_status": f"{PROFILE_TOOL}(operation=status)",
                "plwc_profile_snapshot": f"{PROFILE_TOOL}(operation=snapshot)",
                "plwc_compile_profile": f"{PROFILE_TOOL}(operation=compile)",
                "plwc_write_reflection": f"{REFLECTION_TOOL}(operation=write)",
                "plwc_governor_plan": f"{GOVERNOR_TOOL}(operation=plan)",
                "plwc_governor_apply": f"{GOVERNOR_TOOL}(operation=apply)",
                "plwc_run_python_sandboxed": f"{SANDBOX_RUN_TOOL}(lang=python)",
                "plwc_run_shell_sandboxed": f"{SANDBOX_RUN_TOOL}(lang=shell)",
                "plwc_list_workspace": f"{WORKSPACE_OPERATION_TOOL}(operation=list)",
                "plwc_search_workspace": f"{WORKSPACE_OPERATION_TOOL}(operation=search)",
                "plwc_read_workspace_file": f"{WORKSPACE_OPERATION_TOOL}(operation=read)",
                "plwc_write_workspace_file": f"{WORKSPACE_OPERATION_TOOL}(operation=write)",
            },
            "notes": [
                "Only plwc-gateway is public.",
                "Internal workers and adapters are not exposed as MCP servers.",
                "The 19-to-8 change is a public facade refactor, not a feature expansion.",
                "Old individual tool names remain internal handlers only and are not public MCP tools.",
                'If PLwC tools are deferred in Claude Desktop, search for PLwC tools with tool_search("plwc").',
            ],
            "desktop_bootstrap": {
                "tool_discovery_hint": 'tool_search("plwc") if PLwC tools are not visible yet',
                "first_status_call": f'{PUBLIC_STATUS_TOOL}(scope="first_run")',
                "profile_creation_plan_call": (
                    f'{GOVERNOR_TOOL}(operation="plan", plan_type="profile_creation", '
                    "onboarding_answers={...})"
                ),
                "profile_creation_apply_call": (
                    f'{GOVERNOR_TOOL}(operation="apply", plan_type="profile_creation", '
                    "onboarding_answers=same, confirmed=true)"
                ),
            },
        }
    if scope == "status":
        return {
            "tool": PUBLIC_STATUS_TOOL,
            "dispatch_parameter": "scope",
            "supported_scopes": sorted(SUPPORTED_STATUS_SCOPES),
            "scope_mapping": {
                "runtime": "Gateway runtime, public boundary, workspace/profile roots and adapter status.",
                "sandbox": "Safe Mode and Docker Mode readiness.",
                "first_run": "First-run setup, onboarding schema, greeting and next actions.",
                "config": "Single plwc-gateway Claude Desktop configuration snippet.",
            },
            "desktop_bootstrap": {
                "tool_discovery_hint": 'tool_search("plwc") if PLwC tools are not visible yet',
                "first_status_call": f'{PUBLIC_STATUS_TOOL}(scope="first_run")',
                "onboarding_confirmation": "Do not apply profile creation until the user explicitly confirms.",
            },
            "legacy_tools_replaced": [
                "plwc_runtime_status",
                "plwc_sandbox_status",
                "plwc_first_run_status",
                "plwc_generate_claude_config",
            ],
            "common_denial_reasons": ["missing_scope", "invalid_scope"],
        }
    if scope == "workspace_operation":
        return {
            "tool": WORKSPACE_OPERATION_TOOL,
            "supported_operations": sorted(SUPPORTED_WORKSPACE_OPERATIONS),
            "aliases": {"create_directory": "create_dir"},
            "required_fields": {
                "list": ["operation", "path"],
                "search": ["operation", "path", "query"],
                "read": ["operation", "path"],
                "write": ["operation", "path", "content"],
                "file_info": ["operation", "path"],
                "create_dir": ["operation", "path"],
                "move": ["operation", "source_path", "target_path"],
                "rename": ["operation", "source_path", "target_path"],
                "batch_read": ["operation", "paths"],
                "exact_replace": [
                    "operation",
                    "path",
                    "old_text",
                    "new_text",
                    "expected_replacements",
                ],
                "copy": ["operation", "source_path", "target_path"],
                "read_binary": ["operation", "path"],
                "write_binary": ["operation", "path", "content_base64"],
            },
            # RC12-DESC-001 (B) — optional fields per operation (derived from the
            # dispatch: only params each branch actually reads beyond required_fields).
            "optional_fields": {
                "list": ["depth"],
                "search": ["max_results"],
                "read": [],
                "write": ["mode"],
                "file_info": [],
                "create_dir": [],
                "move": [],
                "rename": [],
                "batch_read": ["max_files", "max_bytes_per_file", "max_total_bytes"],
                "exact_replace": ["require_content_hash"],
                "copy": ["max_bytes"],
                "read_binary": ["max_bytes"],
                "write_binary": ["mode", "max_bytes"],
            },
            "forbidden_operations": sorted(DELETE_LIKE_WORKSPACE_OPERATIONS),
            "path_safety": [
                "Workspace-only paths.",
                "Parent traversal is rejected.",
                "Symlink escape is rejected.",
                "Profile and governance paths are protected.",
            ],
            "overwrite": "Move and rename reject overwrite in the public slice.",
            "parameter_validation_diagnostics": {
                "requirement_id": RC16_WORKSPACE_PARAMETER_REQUIREMENT_ID,
                "error_category": "validation_error",
                "failure_class": "parameter_validation",
                "policy_decision": "NOT_EVALUATED",
                "decision": "invalid_request",
                "policy_evaluated": False,
                "adapter_called": False,
                "meaning": (
                    "Malformed or incomplete tool-call parameters were rejected before "
                    "workspace policy evaluation or adapter execution."
                ),
            },
            "tagebuch_write_contract": {
                "requirement_id": RC17_TAGEBUCH_CANONICAL_REQUIREMENT_ID,
                "canonical_path": "Tagebuch/YYYY-MM-DD.md",
                "multiple_entries_per_day": "append to the same canonical file",
                "guarded_operations": ["write", "write_binary", "move", "rename", "copy"],
                "recommended_call": (
                    "plwc_workspace_operation(operation='write', path='Tagebuch/YYYY-MM-DD.md', "
                    "mode='append', content=...)"
                ),
                "rejected_suffix_examples": [
                    "Tagebuch/YYYY-MM-DD-2.md",
                    "Tagebuch/YYYY-MM-DD_1.md",
                    "Tagebuch/YYYY-MM-DD (2).md",
                ],
                "error_category": "tagebuch_canonical_path_required",
            },
            "search_scope_guards": {
                "note": (
                    "Search scans text contents, not filenames. Inventory and index matches "
                    "are candidate references, not proof that the named file exists at that "
                    "location. Use list with sufficient depth for filename discovery and "
                    "file_info to verify an exact path before mutation. "
                    "RC12-FS-003 — text search bounds its walk so a large binary or "
                    "huge tree cannot stall it. Guards only reduce scope; results carry "
                    "search_stats so skipped files are never silent."
                ),
                "skips": [
                    "files larger than max_file_bytes (default 5 MiB; "
                    "PLWC_WORKSPACE_SEARCH_MAX_FILE_BYTES)",
                    "binary files (a NUL byte in the head window)",
                    "excluded directories: qdrant_storage, .git, __pycache__, node_modules",
                ],
                "scan_cap": (
                    "max_files_scanned (default 50000; "
                    "PLWC_WORKSPACE_SEARCH_MAX_FILES_SCANNED) — search_stats.truncated "
                    "flags when the cap stopped the walk"
                ),
                "search_stats_fields": [
                    "scanned_files",
                    "skipped_files{too_large,binary,unreadable}",
                    "skipped_total",
                    "excluded_dirs",
                    "max_file_bytes",
                    "max_files_scanned",
                    "truncated",
                    "result_limit_reached",
                ],
            },
            "common_denial_reasons": [
                "unknown_operation",
                "missing_required_field",
                "invalid_field_type",
                "parameter_validation",
                "path_escape",
                "protected_path",
                "overwrite_not_supported",
            ],
        }
    if scope == "document_operation":
        return {
            "tool": DOCUMENT_OPERATION_TOOL,
            "worker_image": DOCUMENT_WORKER_IMAGE,
            "worker_mount": WORKER_CONTAINER_WORKDIR,
            "supported_operations": sorted(SUPPORTED_DOCUMENT_OPERATIONS),
            "required_fields": {
                "create_docx": {
                    "top_level": ["operation", "output_path"],
                    "one_of": ["content", "input_path"],
                    "input_path": {
                        "format": "JSON document specification",
                        "extension": ".json",
                        "ambiguity": "content and input_path together are rejected.",
                    },
                    "legacy_content": {
                        "required": ["title", "paragraphs"],
                        "optional": ["table"],
                    },
                    "v2_content": {
                        "schema_version": {
                            "default": DOCX_V2_SCHEMA_VERSION,
                            "supported": sorted(DOCX_V2_SUPPORTED_SCHEMA_VERSIONS),
                            "unknown_version_behavior": "validation_error",
                        },
                        "top_level_fields": sorted(DOCX_V2_TOP_LEVEL_FIELDS),
                        "document_fields": sorted(DOCX_V2_DOCUMENT_FIELDS),
                        "page": {
                            "sizes": sorted(DOCX_V2_PAGE_SIZES),
                            "orientation": sorted(DOCX_V2_ORIENTATIONS),
                            "margins_mm": sorted(DOCX_V2_MARGIN_FIELDS),
                        },
                        "styles": {
                            "names": sorted(DOCX_V2_STYLE_NAMES),
                            "properties": sorted(DOCX_V2_STYLE_FIELDS),
                            "alignment": sorted(DOCX_V2_ALIGNMENTS),
                            "font_embedding": False,
                        },
                        "content_element_types": sorted(DOCX_V2_CONTENT_TYPES),
                        "paragraph_runs": {
                            "supported": True,
                            "fields": sorted(DOCX_V2_RUN_FIELDS),
                            "ambiguity": "text and runs together are rejected.",
                        },
                        "lists": {
                            "supported": True,
                            "types": ["bullet_list", "numbered_list"],
                            "fields": sorted(DOCX_V2_LIST_FIELDS),
                            "nested_lists": False,
                        },
                        "image": {
                            "formats": sorted(DOCX_V2_IMAGE_SUFFIXES),
                            "fields": sorted(DOCX_V2_IMAGE_FIELDS),
                            "path_policy": "Workspace-relative only; traversal and profile/governance paths are rejected.",
                        },
                        "table": {
                            "fields": sorted(DOCX_V2_TABLE_FIELDS),
                            "cell_policy": "Scalar text/number/bool/null cells only; formulas are not executed and formula-like strings are rejected.",
                        },
                    },
                    "extension": ".docx",
                    "builder": "DOCX Creation V2 layout-capable builder.",
                    "unsupported_input_formats": ["Markdown", "plain text", "HTML", "template DOCX"],
                },
                "create_xlsx": {
                    "top_level": ["operation", "output_path"],
                    "one_of": ["content", "input_path"],
                    "input_path": {
                        "extension": ".json",
                        "format": "XLSX Creation V2 JSON workbook specification.",
                        "ambiguity": "input_path and inline content together are rejected.",
                    },
                    "legacy_content": {
                        "required": ["sheet_name", "rows"],
                        "cell_policy": "Plain scalar rows remain supported for compatibility.",
                    },
                    "v2_content": {
                        "schema_version": {
                            "default": XLSX_V2_SCHEMA_VERSION,
                            "supported": sorted(XLSX_V2_SUPPORTED_SCHEMA_VERSIONS),
                            "unknown_version_behavior": "validation_error",
                        },
                        "top_level_fields": sorted(XLSX_V2_TOP_LEVEL_FIELDS),
                        "workbook_fields": sorted(XLSX_V2_WORKBOOK_FIELDS),
                        "sheet_fields": sorted(XLSX_V2_SHEET_FIELDS),
                        "cell_fields": sorted(XLSX_V2_CELL_FIELDS),
                        "cell_value_types": ["string", "integer", "float", "boolean", "null", "explicit formula"],
                        "formatting": {
                            "properties": sorted(XLSX_V2_FORMAT_FIELDS),
                            "alignment": sorted(XLSX_V2_ALIGNMENTS),
                            "vertical_alignment": sorted(XLSX_V2_VERTICAL_ALIGNMENTS),
                            "border": sorted(XLSX_V2_BORDERS),
                            "colors": "#RRGGBB or RRGGBB hex strings.",
                        },
                        "sheet_structure": ["freeze_panes", "auto_filter", "column_widths", "row_heights", "merge_cells"],
                        "sheet_structure_contract": {
                            "auto_filter": {
                                "type": "boolean",
                                "true_behavior": "Apply auto filter to the used data range and first row.",
                                "false_behavior": "Do not apply an auto filter.",
                                "unsupported": "Range-string auto_filter values such as A1:C10 are not supported in this slice.",
                                "future_range_field": "If range-based filtering is added later, use a separate explicit field such as auto_filter_range.",
                                "invalid_type_behavior": "validation_error",
                            }
                        },
                        "formula_policy": {
                            "execution": "PLwC writes explicit formula fields but never executes or verifies formulas.",
                            "literal_default": "Value strings beginning with '=' are stored as literal text unless the formula field is used.",
                            "rejected": ["external workbook references", "URLs", "external data functions", "macro-like functions"],
                        },
                    },
                    "extension": ".xlsx",
                    "builder": "XLSX Creation V2 multi-sheet workbook builder.",
                    "unsupported_input_formats": ["CSV", "Excel templates", "macros", "external links"],
                },
                "create_pptx": {
                    "top_level": ["operation", "output_path"],
                    "one_of": ["content", "input_path"],
                    "top_level_shorthand": ["title", "slides"],
                    "input_path": {
                        "extension": ".json",
                        "format": "PPTX Creation V2 JSON presentation specification.",
                        "ambiguity": "input_path and inline content together are rejected.",
                    },
                    "legacy_content": {
                        "required": ["title", "slides"],
                        "slide_fields": ["title", "bullets"],
                        "bullets_policy": "Slide bullets remain plain string arrays for compatibility.",
                    },
                    "v2_content": {
                        "schema_version": {
                            "default": PPTX_V2_SCHEMA_VERSION,
                            "supported": sorted(PPTX_V2_SUPPORTED_SCHEMA_VERSIONS),
                            "unknown_version_behavior": "validation_error",
                        },
                        "top_level_fields": sorted(PPTX_V2_TOP_LEVEL_FIELDS),
                        "presentation_fields": sorted(PPTX_V2_PRESENTATION_FIELDS),
                        "slide_fields": sorted(PPTX_V2_SLIDE_FIELDS),
                        "slide_layouts": sorted(PPTX_V2_LAYOUTS),
                        "content_element_types": sorted(PPTX_V2_CONTENT_TYPES),
                        "bullet_item_fields": sorted(PPTX_V2_BULLET_ITEM_FIELDS),
                        "bullet_levels": sorted(PPTX_V2_BULLET_LEVELS),
                        "paragraph_fields": sorted(PPTX_V2_PARAGRAPH_FIELDS),
                        "table_fields": sorted(PPTX_V2_TABLE_FIELDS),
                        "image_element_fields": sorted(PPTX_V2_IMAGE_ELEMENT_FIELDS),
                        "text_box_fields": sorted(PPTX_V2_TEXT_BOX_FIELDS),
                        "alignment": sorted(PPTX_V2_ALIGNMENTS),
                        "slide_size_presets": sorted(PPTX_V2_SLIDE_SIZE_PRESETS),
                        "custom_slide_size_fields": sorted(PPTX_V2_CUSTOM_SIZE_FIELDS),
                        "custom_slide_size_mm_bounds": [
                            PPTX_V2_CUSTOM_SIZE_MIN_MM,
                            PPTX_V2_CUSTOM_SIZE_MAX_MM,
                        ],
                        "image_formats": sorted(PPTX_V2_IMAGE_SUFFIXES),
                        "image_path_policy": "Workspace-relative only. External URLs, UNC paths, absolute paths, parent traversal and profile/governance paths are rejected.",
                        "speaker_notes": {
                            "supported": True,
                            "format": "plain text only",
                            "max_chars": 10000,
                            "extract_via": "extract_pptx_text(include_notes=true)",
                        },
                        "table_policy": "Rows are scalar text/number/bool/null cells; rows must share the same column count.",
                        "text_policy": "Slide text fields (title, subtitle, body, paragraph, bullets, table cells, text_box, notes) accept arbitrary user text, including strings that begin with '=' or contain '<script>'/'<?xml' substrings. The builder does not execute, render or interpret such text.",
                        "active_content_policy": "The builder never produces macros, VBA, OLE embeddings, external relationships or remote/font-fetching; only .pptx (not .pptm) output is created.",
                        "non_goals": [
                            "animation",
                            "transitions",
                            "font embedding",
                            "remote/font fetching",
                            "LibreOffice/Pandoc conversion",
                            "rendering engine",
                            "macros/VBA",
                            "OLE embeddings",
                            "PowerPoint automation",
                        ],
                    },
                    "extension": ".pptx",
                    "builder": "PPTX Creation V2 layout-capable builder.",
                    "unsupported_input_formats": [
                        "Markdown",
                        "plain text",
                        "HTML",
                        "PPTX template",
                        "PPTM macro-enabled",
                    ],
                    "example": {
                        "operation": "create_pptx",
                        "output_path": "decks/v2.pptx",
                        "content": {
                            "schema_version": PPTX_V2_SCHEMA_VERSION,
                            "presentation": {"title": "Quarterly Review", "slide_size": "16:9"},
                            "slides": [
                                {"layout": "title", "title": "Quarterly Review", "subtitle": "Q4", "notes": "Welcome"},
                                {
                                    "layout": "content",
                                    "title": "Highlights",
                                    "content": [
                                        {
                                            "type": "bullets",
                                            "items": [
                                                {"text": "Revenue up", "level": 0, "bold": True},
                                                {"text": "Costs flat", "level": 1},
                                            ],
                                        }
                                    ],
                                    "notes": "Speaker reminder.",
                                },
                            ],
                        },
                    },
                },
                "create_pdf": {
                    "top_level": ["operation", "output_path"],
                    "one_of": ["content", "input_path"],
                    "input_path": {
                        "extension": ".json",
                        "format": "PDF Creation V2 JSON document specification.",
                        "ambiguity": "input_path and inline content together are rejected.",
                    },
                    "legacy_content": {
                        "required": ["title", "lines"],
                        "lines_policy": "Plain string lines are written one paragraph per line for compatibility.",
                    },
                    "v2_content": {
                        "schema_version": {
                            "default": PDF_V2_SCHEMA_VERSION,
                            "supported": sorted(PDF_V2_SUPPORTED_SCHEMA_VERSIONS),
                            "unknown_version_behavior": "validation_error",
                        },
                        "top_level_fields": sorted(PDF_V2_TOP_LEVEL_FIELDS),
                        "document_fields": sorted(PDF_V2_DOCUMENT_FIELDS),
                        "page": {
                            "sizes": sorted(PDF_V2_PAGE_SIZES) + ["custom object"],
                            "orientation": sorted(PDF_V2_ORIENTATIONS),
                            "margins_mm": sorted(PDF_V2_MARGIN_FIELDS),
                            "custom_size_fields": sorted(PDF_V2_CUSTOM_SIZE_FIELDS),
                            "custom_size_mm_bounds": [
                                PDF_V2_CUSTOM_SIZE_MIN_MM,
                                PDF_V2_CUSTOM_SIZE_MAX_MM,
                            ],
                        },
                        "styles": {
                            "names": sorted(PDF_V2_STYLE_NAMES),
                            "properties": sorted(PDF_V2_STYLE_FIELDS),
                            "alignment": sorted(PDF_V2_ALIGNMENTS),
                            "font_embedding": False,
                            "font_policy": "Uses PDF-safe built-in fonts; no external font files are embedded or fetched. Exact typography depends on the available PDF library.",
                        },
                        "content_element_types": sorted(PDF_V2_CONTENT_TYPES),
                        "paragraph_runs": {
                            "supported": True,
                            "fields": sorted(PDF_V2_RUN_FIELDS),
                            "ambiguity": "text and runs together are rejected.",
                        },
                        "lists": {
                            "supported": True,
                            "types": ["bullet_list", "numbered_list"],
                            "fields": sorted(PDF_V2_LIST_FIELDS),
                            "nested_lists": False,
                        },
                        "image": {
                            "formats": sorted(PDF_V2_IMAGE_SUFFIXES),
                            "fields": sorted(PDF_V2_IMAGE_FIELDS),
                            "path_policy": "Workspace-relative only. External URLs, UNC paths, absolute paths, parent traversal and profile/governance paths are rejected.",
                        },
                        "table": {
                            "fields": sorted(PDF_V2_TABLE_FIELDS),
                            "cell_policy": "Scalar text/number/bool/null cells only; all rows must share the same column count; no formulas, no active content.",
                            "header_row": "Optional boolean; when true the first row is styled as header.",
                        },
                        "page_break": "Use {\"type\": \"page_break\"} for an explicit page break. heading1.page_break_before honors the style flag.",
                        "text_policy": "Slide and paragraph text fields accept arbitrary user text; strings beginning with '=' or containing '<script>'/'<?xml' substrings are stored verbatim and not interpreted, rendered or executed.",
                        "active_content_policy": "The builder never embeds JavaScript, attachments, external links, OLE/embedded files, fonts or remote relationships. Only `.pdf` output is created.",
                        "non_goals": [
                            "PDF editor",
                            "OCR",
                            "redaction",
                            "digital signing",
                            "form filling",
                            "form creation",
                            "PDF/A",
                            "LibreOffice/Pandoc conversion",
                            "HTML/CSS rendering",
                            "JavaScript in PDFs",
                            "attachments",
                            "embedded files",
                            "external URL fetching",
                            "network access",
                        ],
                    },
                    "extension": ".pdf",
                    "builder": "PDF Creation V2 layout-PDF builder.",
                    "unsupported_input_formats": [
                        "Markdown",
                        "plain text",
                        "HTML",
                        "PDF template",
                        "PDF form",
                    ],
                    "example": {
                        "operation": "create_pdf",
                        "output_path": "reports/v2.pdf",
                        "content": {
                            "schema_version": PDF_V2_SCHEMA_VERSION,
                            "document": {"title": "Quarterly Report"},
                            "page": {"size": "A4", "orientation": "portrait"},
                            "content": [
                                {"type": "title", "text": "Quarterly Report"},
                                {"type": "heading1", "text": "Highlights"},
                                {"type": "paragraph", "text": "Revenue grew."},
                            ],
                        },
                    },
                },
                "inspect_pdf": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".pdf",
                    "returns": ["page_count", "encrypted", "metadata", "file_size"],
                },
                "merge_pdf": {
                    "top_level": ["operation", "input_paths", "output_path"],
                    "extension": ".pdf",
                    "limits": ["max_input_files", "max_structural_input_file_size", "max_merge_output_pages"],
                },
                "split_pdf": {
                    "top_level": ["operation", "input_path", "output_dir", "mode"],
                    "mode": "pages",
                    "limits": ["max_split_output_files"],
                    "page_numbering": "1-based for all user-facing page selectors.",
                },
                "extract_pdf": {
                    "top_level": ["operation", "input_path", "output_path", "pages"],
                    "limits": ["max_extract_output_pages"],
                    "page_numbering": "1-based; page 0 and out-of-range pages are rejected.",
                },
                "rotate_pdf": {
                    "top_level": ["operation", "input_path", "output_path", "rotation"],
                    "optional": ["pages"],
                    "rotation": [90, 180, 270],
                    "limits": ["max_rotate_all_pages", "max_rotate_selected_pages"],
                    "page_numbering": "1-based; omitted pages rotates all pages and uses the all-pages limit.",
                },
                "extract_pdf_text": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "format", "pages", "max_pages", "max_chars", "include_preview", "max_preview_chars"],
                    "formats": ["text", "json"],
                    "output_extensions": {"text": ".txt", "json": ".json"},
                    "page_numbering": "1-based; selected pages are counted against max_pages, not total document pages; omitted pages extracts only the first bounded page scope.",
                    "behavior": "Extracts only the existing PDF text layer; large text is written to .txt/.json instead of being dumped into the response.",
                },
                "inspect_zip": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".zip",
                    "behavior": "Reads ZIP central-directory metadata only; does not extract files.",
                    "returns": ["entry counts", "compressed/uncompressed bytes", "compression ratio", "encrypted entries", "symlink entries", "path findings", "extraction_allowed"],
                },
                "extract_zip": {
                    "top_level": ["operation", "input_path", "output_dir"],
                    "extension": ".zip",
                    "overwrite": "false only in MVP",
                    "behavior": "Validates every entry before extraction and rejects Zip Slip, absolute paths, protected targets, encrypted entries and symlinks.",
                },
                "create_zip": {
                    "top_level": ["operation", "output_path"],
                    "one_of": ["input_path", "input_paths"],
                    "extension": ".zip",
                    "overwrite": "false only in MVP",
                    "behavior": "Creates ZIPs from allowed workspace files/directories; symlink sources are rejected in the MVP.",
                },
                "read_image": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["max_size_kb", "resize_to", "format"],
                    "input_formats": list(READ_IMAGE_SUPPORTED_INPUT_FORMATS),
                    "output_formats": sorted(READ_IMAGE_OUTPUT_FORMATS),
                    "default_output_format": "png",
                    "media_types": {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"},
                    "default_max_size_kb": READ_IMAGE_DEFAULT_MAX_SIZE_KB,
                    "hard_max_size_kb": READ_IMAGE_HARD_MAX_SIZE_KB,
                    "resize_to": ["WIDTHxHEIGHT fit box preserving aspect ratio", "N% proportional scale"],
                    "behavior": "Returns metadata in the text block and delivers image bytes as an MCP image content block; image_data is stripped from the text JSON.",
                    "gif": "Supported as first frame only and encoded to the requested output format.",
                    "unsupported_formats": ["bmp", "svg", "tiff"],
                },
                "inspect_docx": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".docx",
                    "returns": ["paragraph_count", "table_count", "text_char_count", "metadata", "warnings"],
                },
                "extract_docx_text": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "format", "max_chars", "include_preview", "max_preview_chars"],
                    "formats": ["text", "json"],
                    "output_extensions": {"text": ".txt", "json": ".json"},
                    "behavior": "Extracts paragraphs and table text; no layout reconstruction, OCR, macros or embedded-file extraction.",
                },
                "inspect_xlsx": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".xlsx",
                    "returns": ["sheet_names", "sheet_count", "formula_present", "warnings"],
                },
                "extract_xlsx_data": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "sheets", "ranges", "max_rows", "max_cells", "include_preview", "max_preview_chars"],
                    "output_extension": ".json",
                    "behavior": "Extracts bounded scalar cell data. Formulas are reported as formula text and are not executed.",
                },
                "inspect_pptx": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".pptx",
                    "returns": ["slide_count", "text_shape_count", "embedded_media_count", "warnings"],
                },
                "extract_pptx_text": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "slides", "max_chars", "include_preview", "max_preview_chars", "include_notes"],
                    "output_extension": ".txt",
                    "page_numbering": "Slides are 1-based.",
                    "behavior": "Extracts slide text in slide order; no rendering, animation reconstruction, OCR or media extraction.",
                },
                "inspect_odt": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".odt",
                    "returns": ["paragraph_count", "table_count", "text_char_count", "warnings"],
                },
                "extract_odt_text": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "format", "max_chars", "include_preview", "max_preview_chars"],
                    "formats": ["text", "json"],
                    "output_extensions": {"text": ".txt", "json": ".json"},
                    "behavior": "Reads OpenDocument content.xml with safe XML parsing; no embedded object extraction.",
                },
                "inspect_ods": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".ods",
                    "returns": ["sheet_names", "table_count", "formula_present", "warnings"],
                },
                "extract_ods_data": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "sheets", "max_rows", "max_cells", "include_preview", "max_preview_chars"],
                    "output_extension": ".json",
                    "behavior": "Extracts bounded OpenDocument table data. Formulas are reported and are not executed.",
                },
                "inspect_odp": {
                    "top_level": ["operation", "input_path"],
                    "extension": ".odp",
                    "returns": ["slide_count", "text_element_count", "warnings"],
                },
                "extract_odp_text": {
                    "top_level": ["operation", "input_path"],
                    "optional": ["output_path", "slides", "max_chars", "include_preview", "max_preview_chars"],
                    "output_extension": ".txt",
                    "page_numbering": "Slides/pages are 1-based.",
                    "behavior": "Extracts OpenDocument slide text; no rendering, OCR or media extraction.",
                },
                "edit_docx": {
                    "top_level": ["operation", "input_path", "output_path", "content"],
                    "content_fields": {
                        "schema_version": {
                            "default": EDIT_DOCX_SCHEMA_VERSION,
                            "supported": sorted(EDIT_DOCX_SUPPORTED_SCHEMA_VERSIONS),
                        },
                        "edits": "Non-empty list of declarative edit operations (max 200).",
                    },
                    "edit_op_types": sorted(EDIT_DOCX_OP_TYPES),
                    "replace_text": {
                        "fields": sorted(EDIT_DOCX_REPLACE_TEXT_FIELDS),
                        "find": "Non-empty literal string to search for in body paragraph runs.",
                        "replace": "Replacement string (may be empty to delete).",
                        "max_replacements": "Optional positive int; omit or null to replace all occurrences.",
                        "scope": "Body paragraphs and table cell paragraphs only; headers/footers are not scanned.",
                    },
                    "set_core_property": {
                        "fields": sorted(EDIT_DOCX_SET_CORE_PROPERTY_FIELDS),
                        "name": sorted(EDIT_DOCX_CORE_PROPERTY_NAMES),
                        "value": "String value to set.",
                    },
                    "append_paragraph": {
                        "fields": sorted(EDIT_DOCX_APPEND_PARAGRAPH_FIELDS),
                        "text": "Paragraph text.",
                        "style": f"Optional; one of: {', '.join(sorted(DOCX_V2_STYLE_NAMES))}. Defaults to Normal.",
                    },
                    "set_footer_text": {
                        "fields": sorted(EDIT_DOCX_SET_HEADER_FOOTER_FIELDS),
                        "text": "Footer text (may be empty string).",
                        "page_number": "Optional bool; if true appends a PAGE field after the text.",
                        "scope": "First section only.",
                    },
                    "set_header_text": {
                        "fields": sorted(EDIT_DOCX_SET_HEADER_FOOTER_FIELDS),
                        "text": "Header text (may be empty string).",
                        "page_number": "Optional bool; if true appends a PAGE field after the text.",
                        "scope": "First section only.",
                    },
                    "semantics": "read-A-write-B: input_path is read-only; output_path is the new file and must not already exist.",
                    "input_extension": ".docx",
                    "output_extension": ".docx",
                    "macro_policy": ".docm inputs are rejected; no macro execution.",
                    "active_content_policy": "Formulas, raw XML/HTML, scripts and active content strings are rejected in edit field values.",
                    "non_goals_v1": ["in-place editing", "overwrite", "bookmarks", "TOC fields", "tracked changes", "comments", "image replacement"],
                },
            },
            # RC12-DESC-001 (B) — optional fields per operation (derived from the
            # dispatch: keyword args each branch reads with a default are optional).
            # create_* content-schema optionals live in required_fields / creation_contract.
            "optional_fields": {
                "create_docx": ["input_path"],
                "create_xlsx": ["input_path"],
                "create_pptx": ["input_path"],
                "create_pdf": ["input_path"],
                "inspect_pdf": [],
                "merge_pdf": [],
                "split_pdf": ["mode"],
                "extract_pdf": ["pages"],
                "rotate_pdf": ["rotation", "pages"],
                "extract_pdf_text": ["output_path", "pages", "format", "max_pages", "max_chars", "include_preview", "max_preview_chars"],
                "inspect_zip": [],
                "extract_zip": [],
                "create_zip": ["input_path", "input_paths"],
                "read_image": ["max_size_kb", "resize_to", "format"],
                "inspect_docx": [],
                "inspect_xlsx": [],
                "inspect_pptx": [],
                "inspect_odt": [],
                "inspect_ods": [],
                "inspect_odp": [],
                "extract_docx_text": ["output_path", "format", "max_chars", "include_preview", "max_preview_chars"],
                "extract_odt_text": ["output_path", "format", "max_chars", "include_preview", "max_preview_chars"],
                "extract_pptx_text": ["output_path", "slides", "max_chars", "include_preview", "max_preview_chars", "include_notes"],
                "extract_odp_text": ["output_path", "slides", "max_chars", "include_preview", "max_preview_chars", "include_notes"],
                "extract_xlsx_data": ["output_path", "sheets", "ranges", "max_rows", "max_cells", "include_preview", "max_preview_chars"],
                "extract_ods_data": ["output_path", "sheets", "ranges", "max_rows", "max_cells", "include_preview", "max_preview_chars"],
                "edit_docx": [],
            },
            "unsupported_operations": sorted(UNSUPPORTED_DOCUMENT_OPERATION_NAMES),
            "pdf_mvp_limits": {
                "max_structural_input_file_size": PDF_MAX_STRUCTURAL_INPUT_FILE_SIZE,
                "max_input_files": PDF_MAX_INPUT_FILES,
                "max_merge_output_pages": PDF_MAX_MERGE_OUTPUT_PAGES,
                "max_extract_output_pages": PDF_MAX_EXTRACT_OUTPUT_PAGES,
                "max_split_output_files": PDF_MAX_SPLIT_OUTPUT_FILES,
                "max_rotate_all_pages": PDF_MAX_ROTATE_ALL_PAGES,
                "max_rotate_selected_pages": PDF_MAX_ROTATE_SELECTED_PAGES,
                "max_text_pages": PDF_TEXT_MAX_PAGES,
                "max_text_chars": PDF_TEXT_MAX_CHARS,
                "max_preview_chars": PDF_TEXT_MAX_PREVIEW_CHARS,
            },
            "zip_mvp_limits": {
                "max_structural_input_file_size": ZIP_MAX_STRUCTURAL_INPUT_FILE_SIZE,
                "max_entries": ZIP_MAX_ENTRIES,
                "max_extracted_total_bytes": ZIP_MAX_EXTRACTED_BYTES,
                "max_single_file_bytes": ZIP_MAX_SINGLE_FILE_BYTES,
                "max_path_length": ZIP_MAX_PATH_LENGTH,
                "max_compression_ratio": ZIP_MAX_COMPRESSION_RATIO,
                "max_nested_depth": ZIP_MAX_NESTED_DEPTH,
                "limit_model": "Large ZIP inputs may be allowed; extraction/creation is bounded by target, entry validation, output size, file count, path length and zip-bomb ratio.",
            },
            "office_mvp_limits": {
                "max_structural_input_file_size": OFFICE_MAX_STRUCTURAL_INPUT_FILE_SIZE,
                "max_text_chars": OFFICE_MAX_TEXT_CHARS,
                "max_preview_chars": OFFICE_MAX_PREVIEW_CHARS,
                "max_xlsx_rows": OFFICE_MAX_XLSX_ROWS,
                "max_xlsx_cells": OFFICE_MAX_XLSX_CELLS,
                "max_pptx_slides": OFFICE_MAX_PPTX_SLIDES,
                "max_odf_tables": OFFICE_MAX_ODF_TABLES,
                "max_odf_rows": OFFICE_MAX_ODF_ROWS,
                "max_odf_cells": OFFICE_MAX_ODF_CELLS,
                "max_xml_part_bytes": OFFICE_MAX_XML_PART_BYTES,
                "limit_model": "Office/OpenDocument operations use bounded extraction scopes rather than tiny global blockers.",
            },
            "docx_creation_v2_limits": {
                "max_json_input_bytes": DOCX_V2_MAX_JSON_INPUT_BYTES,
                "max_content_elements": DOCX_V2_MAX_CONTENT_ELEMENTS,
                "max_paragraphs": DOCX_V2_MAX_PARAGRAPHS,
                "max_tables": DOCX_V2_MAX_TABLES,
                "max_table_cells": DOCX_V2_MAX_TABLE_CELLS,
                "max_images": DOCX_V2_MAX_IMAGES,
                "max_image_bytes": DOCX_V2_MAX_IMAGE_BYTES,
                "max_output_bytes": DOCX_V2_MAX_OUTPUT_BYTES,
            },
            "xlsx_creation_v2_limits": {
                "max_json_input_bytes": XLSX_V2_MAX_JSON_INPUT_BYTES,
                "max_sheets": XLSX_V2_MAX_SHEETS,
                "max_rows_per_sheet": XLSX_V2_MAX_ROWS_PER_SHEET,
                "max_columns_per_sheet": XLSX_V2_MAX_COLUMNS_PER_SHEET,
                "max_cells_per_sheet": XLSX_V2_MAX_CELLS_PER_SHEET,
                "max_total_cells": XLSX_V2_MAX_TOTAL_CELLS,
                "max_merged_ranges": XLSX_V2_MAX_MERGED_RANGES,
                "max_output_bytes": XLSX_V2_MAX_OUTPUT_BYTES,
            },
            "pptx_creation_v2_limits": {
                "max_json_input_bytes": PPTX_V2_MAX_JSON_INPUT_BYTES,
                "max_slides": PPTX_V2_MAX_SLIDES,
                "max_content_elements_per_slide": PPTX_V2_MAX_CONTENT_ELEMENTS_PER_SLIDE,
                "max_bullet_items_per_slide": PPTX_V2_MAX_BULLET_ITEMS_PER_SLIDE,
                "max_tables_per_slide": PPTX_V2_MAX_TABLES_PER_SLIDE,
                "max_table_cells_per_slide": PPTX_V2_MAX_TABLE_CELLS_PER_SLIDE,
                "max_images": PPTX_V2_MAX_IMAGES,
                "max_image_bytes": PPTX_V2_MAX_IMAGE_BYTES,
                "max_output_bytes": PPTX_V2_MAX_OUTPUT_BYTES,
            },
            "pdf_creation_v2_limits": {
                "max_json_input_bytes": PDF_V2_MAX_JSON_INPUT_BYTES,
                "max_content_elements": PDF_V2_MAX_CONTENT_ELEMENTS,
                "max_paragraphs": PDF_V2_MAX_PARAGRAPHS,
                "max_tables": PDF_V2_MAX_TABLES,
                "max_table_cells": PDF_V2_MAX_TABLE_CELLS,
                "max_images": PDF_V2_MAX_IMAGES,
                "max_image_bytes": PDF_V2_MAX_IMAGE_BYTES,
                "max_output_bytes": PDF_V2_MAX_OUTPUT_BYTES,
            },
            "image_read_limits": {
                "default_max_size_kb": READ_IMAGE_DEFAULT_MAX_SIZE_KB,
                "hard_max_size_kb": READ_IMAGE_HARD_MAX_SIZE_KB,
                "supported_input_formats": list(READ_IMAGE_SUPPORTED_INPUT_FORMATS),
                "supported_output_formats": sorted(READ_IMAGE_OUTPUT_FORMATS),
                "path_policy": "Only workspace-relative paths are allowed; external URLs, absolute paths, traversal and profile/governance paths are rejected.",
                "transfer_policy": "Base64 image bytes are returned as an MCP image content block, not as plain text.",
            },
            "worker_missing": "Returns ok=false with error_category=worker_missing; no pull is attempted.",
            "engine_missing": "Returns ok=false with error_category=engine_missing when a required engine is unavailable inside the worker.",
            "runtime_policy": {
                "network": "none",
                "pull": "never",
                "runtime_pip": False,
                "model_supplied_docker_flags": False,
            },
            "path_safety": [
                "Output paths must be relative workspace paths.",
                "Extension must match the selected operation.",
                "Profile, profiles and governance targets are rejected.",
                "Parent traversal and absolute host paths are rejected.",
            ],
            "creation_contract": {
                "create_docx": "DOCX Creation V2 accepts legacy content.title/content.paragraphs/content.table or a V2 JSON spec through content or input_path. input_path must be .json and cannot be combined with content.",
                "create_xlsx": "XLSX Creation V2 accepts legacy content.sheet_name/content.rows or a V2 JSON workbook spec through content or input_path. input_path must be .json and cannot be combined with content.",
                "create_pdf": "PDF Creation V2 accepts legacy content.title/content.lines or a V2 JSON document spec through content or input_path. input_path must be .json and cannot be combined with content. PDF V2 is a layout-PDF builder; it is not a PDF editor and provides no OCR, redaction, signing, forms, PDF/A claim, attachments, JavaScript or external URL fetching.",
                "create_pptx": "PPTX Creation V2 accepts legacy content.title/content.slides[{title, bullets[string]}] or a V2 JSON presentation spec through content or input_path. input_path must be .json and cannot be combined with content.",
                "create_zip": "output_path plus input_path or input_paths are required; content is not used.",
                "edit_docx": "edit_docx reads an existing .docx from input_path and writes a new .docx to output_path (read-A-write-B). content must be an object with schema_version=edit_docx_1 and a non-empty edits list. Edits are declarative (replace_text, set_core_property, append_paragraph, set_footer_text, set_header_text); no raw XML/HTML input, no in-place overwrite, no .docm macro files.",
                "edit_docx_input_path": "input_path is required for edit_docx and must be a workspace-relative .docx path. The file is read-only and is never modified.",
                "edit_docx_output_path": "output_path is required for edit_docx, must be a workspace-relative .docx path and must not already exist (same semantics as create_docx).",
                "edit_docx_non_goals_v1": "No in-place editing, no overwrite, no bookmarks, no TOC/PAGEREF fields, no tracked changes, no comments, no image replacement. These are explicit edit_docx_v2 candidates.",
                "unsupported_fields": "Unknown structured fields are rejected with validation_error and include unsupported_fields/accepted_fields where the facade can validate them.",
                "input_path": "Creation input_path support is available for create_docx, create_xlsx, create_pptx and create_pdf JSON specs in this slice; read_image also requires input_path for workspace image reads.",
                "docx_v2_non_goals": "No LibreOffice/Pandoc conversion, exact print typography guarantee, font embedding, raw XML/HTML templating or full desktop publishing.",
                "docx_v2_schema_version": f"Default and currently supported schema_version is {DOCX_V2_SCHEMA_VERSION}; unknown future versions fail with validation_error.",
                "docx_v2_inline_features": "heading3, paragraph runs, bullet_list and numbered_list are implemented in this slice with strict field validation.",
                "xlsx_v2_formula_policy": "Formula fields are written but not executed by PLwC; strings beginning with '=' in value cells are literal text, and external or macro-like formulas are rejected.",
                "xlsx_v2_non_goals": "No CSV input in this slice, no macro execution, no external link fetching, no LibreOffice/Pandoc conversion and no calculation engine.",
                "pptx_v2_schema_version": f"Default and currently supported schema_version is {PPTX_V2_SCHEMA_VERSION}; unknown future versions fail with validation_error.",
                "pptx_v2_layouts": "Implemented slide layouts are title, content, blank, section_header and image. Unknown layouts are rejected with unsupported_layout.",
                "pptx_v2_speaker_notes": "Plain-text speaker notes are written to the PPTX notes layer and are returned by extract_pptx_text when include_notes=true.",
                "pptx_v2_text_policy": "Slide text fields accept arbitrary user text; strings that look like formulas, scripts or XML are stored verbatim and not interpreted.",
                "pptx_v2_active_content_policy": "The builder never produces macros, VBA, OLE embeddings, external relationships, font embedding or remote fetching; only .pptx output is created.",
                "pptx_v2_non_goals": "No animation rendering, no transition rendering, no font embedding, no LibreOffice/Pandoc conversion and no PPTX rendering engine.",
                "pdf_v2_schema_version": f"Default and currently supported schema_version is {PDF_V2_SCHEMA_VERSION}; unknown future versions fail with validation_error.",
                "pdf_v2_layout_features": "A4/A5 page size (plus optional custom size), portrait/landscape orientation, millimeter margins, body/title/heading1..3 styles, paragraph runs (bold/italic/underline), bullet_list, numbered_list, table with header_row, image with align/width_mm/height_mm and explicit page_break.",
                "pdf_v2_text_policy": "Paragraph and notes text fields accept arbitrary user text; strings that look like formulas, scripts or XML are stored verbatim and not interpreted, rendered or executed.",
                "pdf_v2_active_content_policy": "The builder never embeds JavaScript, attachments, external links, OLE/embedded files, fonts or remote relationships. Only .pdf output is created.",
                "pdf_v2_non_goals": "Not a PDF editor; no OCR, redaction, digital signing, forms, PDF/A claim, LibreOffice/Pandoc conversion, HTML/CSS rendering, JavaScript, attachments, embedded files, external URL fetching or network access.",
            },
            "non_goals": [
                "conversion",
                "LibreOffice",
                "Pandoc",
                "archive handling",
                "RAR/7z/tar/tar.gz/gzip/bz2/xz archives",
                "password or encrypted ZIP support",
                "nested archive extraction",
                "delete/remove/unlink/rmdir",
                "OCR",
                "Office conversion",
                "LibreOffice",
                "Pandoc",
                "macro execution",
                "formula execution",
                "external link fetching",
                "PDF text OCR",
                "PDF signing",
                "PDF redaction",
                "PDF form filling",
                "PDF layout reconstruction",
                "PDF table reconstruction",
                "embedded file extraction",
                "raw XML or HTML templating",
                "macros",
                "external resources",
            ],
        }
    if scope == "reflection":
        return {
            "tool": REFLECTION_TOOL,
            "dispatch_parameter": "operation",
            "supported_operations": sorted(SUPPORTED_REFLECTION_OPERATIONS),
            "legacy_tools_replaced": ["plwc_write_reflection"],
            "recommended_marker_values": list(REFLECTION_MARKER_RECOMMENDED_VALUES),
            "allowed_markers": list(PBA2_REFLECTION_MARKERS),
            "canonical_storage_markers": list(PBA2_REFLECTION_MARKERS),
            "marker_english_aliases": dict(sorted(REFLECTION_MARKER_SYNONYMS.items())),
            "recommended_trust_values": list(REFLECTION_TRUST_RECOMMENDED_VALUES),
            "allowed_trust_values": list(PBA2_REFLECTION_TRUST_LEVELS),
            "canonical_storage_trust_values": list(PBA2_REFLECTION_TRUST_LEVELS),
            "trust_english_aliases": dict(sorted(CONFIDENCE_TO_PBA2_TRUST.items())),
            "required_fields": ["operation", "summary", "evidence", "confidence_or_trust"],
            "optional_fields": ["profile", "marker", "candidate_for", "target", "entry_date"],
            "supported_targets": ["memory.md"],
            "inner_perspective_contract": {
                "requirement_id": "RC13-INNER-001",
                "marker": "inner_perspective",
                "canonical_storage_marker": "Innenperspektive",
                "required_candidate_for": "PERSONA.md",
                "accepted_intake": (
                    'plwc_reflection(operation="write", marker="inner_perspective", '
                    'candidate_for="PERSONA.md", summary="...", evidence="...", trust="high")'
                ),
                "effect": "Records a reflection candidate only; durable PERSONA.md changes still require governed plan/apply.",
                "security": "Persona-only; no direct protected-file mutation; INNER hard gates still apply.",
            },
            "target_behavior": {
                "optional": True,
                "memory.md": "Marks the reflection entry as eligible for governed reflection_memory_promotion.",
                "unsupported_targets": "Unsupported targets fail closed with validation_error.",
                "safety": "target is logical metadata only, not a raw path.",
            },
            "session_journal_prompt": {
                "id": "RC2-PERF-001",
                "guidance": (
                    "At the end of a PLwC session, offer to capture a brief "
                    "Tagebuch/journal entry of the session's insights before "
                    "the context ends."
                ),
                "trigger": "client_judged_session_end",
                "mode": "advisory_only",
                "consent": "Write only with explicit user consent; never unprompted.",
                "no_background_process": True,
                "delivery": "Surfaced as standing guidance in the PLwC user-system-prompt; the gateway does not detect session end or write automatically.",
            },
            "profile_guard": "Omitted profile writes to the resolved active profile. Explicit profile must match the resolved active profile; cross-profile writes are denied.",
            "validation_behavior": {
                "accepted_scope": "Reusable insights about user style, collaboration patterns, project direction, workflow preferences, tool/system behavior and onboarding/profile workflow findings.",
                "promotion_thresholds": "Reflection write does not apply memory/persona promotion thresholds; thresholds belong to Governor promotion/condensation.",
                "supporting_evidence": "Similar valid insights on a new date/context may be accepted as supporting evidence instead of rejected as duplicates.",
                "exact_duplicate": "Exact same content/evidence/date/candidate can return duplicate_noop without appending a second entry.",
            },
            "valid_example": {
                "marker": "observation",
                "trust": "medium",
                "summary": "The profile repeatedly prefers concise implementation reports.",
                "evidence": "2026-05-09",
                "candidate_for": "memory.md",
                "target": "memory.md",
                "canonical_storage": {"marker": "Beobachtung", "trust": "mittel"},
            },
            "invalid_examples": [
                {"marker": "unknown", "reason": "unknown marker"},
                {"trust": "extreme", "reason": "invalid trust value"},
                {"evidence": "today", "reason": "evidence date must be explicit"},
                {"target": "PERSONA.md", "reason": "unsupported target in this slice"},
            ],
            "common_denial_reasons": [
                "invalid_marker",
                "invalid_trust",
                "missing_evidence",
                "invalid_evidence_date",
                "missing_content",
                "rejected_missing_candidate_for",
                "rejected_no_reusable_insight",
                "duplicate_noop",
                "supporting_evidence",
                "cross_profile_write_denied",
                "invalid_target",
            ],
        }
    if scope == "governor":
        return {
            "tool": GOVERNOR_TOOL,
            "dispatch_parameter": "operation",
            "supported_operations": sorted(SUPPORTED_GOVERNOR_OPERATIONS),
            "parameter_contract": pba.governor_parameter_contract(),
            "legacy_tools_replaced": ["plwc_governor_plan", "plwc_governor_apply"],
            "supported_plan_types": [
                PROFILE_CREATION_PLAN_TYPE,
                "profile_import",
                "profile_activation",
                "memory_promotion",
                "persona_promotion",
                "temperament_promotion",
                REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
                REFLECTION_CONDENSATION_PLAN_TYPE,
            ],
            "confirmation": "Apply requires confirmed=true before mutation.",
            "profile_creation_onboarding_schema": profile_onboarding_schema(
                persona_layer_enabled=config.persona_layer_enabled
            ),
            "profile_creation": {
                "plan_type": PROFILE_CREATION_PLAN_TYPE,
                "aliases": sorted(PROFILE_CREATION_PLAN_TYPES - {PROFILE_CREATION_PLAN_TYPE}),
                "purpose": "Create a missing or onboarding-incomplete active profile through governed onboarding.",
                "default_target": (
                    "If the Claude Desktop/security config active profile is missing, "
                    "plwc_governor operation=plan targets that configured profile by default."
                ),
                "apply_instruction": (
                    "Call plwc_governor with operation=plan, plan_type=profile_creation and onboarding_answers, "
                    "then call plwc_governor with operation=apply, plan_type=profile_creation, the same onboarding_answers "
                    "and confirmed=true."
                ),
                "desktop_bootstrap": {
                    "tool_discovery_hint": 'tool_search("plwc") if PLwC tools are not visible yet',
                    "first_status_call": f'{PUBLIC_STATUS_TOOL}(scope="first_run")',
                    "plan_call": (
                        f'{GOVERNOR_TOOL}(operation="plan", plan_type="profile_creation", '
                        "onboarding_answers={...})"
                    ),
                    "apply_call": (
                        f'{GOVERNOR_TOOL}(operation="apply", plan_type="profile_creation", '
                        "onboarding_answers=same, confirmed=true)"
                    ),
                },
                "no_manual_files": "Do not manually create or edit protected profile/governance files during onboarding.",
            },
            "memory_promotion_classification": {
                "explicit_categories": [
                    "explicit_user_decision",
                    "scope_boundary",
                    "security_requirement",
                    "direct_user_instruction",
                ],
                "inferred_categories": ["inferred_observation", "preference", "concern", "rejected_or_unclear"],
                "explicit_category_threshold": "One strong evidence item may be sufficient.",
                "inferred_category_threshold": "Uses configured memory_write_threshold.",
                "marker_policy": "Markers are metadata only; marker text alone never authorizes profile writes.",
                "sorge_policy": "Raw Sorge/concern is not directly promoted unless transformed into an actionable boundary, requirement or explicit decision.",
            },
            "persona_promotion_classification": {
                "explicit_categories": [
                    "explicit_persona_instruction",
                    "style_preference",
                    "interaction_preference",
                    "project_working_style",
                    "safety_behavior_preference",
                ],
                "inferred_categories": ["preference", "rejected_or_unclear"],
                "explicit_category_threshold": "One strong evidence item may be sufficient.",
                "inferred_category_threshold": "Uses configured persona_write_threshold.",
                "target_file": "PERSONA.md",
                "marker_policy": "Markers are metadata only; explicit persona content may pass without marker Muster, but marker text alone never authorizes writes.",
                "inner_perspective_policy": (
                    "RC12-INNER-002 — marker Innenperspektive promotes a 'soft truth' (one sentence + date + "
                    "Quelle) into PERSONA.md, persona-only. One genuine observation is enough (no multi-date "
                    "evidence, no working-pattern phrasing). The INNER hard gates still apply: emotion-as-fact, "
                    "autonomy/agency and ontology claims are rejected even with this marker. Capped at 3 active "
                    "entries; a 4th is denied (inner_truth_limit_reached) until one is retired (governed). "
                    "list_retirable flags the surplus via inner_truth_overflow."
                ),
                "evidence_date_policy": "If evidence text has no YYYY-MM-DD date, entry_date is used as the evidence-date fallback.",
                "conflict_policy": "Conflicting persona instructions in known families such as address formality, PLwC working style, translation fidelity, safety strictness and verbosity become review_required instead of silently appending contradictory content.",
            },
            "temperament_promotion_classification": {
                "explicit_categories": [
                    "tone_shift",
                    "working_style",
                    "collaboration_tendency",
                    "temperament_trait",
                ],
                "inferred_categories": ["preference", "rejected_or_unclear"],
                "explicit_category_threshold": "One evidence item is sufficient (shortcut: N=1).",
                "inferred_category_threshold": "Uses configured temperament_write_threshold (default N=2).",
                "target_file": "TEMPERAMENT.md",
                "markers": "Muster and Beobachtung accepted (persona only accepts Muster).",
                "force_override": "force=true bypasses insufficient_marker and insufficient_evidence; semantic, trust, duplicate and conflict-review gates remain unconditional.",
                "source_provenance": "Optionally supply source_file and source_heading to lock the plan to a Tagebuch entry section. source_sha256 is optional at plan: the gateway computes the canonical SHA-256 (over the LF-normalized entry section) and returns it in data.source_provenance.source_sha256 (source_sha256_canonical=true). Pass that exact value as source_sha256 to apply, where it is required and re-checked. This avoids CRLF/LF mismatches on Windows. data.source_provenance.source_sha256_resolution reports why a canonical SHA was or was not computed: 'resolved', 'file_not_found' (no allowed root holds source_file), or 'heading_not_found' (file present, section heading missing).",
            },
            "reflection_memory_promotion": {
                "purpose": "Promote eligible reflection.md memory candidates into memory.md through governed plan/apply.",
                "apply_instruction": "Call plwc_governor with operation=apply, plan_type=reflection_memory_promotion and confirmed=true.",
                "target_file": "memory.md",
                "non_targets": ["PERSONA.md", "CORE.md", "TEMPERAMENT.md"],
            },
            "reflection_condensation": {
                "purpose": "Condense approved reflection directives, including persona/revision directives.",
                "apply_instruction": "Use plan_id from plwc_governor operation=plan with confirmed=true. The backward-compatible onboarding_answers.approved_plan payload is still accepted.",
                "plan_id_apply": {
                    "supported": True,
                    "plan_id_source": "plwc_governor operation=plan returns a stable runtime plan_id.",
                    "pending_plan_store": "Runtime state under state/pending_plans, outside workspace allowed_roots and outside profile_root.",
                    "security": [
                        "confirmed=true is still required.",
                        "plan_id is strict hexadecimal and cannot target another active profile.",
                        "stored plan snapshots are hash-checked before apply.",
                        "workspace/document operations cannot read or mutate pending plan files.",
                    ],
                },
                "approved_plan_compatibility": "Full onboarding_answers.approved_plan apply remains supported for backward compatibility.",
            },
            "memory_retirement": {
                "operations": ["retire", "list_retirable"],
                "purpose": (
                    "RC8-FEAT-001 — retire an existing active profile entry (status change, never a "
                    "deletion). Retired entries leave the compiled_layer but stay in the file for the "
                    "audit trail."
                ),
                "target_files": list(RETIREMENT_TARGET_FILES),
                "non_targets": ["CORE.md"],
                "retire_instruction": (
                    "Call plwc_governor with operation=retire, target_file, reason and EITHER heading "
                    "(the exact ## [ACTIVE] ... line) OR directive_id (RC12-RETIRE-001 — the stable "
                    "per-section SHA from list_retirable; resolves the ambiguous-heading case when "
                    "several entries share one heading). Optionally conflicts_with. Without confirmed it "
                    "returns a non-mutating plan-preview; re-run with confirmed=true to write the "
                    "[RETIRED] status, retired_at/Grund/conflicts_with and a journaled governor event."
                ),
                "directive_id_selector": (
                    "RC12-RETIRE-001 — directive_id is canonical_section_sha256(heading, body), the same "
                    "per-section identity the indexer uses. It is derived, not stored. A directive_id that "
                    "matches several byte-identical sections is denied with exact_duplicate (no silent "
                    "guess); pass dedup=true to keep one and retire the rest."
                ),
                "list_retirable_instruction": (
                    "Call plwc_governor with operation=list_retirable (optionally target_file) for a "
                    "read-only candidate review. It decides no truth — it surfaces candidates (each with "
                    "its directive_id for an unambiguous retire) and questions; the human retires via a "
                    "confirmed retire."
                ),
                "candidate_criteria": {
                    "history_only": "entry_date older than retirement_age_threshold_days (governance/config.yaml, default 90; lower it for young profiles).",
                    "superseded": (
                        "a lower version only when a higher active same-marker version also has exact "
                        "or near-duplicate content; version number alone is not enough."
                    ),
                    "duplicate": "exact normalized repeat of another active entry's content.",
                    "near_duplicate": (
                        "RC12-RETIRE-002 — high token overlap (symmetric Jaccard) with another active "
                        "entry without being byte-identical; catches near-dupes the exact duplicate check "
                        "misses. Threshold near_duplicate_similarity_threshold (governance/config.yaml, "
                        "default 0.85; 0 disables it)."
                    ),
                    "inner_truth_overflow": "RC12-INNER-002 — more than 3 active Innenperspektive entries in PERSONA.md; the surplus are retirement candidates.",
                    "no_action_rule": "SOFT review flag only — entry yields no action rule/boundary/preference; never auto-retires.",
                },
                "no_action_rule_review_question": NO_ACTION_RULE_REVIEW_QUESTION,
            },
            "qdrant_retrieval": {
                "operations": ["reindex", "drop_index", "retrieve (plwc_profile)"],
                "purpose": (
                    "RC8-FEAT-002 — a reconstructable semantic retrieval index over governed sources "
                    "(v1: memory.md). Read-only evidence; no own memory, no source of truth. OFF by "
                    "default (governance flag qdrant_enabled). No background watcher; reindex is explicit."
                ),
                "enabled_flag": "qdrant_enabled (governance/config.yaml); false ⇒ feature_disabled.",
                "embedding": {
                    "backend": qdrant_index.EMBEDDING_BACKEND,
                    "model": qdrant_index.EMBEDDING_MODEL,
                    "dimension": qdrant_index.EMBEDDING_DIM,
                    "note": "Pinned; no library default and no automatic fallback.",
                },
                "reindex_instruction": (
                    "plwc_governor operation=reindex — explicit full rebuild from the canon; writes only "
                    "derived data; reconstructable."
                ),
                "drop_index_instruction": (
                    "plwc_governor operation=drop_index — deletes the derived index only; loses no "
                    "canonical memory."
                ),
                "retrieve_instruction": (
                    "plwc_profile operation=retrieve, query=... — read-only. Default excludes RETIRED; "
                    "include_retired=true surfaces and marks them. require_fresh=true refuses on a stale "
                    "index (mandatory for Governor-/safety-relevant use). No hit becomes behaviorally "
                    "active without a governed plan/apply."
                ),
                "working_compile_integration": {
                    "requirement_id": RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID,
                    "mode": "compile_mode=working",
                    "query_source": "task_context",
                    "load_bearing_condition": (
                        "Fresh, current ACTIVE memory.md hits are injected into the compact working layer; "
                        "stale, timeout, busy and backend-error states fall back without failing compile."
                    ),
                    "boot_compile_dependency": False,
                    "auto_reindex": False,
                    "max_hits": WORKING_SEMANTIC_MEMORY_HIT_LIMIT,
                },
                "staleness_diagnostics": {
                    "requirement_id": RC15_QDRANT_STALENESS_REQUIREMENT_ID,
                    "fields": [
                        "last_indexed",
                        "source_mtime",
                        "index_meta_mtime",
                        "source_newer_than_index",
                        "staleness_reason",
                        "next_action",
                    ],
                    "stale_next_action": "reindex",
                    "auto_reindex": False,
                    "compile_behavior": (
                        "working compile reports stale retrieve diagnostics as fallback metadata; "
                        "boot and full compile remain independent from Qdrant."
                    ),
                },
                "semantic_readiness_smoke": {
                    "requirement_id": RC15_QDRANT_SMOKE_REQUIREMENT_ID,
                    "checklist": "docs/SMOKE_QDRANT_RC15_DEV0.md",
                    "status": "prepared_not_run",
                    "scope": [
                        "reindex",
                        "bounded fresh retrieve",
                        "working compile semantic memory",
                        "stale fallback",
                        "drop_index fallback",
                        "transport survival",
                    ],
                },
                "index_maintenance_guard": {
                    "requirement_id": RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID,
                    "reindex_timeout_seconds_default": DEFAULT_QDRANT_REINDEX_TIMEOUT_SECONDS,
                    "timeout_error": "qdrant_reindex_timeout",
                    "busy_error": "qdrant_reindex_busy",
                    "drop_busy_error": "qdrant_index_maintenance_busy",
                    "client_cancel_behavior": (
                        "The public reindex wrapper abandons the worker on MCP client cancellation; "
                        "the worker may finish derived index maintenance, but it cannot emit a second response."
                    ),
                    "canonical_memory_mutation": False,
                },
                "staleness_contract": (
                    "Every retrieve returns last_reindex/last_indexed, index_stale, changed_sources, "
                    "source_mtime, index_meta_mtime, source_newer_than_index, staleness_reason, "
                    "next_action, embedding_model and index_fingerprint; each hit carries source_current "
                    "(current/source_changed/source_retired/source_missing) + source_file + section_id + "
                    "canonical SHA. A hit is 'current' only when its own source/heading/SHA match the live canon."
                ),
                "runtime_guard": {
                    "requirement_id": RC14_QDRANT_REQUIREMENT_ID,
                    "timeout_seconds_default": DEFAULT_QDRANT_RETRIEVE_TIMEOUT_SECONDS,
                    "timeout_error": "qdrant_timeout",
                    "busy_error": "qdrant_retrieve_busy",
                    "worker_abandoned": (
                        "A timeout response may leave the backend worker running; a second retrieve for "
                        "the same profile/index returns qdrant_retrieve_busy instead of piling up."
                    ),
                    "diagnostic_fields": [
                        "retrieve_elapsed_seconds",
                        "worker_abandoned",
                        "worker_cancelled",
                        "worker_active",
                        "retryable",
                    ],
                },
            },
            "lifecycle_states": list(GOVERNOR_LIFECYCLE_STATES),
            "stale_plan_behavior": "Stale plans are rejected without target mutation.",
            "duplicate_behavior": "Duplicate candidates become no_op or review_required depending on risk.",
            "review_required_behavior": "Review-required plans do not silently mutate profile files.",
            "common_denial_reasons": [
                "unknown_plan_type",
                "unconfirmed_apply",
                "stale_plan",
                "duplicate_directive_id",
                "invalid_directive_target",
            ],
        }
    if scope == "sandbox":
        return {
            "tools": [PUBLIC_STATUS_TOOL, SANDBOX_RUN_TOOL],
            "status_scope": "sandbox",
            "run_langs": sorted(SUPPORTED_SANDBOX_LANGS),
            "lang_code_semantics": {
                "python": "Inline Python code string evaluated with 'python -c'.",
                "shell": "Shell command string evaluated with 'sh -lc'.",
                "node": "Workspace-relative path to a .js script file (e.g. 'scripts/build.js') run with 'node'.",
            },
            "node_image": "plwc-node-runner:0.1.0",
            "node_image_note": (
                "Build locally: 'docker build -t plwc-node-runner:0.1.0 docker/node-runner/'. "
                "PLwC never pulls images at runtime. "
                "Supply node_modules in the workspace mount; 'npm install' cannot reach a registry inside the sandbox."
            ),
            "node_tmp_noexec": "/tmp is mounted noexec; scripts that execute temp files will fail — this is expected.",
            "legacy_tools_replaced": ["plwc_sandbox_status", "plwc_run_python_sandboxed", "plwc_run_shell_sandboxed"],
            "mount_path": WORKER_CONTAINER_WORKDIR,
            "network": "disabled for controlled workers",
            "pull_policy": "never for controlled workers",
            "runtime_pip": "not allowed for document worker runtime",
            "docker_flags": "server-owned only",
            "limitations": [
                "No host-shell fallback.",
                "No model-supplied Docker mounts.",
                "No model-supplied Docker image selection for governed workers.",
                "No network access inside any sandbox (--network none).",
                "No npm as entrypoint; node runs scripts directly.",
            ],
            "document_worker_distinction": "The document worker is a specialized prepared image, not a generic sandbox fallback.",
        }
    if scope == "profiles":
        return {
            "tools": [
                PROFILE_TOOL,
                GOVERNOR_TOOL,
            ],
            "profile_operations": sorted(SUPPORTED_PROFILE_OPERATIONS),
            "compile_modes": {
                "default": DEFAULT_PROFILE_COMPILE_MODE,
                "supported": sorted(SUPPORTED_COMPILE_MODES),
                "boot": {
                    "purpose": "Small session bootloader; includes core context plus a small hot profile slice.",
                    "default_max_chars": DEFAULT_BOOT_COMPILE_MAX_CHARS,
                    "memory_behavior": "Does not dump full memory.md; includes only a few active anchor/recent entries.",
                },
                "working": {
                    "purpose": "Task-oriented working layer using task_context relevance plus recent active entries.",
                    "default_max_chars": DEFAULT_WORKING_COMPILE_MAX_CHARS,
                    "memory_behavior": "Includes a bounded subset of active memory/persona/temperament entries.",
                    "semantic_memory": {
                        "requirement_id": RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID,
                        "source": "Qdrant over governed memory.md",
                        "gate": "qdrant_enabled=true and non-empty task_context",
                        "freshness": "require_fresh=true; stale indexes fall back without failing compile",
                        "max_hits": WORKING_SEMANTIC_MEMORY_HIT_LIMIT,
                        "fallback_reasons": [
                            "qdrant_disabled",
                            "missing_task_context",
                            "not_indexed",
                            "refused_stale",
                            "qdrant_timeout",
                            "qdrant_retrieve_busy",
                            "qdrant_backend_error",
                            "no_current_hits",
                        ],
                    },
                },
                "full": {
                    "purpose": "Audit/diagnostic mode matching the historical full compiled layer.",
                    "warning": "May consume large session context; not recommended as the normal session start.",
                },
                "compile_max_chars": {
                    "range": [MIN_COMPACT_COMPILE_MAX_CHARS, MAX_COMPACT_COMPILE_MAX_CHARS],
                    "zero": "Use the selected mode default.",
                    "ignored_for": "full",
                },
                "persona_layer": {
                    "requirement_id": V1_PERSONA_LAYER_REQUIREMENT_ID,
                    "parameter": "persona_layer",
                    "extension_config_key": "persona_layer_disabled",
                    "env_var": PERSONA_LAYER_DISABLED_ENV_VAR,
                    "extension_config_default": False,
                    "enable_value": False,
                    "legacy_extension_config_key": "persona_layer_enabled",
                    "legacy_env_var": PERSONA_LAYER_ENABLED_ENV_VAR,
                    "legacy_disable_value": False,
                    "default": True,
                    "current_default": config.persona_layer_enabled,
                    "current_default_source": config.persona_layer_enabled_source,
                    "disable_value": True,
                    "core_omission_labels": [
                        "Role",
                        "Rolle",
                        "Assistant role",
                        "Assistant identity",
                        "Identity",
                        "Identitaet",
                        "Persona",
                        "Persona name",
                        "Name",
                        "Voice",
                        "Stimme",
                        "Working context",
                        "Arbeitskontext",
                    ],
                    "behavior": (
                        "When false, compile output omits the PERSONA block and role, identity, voice "
                        "or working-context lines from CORE while preserving CORE safety principles, "
                        "TEMPERAMENT, MEMORY, TASK CONTEXT, hard gates, governance and audit behavior."
                    ),
                    "override_behavior": (
                        "The extension config controls the default. A per-call persona_layer value "
                        "overrides that default for a single compile request."
                    ),
                    "profile_files_mutated": False,
                    "public_tool_expansion": False,
                    "odysseus_prerequisite": True,
                },
            },
            "governor_operations": sorted(SUPPORTED_GOVERNOR_OPERATIONS),
            "doctor": {
                "requirement_id": RC17_CLU_DOCTOR_REQUIREMENT_ID,
                "runner_requirement_id": RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID,
                "operation": "doctor",
                "modes": sorted(SUPPORTED_DOCTOR_MODES),
                "scopes": sorted(SUPPORTED_DOCTOR_SCOPES),
                "runner_scopes": sorted(DOCTOR_RUNNER_SCOPES),
                "default_mode": "clu",
                "source_pack_sha256": CLU_SOURCE_PACK_SHA256,
                "mutation_allowed": False,
                "direct_memory_promotion": False,
                "public_tool_expansion": False,
                "runner_fields": ["checked", "findings", "not_checked"],
                "runner_verdicts": ["PASS", "PASS_WITH_NOTES", "WARN", "FAIL", "BLOCKED", "NEEDS_EVIDENCE"],
                "runner_excluded_checks": [check_id for check_id, _reason in _DOCTOR_EXCLUDED_CHECKS],
                "purpose": (
                    "Read-only diagnostic contract for evidence separation, profile hygiene, "
                    "memory-candidate review, smoke-test evaluation and release-risk triage."
                ),
                "runner_boundary": (
                    "The rc18 runner collects bounded local facts only; it does not run Qdrant maintenance, "
                    "sandbox code, document-worker jobs, package builds, network access or protected-file mutation."
                ),
                "persistent_change_rule": "Doctor may propose candidates or patches; governed plan/apply must perform any persistent change.",
            },
            "legacy_tools_replaced": [
                "plwc_profile_status",
                "plwc_profile_snapshot",
                "plwc_compile_profile",
                "plwc_governor_plan",
                "plwc_governor_apply",
            ],
            "concepts": [
                "active_profile",
                "profile_import",
                "profile_activation",
                "onboarding",
                "governed_profile_mutation",
            ],
            "deletion_supported": False,
            "deletion_note": "Profile deletion is not supported in this public slice.",
            "governance_boundaries": [
                "Profile and governance files are protected from normal workspace tools.",
                "Profile mutation must go through governed plan/apply paths.",
                "First profile creation uses governed onboarding apply with confirmed=true, never manual protected-file edits.",
            ],
            "active_profile_precedence": [
                "An explicitly configured active profile wins over active_profile.json state.",
                "A missing configured active profile becomes the onboarding target and does not fall back to another profile.",
                "An invalid configured active profile reports invalid_configured_profile/setup_required and does not fall back.",
                "When no configured profile exists, active_profile.json may select the active profile and active_profile_source reports plwc_state.",
            ],
            "onboarding_schema": profile_onboarding_schema(persona_layer_enabled=config.persona_layer_enabled),
            "profile_schema": {
                "required_files": [
                    "CORE.md",
                    "TEMPERAMENT.md",
                    "PERSONA.md",
                    "memory.md",
                    "reflection.md",
                    "governance/config.yaml",
                ],
                "optional_files": ["journal.md", "STATE.md", "CONSCIENCE.md"],
                "generated_files": ["compiled_prompt.txt"],
                "governance_config_policy": (
                    "Profile-local thresholds must be integers of at least 1 when present; "
                    "profile-local metadata cannot enable direct workspace profile writes, "
                    "disable governed-tool requirements or disable Governor confirmation."
                ),
                "governance_config_keys": {
                    "memory_write_threshold / persona_write_threshold / temperament_write_threshold": "int promotion thresholds.",
                    "retirement_age_threshold_days": "int; list_retirable history_only age (default 90).",
                    "near_duplicate_similarity_threshold": "0..1; list_retirable near_duplicate (default 0.85; 0 disables).",
                    "inner_redundancy_threshold": "0..1; scan_tagebuch redundancy_warning (default 0.85).",
                    "qdrant_enabled": "bool; enables the Qdrant retrieval index.",
                    "persona_aliases": "RC12-GEN-001 — comma-separated persona self-reference names; the INNER gate blocks third-person self-claims under these (re.escape'd). EMPTY = generic first-person checks only, i.e. NO name-based (third-person) protection (first-person blocking is never weakened).",
                    "user_aliases": "RC12-GEN-001 — comma-separated user names; recognized as user-insight / direct-instruction signals (generic 'user …' always applies).",
                },
            },
        }
    if scope == "describe":
        # RC12-DESC-001 (A) — the describe tool documents itself (the 8th tool), so
        # every public tool is reachable through describe.
        return {
            "tool": DESCRIBE_TOOL,
            "purpose": (
                "Self-documentation: inspect any PLwC tool's operations, fields and contracts "
                "without trial-and-error. Pick a scope per tool."
            ),
            "supported_scopes": sorted(DESCRIBE_SCOPES),
            "scope_aliases": dict(sorted(_DESCRIBE_SCOPE_ALIASES.items())),
            "parameters": {
                "scope": {
                    "required": False,
                    "default": "tools",
                    "choices": sorted(DESCRIBE_SCOPES),
                    "note": "Tool-name aliases are accepted (e.g. 'workspace', 'profile', 'plwc_governor').",
                },
                "detail": {"required": False, "default": "short", "choices": ["short", "full"]},
                "format": {"required": False, "default": "json", "choices": ["json", "markdown"]},
            },
            "scope_to_tool": {
                "tools": "overview of all public tools",
                "status": PUBLIC_STATUS_TOOL,
                "workspace_operation": WORKSPACE_OPERATION_TOOL,
                "document_operation": DOCUMENT_OPERATION_TOOL,
                "reflection": REFLECTION_TOOL,
                "governor": GOVERNOR_TOOL,
                "sandbox": SANDBOX_RUN_TOOL,
                "profiles": PROFILE_TOOL,
                "describe": DESCRIBE_TOOL,
            },
        }
    raise ValueError(f"Unsupported describe scope: {scope}")


def _describe_markdown(scope: str, data: dict[str, Any]) -> str:
    if scope == "tools":
        lines = [
            "# PLwC tools",
            f"Public server: {data['public_server']}",
            f"Public tool count: {data['public_tool_count']}",
            "",
            "## Tool names",
        ]
        lines.extend(f"- {tool_name}" for tool_name in data["tool_names"])
        return "\n".join(lines)
    if scope in {"workspace_operation", "document_operation"}:
        lines = [
            f"# {scope}",
            f"Tool: {data['tool']}",
            "",
            "## Supported operations",
        ]
        lines.extend(f"- {operation}" for operation in data["supported_operations"])
        if "unsupported_operations" in data:
            lines.append("")
            lines.append("## Unsupported operations")
            lines.extend(f"- {operation}" for operation in data["unsupported_operations"])
        return "\n".join(lines)
    return f"# {scope}\n\n```json\n{json.dumps(data, indent=2, sort_keys=True)}\n```"


def _workspace_operation_failure(
    operation: str,
    reason: str,
    requirement_ids: tuple[str, ...],
    *,
    path: str | None = None,
    source_path: str | None = None,
    target_path: str | None = None,
    changed_files: tuple[str, ...] = (),
    read_files: tuple[str, ...] = (),
    error_category: str = "validation_error",
    protected_boundary_decision: str | None = None,
) -> dict[str, Any]:
    is_parameter_validation = error_category == "validation_error"
    payload_requirement_ids = list(requirement_ids)
    if is_parameter_validation and RC16_WORKSPACE_PARAMETER_REQUIREMENT_ID not in payload_requirement_ids:
        payload_requirement_ids.append(RC16_WORKSPACE_PARAMETER_REQUIREMENT_ID)
    payload: dict[str, Any] = {
        "ok": False,
        "operation": operation,
        "policy_decision": "NOT_EVALUATED" if is_parameter_validation else PolicyDecision.DENY.value,
        "decision": "invalid_request" if is_parameter_validation else "denied",
        "reason": reason,
        "error": reason,
        "error_category": error_category,
        "requirement_ids": payload_requirement_ids,
        "changed_files": list(changed_files),
        "read_files": list(read_files),
    }
    if is_parameter_validation:
        payload.update(
            {
                "failure_class": "parameter_validation",
                "policy_evaluated": False,
                "adapter_called": False,
            }
        )
    if path is not None:
        payload["path"] = path
    if source_path is not None:
        payload["source_path"] = source_path
    if target_path is not None:
        payload["target_path"] = target_path
    if protected_boundary_decision:
        payload["protected_boundary_decision"] = protected_boundary_decision
    return payload


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _load_config(config: GatewayConfig | None) -> GatewayConfig:
    return config or load_gateway_config()


def _install_mode() -> str:
    bundle_root = Path(__file__).resolve().parents[3]
    if (bundle_root / "manifest.json").exists():
        return "mcpb_package"
    return "source_tree"


def _profile_state_note(
    *,
    mismatch_reason: str | None,
    configured_profile: str | None,
    state_profile: str | None,
) -> str | None:
    """Return a human-readable explanation when the configured active profile differs
    from the last saved state profile.  This note is informational only — the
    mismatch is not an error; configured profile always wins.  (RC2-UX-001)"""
    if mismatch_reason == "configured_active_profile_takes_precedence_over_active_state":
        return (
            f"Active profile is '{configured_profile}' (from extension config). "
            f"The state file records '{state_profile}' — this is a stale artifact "
            "from a previous session and is NOT an error. "
            "The configured profile always takes precedence over the saved state."
        )
    return None


def _policy_config_note(config_source: str) -> str | None:
    """Explain policy_config_source='defaults' so it is not mistaken for missing
    security configuration.  (RC2-UX-002)"""
    if config_source == "defaults":
        return (
            "Using bundled conservative defaults. "
            "Security is active — no custom plwc_security.json config file is required "
            "for normal use. Custom config is only needed to override specific limits or policies."
        )
    return None


def _filesystem_adapter(config: GatewayConfig) -> SafeFilesystemAdapter:
    return SafeFilesystemAdapter(
        config.allowed_roots,
        base_dir=config.allowed_roots[0] if config.allowed_roots else None,
        protected_path_patterns=config.protected_path_patterns,
        project_root=config.project_root,
        max_binary_bytes=config.workspace_binary_max_bytes,
        max_search_file_bytes=config.workspace_search_max_file_bytes,
        max_search_files_scanned=config.workspace_search_max_files_scanned,
    )


def _document_worker_adapter(config: GatewayConfig) -> DocumentWorkerAdapter:
    return DocumentWorkerAdapter(
        workspace_roots=config.allowed_roots,
    )


def _profile_adapter(config: GatewayConfig) -> PBAProfileAdapter:
    return PBAProfileAdapter(
        profile_root=config.profile_root,
        memory_write_threshold=config.governance.memory_write_threshold,
        persona_write_threshold=config.governance.persona_write_threshold,
        temperament_write_threshold=config.governance.temperament_write_threshold,
        memory_write_threshold_source=config.governance.memory_write_threshold_source,
        persona_write_threshold_source=config.governance.persona_write_threshold_source,
        temperament_write_threshold_source=config.governance.temperament_write_threshold_source,
        active_profile_name=config.active_profile_name,
        configured_active_profile_name=config.configured_active_profile_name,
        active_profile_source=config.active_profile_source,
        active_profile_state_file=config.active_profile_state_file,
        pending_plan_root=config.pending_plan_root,
        persona_layer_enabled=config.persona_layer_enabled,
    )


def _selected_profile(profile: str, config: GatewayConfig) -> str:
    return profile.strip() or config.configured_active_profile_name or config.active_profile_name


def _selected_onboarding_profile(
    profile: str,
    config: GatewayConfig,
    onboarding_answers: dict[str, Any] | None,
) -> str:
    explicit_profile = profile.strip()
    if explicit_profile:
        return explicit_profile
    answer_profile = _profile_name_from_onboarding_answers(onboarding_answers)
    return answer_profile or config.configured_active_profile_name or config.active_profile_name


def _selected_governor_profile(
    profile: str,
    config: GatewayConfig,
    onboarding_answers: dict[str, Any] | None,
    plan_type: str,
) -> str:
    normalized_plan_type = plan_type.strip().casefold().replace("-", "_")
    if normalized_plan_type == "profile_activation":
        return profile.strip()
    if normalized_plan_type == "profile_import":
        return profile.strip() or _profile_import_target_from_answers(onboarding_answers)
    return _selected_onboarding_profile(profile, config, onboarding_answers)


# ---------------------------------------------------------------------------
# RC8-FEAT-002 — Qdrant retrieval index facade wiring (Phase 4)
# ---------------------------------------------------------------------------


def _qdrant_enabled_for(config: GatewayConfig, profile: str) -> bool:
    """Layered activation (RC10-FEAT-001), matching the write-threshold precedence
    (the config-window / extension value wins; the profile file is the fallback):
    1. the config-window / extension value ``PLWC_QDRANT_ENABLED``, when set
       (so the checkbox is authoritative and is not silently overridden);
    2. otherwise the profile's own ``governance/config.yaml`` ``qdrant_enabled``
       (this still works when PLwC runs without the config window, e.g. tests);
    3. otherwise OFF.
    """
    env_value = os.environ.get("PLWC_QDRANT_ENABLED")
    if env_value is not None and env_value.strip() != "":
        return qdrant_index.qdrant_enabled({qdrant_index.QDRANT_ENABLED_KEY: env_value})
    cfg = config.profile_root / profile / "governance" / "config.yaml"
    if not cfg.is_file():
        return False
    values: dict[str, str] = {}
    for line in cfg.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and ":" in stripped:
            key, value = stripped.split(":", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return qdrant_index.qdrant_enabled(values)


def _qdrant_paths(config: GatewayConfig, profile: str) -> tuple[Path, Path]:
    """Resolve (memory_path, storage_dir) for a profile. Storage is per-profile,
    derived data under the workspace root."""
    memory_path = config.profile_root / profile / "memory.md"
    workspace = config.allowed_roots[0] if config.allowed_roots else config.project_root
    storage_dir = Path(workspace) / qdrant_index.QDRANT_STORAGE_SUBDIR / profile
    return memory_path, storage_dir


def _active_promotion_entries(profile_dir: Path) -> list[dict[str, str]]:
    """RC12-INNER-001 — the ACTIVE entries of the redundancy targets (memory.md +
    TEMPERAMENT.md) as ``{target_file, heading, text}`` for the scan redundancy
    check. Read-only."""
    entries: list[dict[str, str]] = []
    for filename in ("memory.md", "TEMPERAMENT.md"):
        path = profile_dir / filename
        if not path.is_file():
            continue
        for entry in pba._parse_profile_entries(path.read_text(encoding="utf-8")):
            if entry["status"] == "ACTIVE":
                entries.append(
                    {
                        "target_file": filename,
                        "heading": entry["heading"],
                        "text": f"{entry['heading']}\n{entry['body']}".strip(),
                    }
                )
    return entries


def _inner_redundancy_threshold(config: GatewayConfig, profile: str) -> float:
    """RC12-INNER-001 — read ``inner_redundancy_threshold`` from the profile's
    governance config (default DEFAULT_INNER_REDUNDANCY_THRESHOLD)."""
    cfg = config.profile_root / profile / "governance" / "config.yaml"
    default = pba.DEFAULT_INNER_REDUNDANCY_THRESHOLD
    if not cfg.is_file():
        return default
    for line in cfg.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("inner_redundancy_threshold") and ":" in stripped:
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return pba._ratio_value(value, default)
    return default


def _inner_name_aliases(config: GatewayConfig, profile: str) -> tuple[str, ...]:
    """RC12-GEN-001 — configured persona_aliases + user_aliases for the active
    profile, so scan_tagebuch suppresses the persona/user names as scan themes
    instead of a hard-coded list."""
    cfg = config.profile_root / profile / "governance" / "config.yaml"
    if not cfg.is_file():
        return ()
    values: dict[str, str] = {}
    for line in cfg.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and ":" in stripped:
            key, value = stripped.split(":", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return pba._parse_alias_list(values.get("persona_aliases")) + pba._parse_alias_list(values.get("user_aliases"))


_DOCTOR_REQUIRED_PROFILE_FILES = (
    "CORE.md",
    "TEMPERAMENT.md",
    "PERSONA.md",
    "memory.md",
    "reflection.md",
    "governance/config.yaml",
)
_DOCTOR_OPTIONAL_PROFILE_FILES = ("journal.md", "STATE.md", "CONSCIENCE.md")
_DOCTOR_EXCLUDED_CHECKS = (
    ("qdrant_live_retrieval", "Doctor does not run semantic retrieval."),
    ("qdrant_reindex_or_drop", "Doctor does not mutate derived Qdrant indexes."),
    ("sandbox_execution", "Doctor does not execute code or shell commands."),
    ("document_worker_execution", "Doctor does not start document-worker jobs."),
    ("package_build", "Doctor does not build or pack release artifacts."),
    ("full_source_scan", "Doctor does not run an unbounded source scan."),
    ("network_access", "Doctor does not access the network."),
)


def _doctor_checked(
    check_id: str,
    *,
    scope: str,
    status: str,
    evidence: list[str],
    source: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "scope": scope,
        "status": status,
        "source": source,
        "evidence": evidence,
        "requirement_id": RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID,
    }


def _doctor_finding(
    finding_id: str,
    *,
    severity: str,
    title: str,
    verdict: str,
    evidence: list[str],
    recommendation: str,
    checked_item: str,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "severity": severity,
        "title": title,
        "verdict": verdict,
        "evidence": evidence,
        "recommendation": recommendation,
        "checked_item": checked_item,
        "requirement_id": RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID,
    }


def _doctor_not_checked(check_id: str, *, scope: str, reason: str) -> dict[str, str]:
    return {
        "id": check_id,
        "scope": scope,
        "reason": reason,
        "requirement_id": RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID,
    }


def _doctor_can_open(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def _doctor_profile_presence(config: GatewayConfig, profile: str) -> dict[str, Any]:
    profile_dir = config.profile_root / profile
    required = {name: (profile_dir / name).is_file() for name in _DOCTOR_REQUIRED_PROFILE_FILES}
    optional = {name: (profile_dir / name).is_file() for name in _DOCTOR_OPTIONAL_PROFILE_FILES}
    files = {**required, **optional}
    governance_config = profile_dir / "governance" / "config.yaml"
    return {
        "profile_dir_exists": profile_dir.is_dir(),
        "files": files,
        "required_files": required,
        "optional_files": optional,
        "missing_required_files": [name for name, present in required.items() if not present],
        "missing_optional_files": [name for name, present in optional.items() if not present],
        "governance_config_readable": governance_config.is_file() and _doctor_can_open(governance_config),
    }


def _doctor_general_checks(
    config: GatewayConfig,
    *,
    profile: str,
    profile_presence: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    checked: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    not_checked: list[dict[str, str]] = []

    tool_count = len(PUBLIC_TOOLS)
    boundary_ok = tool_count == 8 and "plwc_doctor" not in PUBLIC_TOOLS
    checked.append(
        _doctor_checked(
            "public_boundary.tool_count",
            scope="general",
            status="PASS" if boundary_ok else "FAIL",
            source="PUBLIC_TOOLS",
            evidence=[
                f"public_server={PUBLIC_SERVER_NAME}",
                f"public_tool_count={tool_count}",
                "plwc_doctor_present=false" if "plwc_doctor" not in PUBLIC_TOOLS else "plwc_doctor_present=true",
            ],
        )
    )
    findings.append(
        _doctor_finding(
            "public_boundary.tool_count",
            severity="INFO" if boundary_ok else "BLOCKER",
            title="Public boundary exposes the expected facade tool set.",
            verdict="PASS" if boundary_ok else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "Keep Doctor under plwc_profile; do not add a public plwc_doctor tool."
                if boundary_ok
                else "Restore the eight-tool public boundary before release."
            ),
            checked_item="public_boundary.tool_count",
        )
    )

    checked.append(
        _doctor_checked(
            "runtime.version",
            scope="general",
            status="PASS",
            source="plwc_gateway.__version__",
            evidence=[f"runtime_version={__version__}"],
        )
    )
    findings.append(
        _doctor_finding(
            "runtime.version.reported",
            severity="INFO",
            title="Runtime version is available for smoke comparison.",
            verdict="PASS",
            evidence=checked[-1]["evidence"],
            recommendation="Compare this value with package and Desktop smoke evidence before release.",
            checked_item="runtime.version",
        )
    )

    thresholds = config.governance.as_dict()
    threshold_values_ok = all(
        int(thresholds[name]) >= 1
        for name in ("memory_write_threshold", "persona_write_threshold", "temperament_write_threshold")
    )
    checked.append(
        _doctor_checked(
            "config.governance_thresholds",
            scope="general",
            status="PASS" if threshold_values_ok else "FAIL",
            source="GatewayConfig.governance",
            evidence=[
                f"memory_write_threshold_source={thresholds['memory_write_threshold_source']}",
                f"persona_write_threshold_source={thresholds['persona_write_threshold_source']}",
                f"temperament_write_threshold_source={thresholds['temperament_write_threshold_source']}",
            ],
        )
    )
    findings.append(
        _doctor_finding(
            "config.governance_thresholds",
            severity="INFO" if threshold_values_ok else "HIGH",
            title="Governance thresholds are surfaced through runtime config.",
            verdict="PASS" if threshold_values_ok else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "Keep threshold sources visible in status and Doctor output."
                if threshold_values_ok
                else "Repair invalid governance threshold values before running governed promotion."
            ),
            checked_item="config.governance_thresholds",
        )
    )

    missing_required = profile_presence["missing_required_files"]
    checked.append(
        _doctor_checked(
            "profile_schema.required_files",
            scope="general",
            status="PASS" if not missing_required else "FAIL",
            source="profile file presence",
            evidence=[
                f"profile={profile}",
                f"profile_dir_exists={str(profile_presence['profile_dir_exists']).lower()}",
                "missing_required_files=" + (",".join(missing_required) if missing_required else "none"),
            ],
        )
    )
    findings.append(
        _doctor_finding(
            "profile_schema.required_files",
            severity="INFO" if not missing_required else "HIGH",
            title="Active profile required-file presence was checked.",
            verdict="PASS" if not missing_required else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "No required profile files are missing."
                if not missing_required
                else "Repair the active profile through governed onboarding or import before relying on compile."
            ),
            checked_item="profile_schema.required_files",
        )
    )

    if config.setup_warnings:
        checked.append(
            _doctor_checked(
                "config.setup_warnings",
                scope="general",
                status="WARN",
                source="GatewayConfig.setup_warnings",
                evidence=[f"setup_warning_count={len(config.setup_warnings)}"],
            )
        )
        findings.append(
            _doctor_finding(
                "config.setup_warnings.present",
                severity="MEDIUM",
                title="Gateway configuration emitted setup warnings.",
                verdict="WARN",
                evidence=checked[-1]["evidence"],
                recommendation="Inspect plwc_status(scope=\"runtime\") for warning details before release.",
                checked_item="config.setup_warnings",
            )
        )
    else:
        checked.append(
            _doctor_checked(
                "config.setup_warnings",
                scope="general",
                status="PASS",
                source="GatewayConfig.setup_warnings",
                evidence=["setup_warning_count=0"],
            )
        )

    not_checked.extend(_doctor_not_checked(check_id, scope="general", reason=reason) for check_id, reason in _DOCTOR_EXCLUDED_CHECKS)
    return checked, findings, not_checked


def _doctor_profile_checks(
    config: GatewayConfig,
    *,
    profile: str,
    profile_presence: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    checked: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    not_checked: list[dict[str, str]] = []

    checked.append(
        _doctor_checked(
            "profile.active_resolution",
            scope="profile",
            status="PASS" if profile else "FAIL",
            source="GatewayConfig active-profile fields",
            evidence=[
                f"active_profile={profile or ''}",
                f"active_profile_source={config.active_profile_source}",
                f"configured_active_profile={config.configured_active_profile_name or ''}",
            ],
        )
    )
    findings.append(
        _doctor_finding(
            "profile.active_resolution",
            severity="INFO" if profile else "HIGH",
            title="Active profile resolution is explicit.",
            verdict="PASS" if profile else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "Use this resolved profile for read-only checks."
                if profile
                else "Configure or create an active profile before relying on Doctor."
            ),
            checked_item="profile.active_resolution",
        )
    )

    missing_required = profile_presence["missing_required_files"]
    checked.append(
        _doctor_checked(
            "profile.required_files",
            scope="profile",
            status="PASS" if not missing_required else "FAIL",
            source="profile file presence",
            evidence=["missing_required_files=" + (",".join(missing_required) if missing_required else "none")],
        )
    )
    findings.append(
        _doctor_finding(
            "profile.required_files",
            severity="INFO" if not missing_required else "HIGH",
            title="Required profile files are present.",
            verdict="PASS" if not missing_required else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "Required profile skeleton is present."
                if not missing_required
                else "Restore missing required files through governed profile tools."
            ),
            checked_item="profile.required_files",
        )
    )

    missing_optional = profile_presence["missing_optional_files"]
    checked.append(
        _doctor_checked(
            "profile.optional_files",
            scope="profile",
            status="PASS_WITH_NOTES" if missing_optional else "PASS",
            source="profile file presence",
            evidence=["missing_optional_files=" + (",".join(missing_optional) if missing_optional else "none")],
        )
    )
    if missing_optional:
        findings.append(
            _doctor_finding(
                "profile.optional_files.missing",
                severity="LOW",
                title="Some optional profile files are absent.",
                verdict="PASS_WITH_NOTES",
                evidence=checked[-1]["evidence"],
                recommendation="No repair is required unless the feature depending on the optional file is needed.",
                checked_item="profile.optional_files",
            )
        )

    checked.append(
        _doctor_checked(
            "profile.governance_config_readable",
            scope="profile",
            status="PASS" if profile_presence["governance_config_readable"] else "FAIL",
            source="governance/config.yaml open check",
            evidence=[f"governance_config_readable={str(profile_presence['governance_config_readable']).lower()}"],
        )
    )
    findings.append(
        _doctor_finding(
            "profile.governance_config_readable",
            severity="INFO" if profile_presence["governance_config_readable"] else "HIGH",
            title="Governance config readability was checked without returning contents.",
            verdict="PASS" if profile_presence["governance_config_readable"] else "FAIL",
            evidence=checked[-1]["evidence"],
            recommendation=(
                "Keep governance config readable only through governed profile paths."
                if profile_presence["governance_config_readable"]
                else "Repair governance/config.yaml before using governed profile operations."
            ),
            checked_item="profile.governance_config_readable",
        )
    )

    not_checked.extend(_doctor_not_checked(check_id, scope="profile", reason=reason) for check_id, reason in _DOCTOR_EXCLUDED_CHECKS)
    not_checked.append(
        _doctor_not_checked(
            "protected_file_content_review",
            scope="profile",
            reason="Doctor checks presence/readability but does not return protected profile file contents.",
        )
    )
    return checked, findings, not_checked


def _doctor_smoke_checks(
    *,
    task_context: str,
    query: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    checked: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    not_checked: list[dict[str, str]] = []
    evidence_text = f"{task_context}\n{query}".strip()
    evidence_lower = evidence_text.casefold()
    has_smoke_hint = "smoke" in evidence_lower or "desktop" in evidence_lower
    has_package_hint = "package" in evidence_lower or "mcpb" in evidence_lower or "sha" in evidence_lower
    mentions_runtime_version = bool(__version__ and __version__ in evidence_text)

    checked.append(
        _doctor_checked(
            "smoke.runtime_version",
            scope="smoke",
            status="PASS",
            source="plwc_gateway.__version__",
            evidence=[f"runtime_version={__version__}"],
        )
    )
    findings.append(
        _doctor_finding(
            "smoke.runtime_version.available",
            severity="INFO",
            title="Runtime version is available for smoke report comparison.",
            verdict="PASS",
            evidence=checked[-1]["evidence"],
            recommendation="Compare this runtime version with the package and Desktop smoke report.",
            checked_item="smoke.runtime_version",
        )
    )

    checked.append(
        _doctor_checked(
            "smoke.supplied_hints",
            scope="smoke",
            status="PASS_WITH_NOTES" if evidence_text else "NEEDS_EVIDENCE",
            source="doctor task_context/query",
            evidence=[
                f"has_smoke_hint={str(has_smoke_hint).lower()}",
                f"has_package_hint={str(has_package_hint).lower()}",
                f"mentions_runtime_version={str(mentions_runtime_version).lower()}",
            ],
        )
    )
    if evidence_text:
        findings.append(
            _doctor_finding(
                "smoke.supplied_hints.present",
                severity="LOW",
                title="Smoke/package hints were supplied but not fully verified.",
                verdict="PASS_WITH_NOTES",
                evidence=checked[-1]["evidence"],
                recommendation="Use explicit report path, package SHA256 and runtime version in the smoke evidence.",
                checked_item="smoke.supplied_hints",
            )
        )
    else:
        findings.append(
            _doctor_finding(
                "smoke.supplied_hints.missing",
                severity="MEDIUM",
                title="No smoke/package evidence was supplied to Doctor.",
                verdict="NEEDS_EVIDENCE",
                evidence=checked[-1]["evidence"],
                recommendation="Provide a smoke report path, package SHA256 and observed runtime version for comparison.",
                checked_item="smoke.supplied_hints",
            )
        )

    if not has_smoke_hint:
        not_checked.append(
            _doctor_not_checked(
                "smoke_report.verdict",
                scope="smoke",
                reason="No smoke report verdict hint was supplied in task_context or query.",
            )
        )
    if not has_package_hint:
        not_checked.append(
            _doctor_not_checked(
                "package_report.sha256",
                scope="smoke",
                reason="No package hash or MCPB hint was supplied in task_context or query.",
            )
        )
    if not mentions_runtime_version:
        not_checked.append(
            _doctor_not_checked(
                "smoke_report.runtime_version_match",
                scope="smoke",
                reason="Supplied hints do not mention the current runtime version.",
            )
        )
    not_checked.extend(_doctor_not_checked(check_id, scope="smoke", reason=reason) for check_id, reason in _DOCTOR_EXCLUDED_CHECKS)
    return checked, findings, not_checked


def _clu_doctor_runner(
    config: GatewayConfig,
    *,
    profile: str,
    doctor_scope: str,
    task_context: str,
    query: str,
    profile_presence: dict[str, Any],
) -> dict[str, Any]:
    if doctor_scope == "general":
        checked, findings, not_checked = _doctor_general_checks(
            config,
            profile=profile,
            profile_presence=profile_presence,
        )
    elif doctor_scope == "profile":
        checked, findings, not_checked = _doctor_profile_checks(
            config,
            profile=profile,
            profile_presence=profile_presence,
        )
    elif doctor_scope == "smoke":
        checked, findings, not_checked = _doctor_smoke_checks(
            task_context=task_context,
            query=query,
        )
    else:
        checked = []
        findings = [
            _doctor_finding(
                f"{doctor_scope}.runner.not_implemented",
                severity="LOW",
                title="Deterministic Doctor runner is not implemented for this scope yet.",
                verdict="NEEDS_EVIDENCE",
                evidence=[f"doctor_scope={doctor_scope}", "runner_active=false"],
                recommendation="Use general, profile or smoke for deterministic rc18 checks.",
                checked_item=f"{doctor_scope}.runner",
            )
        ]
        not_checked = [
            _doctor_not_checked(
                f"{doctor_scope}.deterministic_checks",
                scope=doctor_scope,
                reason="RC18 implements deterministic checks only for general, profile and smoke.",
            )
        ]
        not_checked.extend(_doctor_not_checked(check_id, scope=doctor_scope, reason=reason) for check_id, reason in _DOCTOR_EXCLUDED_CHECKS)

    return {
        "requirement_id": RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID,
        "runner_active": doctor_scope in DOCTOR_RUNNER_SCOPES,
        "implemented_scopes": sorted(DOCTOR_RUNNER_SCOPES),
        "checked_count": len(checked),
        "finding_count": len(findings),
        "not_checked_count": len(not_checked),
        "checked": checked,
        "findings": findings,
        "not_checked": not_checked,
    }


def _clu_doctor_payload(
    config: GatewayConfig,
    *,
    profile: str,
    doctor_scope: str,
    task_context: str,
    query: str,
) -> dict[str, Any]:
    profile_presence = _doctor_profile_presence(config, profile)
    runner = _clu_doctor_runner(
        config,
        profile=profile,
        doctor_scope=doctor_scope,
        task_context=task_context,
        query=query,
        profile_presence=profile_presence,
    )
    scope_guidance = {
        "general": "Use CLU for evidence separation, consistency checks and governance-risk triage.",
        "profile": "Review CORE, PERSONA, TEMPERAMENT and memory consistency without mutating protected files.",
        "memory": "Treat every persistent-memory suggestion as a candidate until governed apply confirms it.",
        "smoke": "Compare smoke verdicts against observed evidence and mark contradictions as release risks.",
        "workspace": "Check path scope, ALLOW/DENY reasons, audit metadata and mutation boundaries.",
        "release": "Classify missing evidence, stale artifacts, transport failures and public-boundary drift.",
    }
    return {
        "ok": True,
        "facade": PROFILE_TOOL,
        "operation": "doctor",
        "doctor_mode": "clu",
        "doctor_scope": doctor_scope,
        "profile": profile,
        "policy_decision": PolicyDecision.ALLOW.value,
        "mutation_allowed": False,
        "writes_allowed": False,
        "applies_patches": False,
        "promotes_memory": False,
        "source_pack": {
            "name": "clu80_persona_pack.zip",
            "version": CLU_SOURCE_PACK_VERSION,
            "sha256": CLU_SOURCE_PACK_SHA256,
            "profile_id": "clu",
            "source_profile_id": "clu80",
        },
        "contract": {
            "requirement_id": RC17_CLU_DOCTOR_REQUIREMENT_ID,
            "role": "controlled PLwC diagnostic and consistency mode",
            "inherits_global_core": True,
            "global_core_wins": True,
            "allowed_outputs": [
                "findings",
                "risk classifications",
                "evidence tables",
                "patch proposals",
                "memory candidates",
                "smoke-test prompts",
                "consistency reports",
                "audit notes",
                "suggested diffs",
            ],
            "hard_prohibitions": [
                "no autonomous persistent writes",
                "no direct memory promotion",
                "no self-description written into memory as fact",
                "no invented personal facts",
                "no governance-threshold weakening",
                "no bypass of governed apply, explicit confirmation or audit logging",
                "no claim that a file was modified unless it actually changed",
                "no assumption that recent metadata makes old content current",
            ],
            "severity_levels": ["INFO", "LOW", "MEDIUM", "HIGH", "BLOCKER"],
            "verdicts": ["PASS", "PASS_WITH_NOTES", "NEEDS_EVIDENCE", "NEEDS_CONFIRMATION", "FAIL", "BLOCKED"],
        },
        "recommended_output_shape": [
            "Status",
            "Finding",
            "Evidence",
            "Risk",
            "Recommendation",
            "Patch candidate",
        ],
        "scope_guidance": scope_guidance[doctor_scope],
        "doctor_runner": {
            "requirement_id": runner["requirement_id"],
            "runner_active": runner["runner_active"],
            "implemented_scopes": runner["implemented_scopes"],
            "checked_count": runner["checked_count"],
            "finding_count": runner["finding_count"],
            "not_checked_count": runner["not_checked_count"],
            "read_only": True,
        },
        "checked": runner["checked"],
        "findings": runner["findings"],
        "not_checked": runner["not_checked"],
        "profile_presence": profile_presence,
        "task_context": task_context,
        "query": query,
        "next_actions": [
            "Inspect evidence before issuing a verdict.",
            "Return candidates instead of applying protected changes.",
            "Use governed plan/apply for any persistent profile or memory change.",
            "Record missing evidence as NEEDS_EVIDENCE instead of guessing.",
        ],
        "requirement_ids": list(FACADE_REQUIREMENTS)
        + [RC17_CLU_DOCTOR_REQUIREMENT_ID, RC18_CLU_DOCTOR_RUNNER_REQUIREMENT_ID],
    }


def _qdrant_feature_disabled_payload(facade: str, operation: str) -> dict[str, Any]:
    return {
        "ok": True,
        "facade": facade,
        "operation": operation,
        "feature_disabled": True,
        "reason": "feature_disabled",
        "detail": "Qdrant retrieval index is OFF (governance flag qdrant_enabled is false).",
    }


def _qdrant_error_payload(facade: str, operation: str, error: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "facade": facade,
        "operation": operation,
        "error": str(error),
        "error_category": "qdrant_" + type(error).__name__,
    }


def _qdrant_structured_error_payload(
    facade: str,
    operation: str,
    *,
    reason: str,
    detail: str,
    timeout_seconds: float | None = None,
    base_requirement_ids: list[str] | None = None,
    extra_requirement_ids: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    include_hits: bool = True,
) -> dict[str, Any]:
    if base_requirement_ids is None:
        base_requirement_ids = [RC13_QDRANT_REQUIREMENT_ID]
    requirement_ids = list(FACADE_REQUIREMENTS)
    for requirement_id in list(base_requirement_ids) + list(extra_requirement_ids or []):
        if requirement_id not in requirement_ids:
            requirement_ids.append(requirement_id)
    payload: dict[str, Any] = {
        "ok": False,
        "facade": facade,
        "operation": operation,
        "error": detail,
        "error_category": reason,
        "reason": reason,
        "feature_disabled": False,
        "requirement_ids": requirement_ids,
    }
    if include_hits:
        payload["hits"] = []
    if timeout_seconds is not None:
        payload["timeout_seconds"] = timeout_seconds
    if extra:
        payload.update(extra)
    return payload


def _append_requirement_ids(payload: dict[str, Any], *requirement_ids: str) -> None:
    existing = payload.setdefault("requirement_ids", [])
    if not isinstance(existing, list):
        payload["requirement_ids"] = list(requirement_ids)
        return
    for requirement_id in requirement_ids:
        if requirement_id not in existing:
            existing.append(requirement_id)


def _qdrant_retrieve_lock(profile: str, storage_dir: Path) -> threading.Lock:
    key = (profile, str(storage_dir.resolve()))
    with _QDRANT_RETRIEVE_LOCKS_GUARD:
        lock = _QDRANT_RETRIEVE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _QDRANT_RETRIEVE_LOCKS[key] = lock
        return lock


def _qdrant_retrieve_timeout_seconds() -> float:
    raw = os.environ.get("PLWC_QDRANT_RETRIEVE_TIMEOUT_SECONDS", "").strip()
    if raw:
        try:
            value = float(raw)
        except ValueError:
            return DEFAULT_QDRANT_RETRIEVE_TIMEOUT_SECONDS
        if value > 0:
            return min(value, DEFAULT_QDRANT_RETRIEVE_TIMEOUT_SECONDS)
    return DEFAULT_QDRANT_RETRIEVE_TIMEOUT_SECONDS


def _qdrant_maintenance_lock(profile: str, storage_dir: Path) -> threading.Lock:
    key = (profile, str(storage_dir.resolve()))
    with _QDRANT_MAINTENANCE_LOCKS_GUARD:
        lock = _QDRANT_MAINTENANCE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _QDRANT_MAINTENANCE_LOCKS[key] = lock
        return lock


def _qdrant_reindex_timeout_seconds() -> float:
    raw = os.environ.get("PLWC_QDRANT_REINDEX_TIMEOUT_SECONDS", "").strip()
    if raw:
        try:
            value = float(raw)
        except ValueError:
            return DEFAULT_QDRANT_REINDEX_TIMEOUT_SECONDS
        if value > 0:
            return min(value, DEFAULT_QDRANT_REINDEX_TIMEOUT_SECONDS)
    return DEFAULT_QDRANT_REINDEX_TIMEOUT_SECONDS


def _qdrant_maintenance_busy_payload(*, operation: str, started: float) -> dict[str, Any]:
    return _qdrant_structured_error_payload(
        GOVERNOR_TOOL,
        operation,
        reason="qdrant_reindex_busy" if operation == "reindex" else "qdrant_index_maintenance_busy",
        detail=(
            "A previous Qdrant index maintenance worker is still running for this profile/index. "
            "Retry later; boot and full compile remain independent from Qdrant."
        ),
        base_requirement_ids=[],
        extra_requirement_ids=[RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID],
        extra={
            "retryable": True,
            "worker_active": True,
            "maintenance_elapsed_seconds": round(time.perf_counter() - started, 3),
        },
        include_hits=False,
    )


def _bounded_qdrant_reindex(*, profile: str, memory_path: Path, storage_dir: Path) -> dict[str, Any]:
    """RC16: explicit reindex must not hang or crash the public transport."""
    started = time.perf_counter()
    timeout_seconds = _qdrant_reindex_timeout_seconds()
    maintenance_lock = _qdrant_maintenance_lock(profile, storage_dir)
    if not maintenance_lock.acquire(blocking=False):
        return _qdrant_maintenance_busy_payload(operation="reindex", started=started)

    def call() -> dict[str, Any]:
        try:
            return qdrant_index.reindex_profile(profile=profile, memory_path=memory_path, storage_dir=storage_dir)
        finally:
            maintenance_lock.release()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="plwc-qdrant-reindex")
    future = executor.submit(call)
    try:
        payload = future.result(timeout=timeout_seconds)
        payload["facade"] = GOVERNOR_TOOL
        payload["operation"] = "reindex"
        payload["reindex_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(payload, RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID)
        return payload
    except concurrent.futures.TimeoutError:
        cancelled = future.cancel()
        if cancelled and maintenance_lock.locked():
            maintenance_lock.release()
        return _qdrant_structured_error_payload(
            GOVERNOR_TOOL,
            "reindex",
            reason="qdrant_reindex_timeout",
            detail=(
                "Qdrant reindex exceeded the bounded public timeout. "
                "Retry later; boot and full compile remain independent from Qdrant."
            ),
            timeout_seconds=timeout_seconds,
            base_requirement_ids=[],
            extra_requirement_ids=[RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID],
            extra={
                "retryable": True,
                "worker_abandoned": not cancelled,
                "worker_cancelled": cancelled,
                "reindex_elapsed_seconds": round(time.perf_counter() - started, 3),
            },
            include_hits=False,
        )
    except qdrant_index.QdrantError as exc:
        payload = _qdrant_error_payload(GOVERNOR_TOOL, "reindex", exc)
        payload["reindex_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(payload, RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID)
        return payload
    except Exception as exc:
        return _qdrant_structured_error_payload(
            GOVERNOR_TOOL,
            "reindex",
            reason="qdrant_reindex_backend_error",
            detail=f"{type(exc).__name__}: {exc}",
            base_requirement_ids=[],
            extra_requirement_ids=[RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID],
            extra={"reindex_elapsed_seconds": round(time.perf_counter() - started, 3)},
            include_hits=False,
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _bounded_qdrant_drop_index(*, profile: str, storage_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    maintenance_lock = _qdrant_maintenance_lock(profile, storage_dir)
    if not maintenance_lock.acquire(blocking=False):
        return _qdrant_maintenance_busy_payload(operation="drop_index", started=started)
    try:
        payload = qdrant_index.drop_index(profile=profile, storage_dir=storage_dir)
        payload["facade"] = GOVERNOR_TOOL
        payload["operation"] = "drop_index"
        payload["drop_index_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(payload, RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID)
        return payload
    except qdrant_index.QdrantError as exc:
        payload = _qdrant_error_payload(GOVERNOR_TOOL, "drop_index", exc)
        payload["drop_index_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(payload, RC15_QDRANT_SMOKE_REQUIREMENT_ID, RC16_QDRANT_MAINTENANCE_REQUIREMENT_ID)
        return payload
    finally:
        maintenance_lock.release()


def _bounded_qdrant_retrieve(
    *,
    profile: str,
    query: str,
    memory_path: Path,
    storage_dir: Path,
    limit: int,
    include_retired: bool,
    require_fresh: bool,
) -> dict[str, Any]:
    """RC13/RC14: optional retrieve must be bounded and non-amplifying."""
    started = time.perf_counter()
    timeout_seconds = _qdrant_retrieve_timeout_seconds()
    retrieve_lock = _qdrant_retrieve_lock(profile, storage_dir)
    if not retrieve_lock.acquire(blocking=False):
        return _qdrant_structured_error_payload(
            PROFILE_TOOL,
            "retrieve",
            reason="qdrant_retrieve_busy",
            detail=(
                "A previous Qdrant retrieve is still running for this profile/index. "
                "Retry later, use compile boot/full, or rely on working compile fallback metadata."
            ),
            extra_requirement_ids=[RC14_QDRANT_REQUIREMENT_ID],
            extra={
                "retryable": True,
                "worker_active": True,
                "retrieve_elapsed_seconds": round(time.perf_counter() - started, 3),
            },
        )

    def call() -> dict[str, Any]:
        try:
            return qdrant_index.retrieve(
                profile=profile,
                query=query,
                memory_path=memory_path,
                storage_dir=storage_dir,
                limit=limit,
                include_retired=include_retired,
                require_fresh=require_fresh,
            )
        finally:
            retrieve_lock.release()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="plwc-qdrant-retrieve")
    future = executor.submit(call)
    try:
        payload = future.result(timeout=timeout_seconds)
        payload["facade"] = PROFILE_TOOL
        payload["retrieve_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(
            payload,
            RC13_QDRANT_REQUIREMENT_ID,
            RC14_QDRANT_REQUIREMENT_ID,
            RC15_QDRANT_STALENESS_REQUIREMENT_ID,
        )
        return payload
    except concurrent.futures.TimeoutError:
        cancelled = future.cancel()
        if cancelled and retrieve_lock.locked():
            retrieve_lock.release()
        return _qdrant_structured_error_payload(
            PROFILE_TOOL,
            "retrieve",
            reason="qdrant_timeout",
            detail=(
                "Qdrant retrieve exceeded the bounded public timeout. "
                "Retry after reindexing, use compile boot/full, or rely on working compile fallback metadata."
            ),
            timeout_seconds=timeout_seconds,
            extra_requirement_ids=[RC14_QDRANT_REQUIREMENT_ID],
            extra={
                "retryable": True,
                "worker_abandoned": not cancelled,
                "worker_cancelled": cancelled,
                "retrieve_elapsed_seconds": round(time.perf_counter() - started, 3),
            },
        )
    except qdrant_index.QdrantError as exc:
        payload = _qdrant_error_payload(PROFILE_TOOL, "retrieve", exc)
        payload["retrieve_elapsed_seconds"] = round(time.perf_counter() - started, 3)
        _append_requirement_ids(payload, RC13_QDRANT_REQUIREMENT_ID, RC14_QDRANT_REQUIREMENT_ID)
        return payload
    except Exception as exc:
        return _qdrant_structured_error_payload(
            PROFILE_TOOL,
            "retrieve",
            reason="qdrant_backend_error",
            detail=f"{type(exc).__name__}: {exc}",
            extra_requirement_ids=[RC14_QDRANT_REQUIREMENT_ID],
            extra={"retrieve_elapsed_seconds": round(time.perf_counter() - started, 3)},
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _working_compile_semantic_memory(
    config: GatewayConfig,
    *,
    profile: str,
    task_context: str,
) -> dict[str, Any]:
    """RC14-QDRANT-002: fresh semantic memory for working compile, best-effort."""
    metadata: dict[str, Any] = {
        "requirement_id": RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID,
        "diagnostics_requirement_id": RC15_QDRANT_STALENESS_REQUIREMENT_ID,
        "source": "qdrant",
        "applies_to": "compile_mode=working",
        "enabled": False,
        "attempted": False,
        "applied": False,
        "fallback": False,
        "reason": "qdrant_disabled",
        "require_fresh": True,
        "include_retired": False,
        "max_hits": WORKING_SEMANTIC_MEMORY_HIT_LIMIT,
        "hits_included": 0,
    }
    if not _qdrant_enabled_for(config, profile):
        return {"block": "", "metadata": metadata}

    metadata["enabled"] = True
    query = " ".join(str(task_context or "").split())
    if not query:
        metadata["reason"] = "missing_task_context"
        return {"block": "", "metadata": metadata}

    memory_path, storage_dir = _qdrant_paths(config, profile)
    retrieve_payload = _bounded_qdrant_retrieve(
        profile=profile,
        query=query,
        memory_path=memory_path,
        storage_dir=storage_dir,
        limit=WORKING_SEMANTIC_MEMORY_HIT_LIMIT,
        include_retired=False,
        require_fresh=True,
    )
    metadata["attempted"] = True
    metadata["retrieve"] = _semantic_memory_retrieve_summary(retrieve_payload)
    if retrieve_payload.get("next_action"):
        metadata["next_action"] = retrieve_payload.get("next_action")

    if retrieve_payload.get("ok") is not True:
        metadata["fallback"] = True
        metadata["reason"] = str(
            retrieve_payload.get("reason")
            or retrieve_payload.get("error_category")
            or "retrieve_failed"
        )
        return {"block": "", "metadata": metadata}

    if retrieve_payload.get("indexed") is False:
        metadata["fallback"] = True
        metadata["reason"] = str(retrieve_payload.get("reason") or "not_indexed")
        return {"block": "", "metadata": metadata}
    if retrieve_payload.get("index_stale") is True:
        metadata["fallback"] = True
        metadata["reason"] = "stale_index"
        return {"block": "", "metadata": metadata}

    hits = _current_semantic_memory_hits(retrieve_payload)
    if not hits:
        metadata["fallback"] = True
        metadata["reason"] = str(retrieve_payload.get("reason") or "no_current_hits")
        return {"block": "", "metadata": metadata}

    metadata["applied"] = True
    metadata["fallback"] = False
    metadata["reason"] = "fresh_current_hits"
    metadata["hits_included"] = len(hits)
    return {"block": _format_semantic_memory_block(hits), "metadata": metadata}


def _semantic_memory_retrieve_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "ok": payload.get("ok"),
        "reason": payload.get("reason"),
        "error_category": payload.get("error_category"),
        "indexed": payload.get("indexed"),
        "index_stale": payload.get("index_stale"),
        "last_reindex": payload.get("last_reindex"),
        "last_indexed": payload.get("last_indexed"),
        "source_mtime": payload.get("source_mtime"),
        "index_meta_mtime": payload.get("index_meta_mtime"),
        "source_newer_than_index": payload.get("source_newer_than_index"),
        "staleness_reason": payload.get("staleness_reason"),
        "next_action": payload.get("next_action"),
        "retrieve_elapsed_seconds": payload.get("retrieve_elapsed_seconds"),
        "worker_abandoned": payload.get("worker_abandoned"),
        "worker_active": payload.get("worker_active"),
    }
    changed_sources = payload.get("changed_sources")
    if isinstance(changed_sources, list):
        summary["changed_sources_count"] = len(changed_sources)
        if len(changed_sources) <= 10:
            summary["changed_sources"] = changed_sources
    return {key: value for key, value in summary.items() if value is not None}


def _current_semantic_memory_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for hit in payload.get("hits") or []:
        if not isinstance(hit, dict):
            continue
        if hit.get("source_file") != "memory.md":
            continue
        if hit.get("lifecycle_status") != "ACTIVE":
            continue
        if hit.get("source_current") != qdrant_index.SOURCE_CURRENT:
            continue
        if not str(hit.get("text") or "").strip():
            continue
        hits.append(hit)
        if len(hits) >= WORKING_SEMANTIC_MEMORY_HIT_LIMIT:
            break
    return hits


def _format_semantic_memory_block(hits: list[dict[str, Any]]) -> str:
    lines = [
        "SEMANTIC MEMORY:",
        "[Fresh Qdrant hits from governed memory.md; read-only, require_fresh=true.]",
    ]
    for hit in hits:
        section_id = _truncate_text(str(hit.get("section_id") or "memory.md section"), 120)
        score = hit.get("score")
        try:
            score_text = f"score={float(score):.3f}"
        except (TypeError, ValueError):
            score_text = "score=unknown"
        excerpt = _semantic_memory_excerpt(str(hit.get("text") or ""))
        lines.append(f"- {section_id} ({score_text}): {excerpt}")
    return "\n".join(lines)


def _semantic_memory_excerpt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    content_lines = [line for line in lines if line.casefold().startswith("inhalt:")]
    if content_lines:
        return _truncate_text(content_lines[0], WORKING_SEMANTIC_MEMORY_ENTRY_MAX_CHARS)
    return _truncate_text(" ".join(lines[:2]), WORKING_SEMANTIC_MEMORY_ENTRY_MAX_CHARS)


def _merge_promotion_parameters(
    onboarding_answers: dict[str, Any] | None,
    *,
    plan_type: str,
    candidate_summary: str = "",
    evidence: str = "",
    trust: str = "",
    marker: str = "",
    confidence: str = "",
    entry_date: str = "",
    candidate_for: str = "",
    reason: str = "",
    target_section: str = "",
    conflicts_with: str = "",
) -> dict[str, Any] | None:
    normalized_plan_type = plan_type.strip().casefold().replace("-", "_")
    if normalized_plan_type not in PROMOTION_PLAN_TYPES:
        return onboarding_answers

    merged: dict[str, Any] = dict(onboarding_answers or {})
    explicit_values = {
        "evidence": evidence,
        "trust": trust,
        "marker": marker,
        "confidence": confidence,
        "entry_date": entry_date,
        "candidate_for": candidate_for,
        "reason": reason,
        "target_section": target_section,
        "conflicts_with": conflicts_with,
    }
    if candidate_summary.strip():
        merged["content"] = candidate_summary
        merged["candidate_summary"] = candidate_summary
    for key, value in explicit_values.items():
        if isinstance(value, str) and value.strip():
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# RC6-INNER Phase 3 — Tagebuch source provenance helpers
# ---------------------------------------------------------------------------

_TAGEBUCH_PATH_RE = re.compile(r"^Tagebuch/\d{4}-\d{2}-\d{2}\.md$")


def _validate_tagebuch_source_path(source_file: str) -> str | None:
    """Return error string if source_file is not a valid relative Tagebuch path, else None."""
    if not source_file:
        return None
    normalized = source_file.replace("\\", "/")
    if normalized.startswith("//") or (len(normalized) > 1 and normalized[1] == ":"):
        return f"source_file must be a relative path, not absolute or UNC (got: {source_file!r})."
    if ".." in normalized.split("/"):
        return f"source_file must not contain path traversal (got: {source_file!r})."
    if not _TAGEBUCH_PATH_RE.match(normalized):
        return (
            f"source_file must match 'Tagebuch/YYYY-MM-DD.md' format (got: {source_file!r}). "
            "Example: 'Tagebuch/2026-06-09.md'."
        )
    return None


def _check_tagebuch_source_provenance_args(
    source_file: str,
    source_heading: str,
    source_sha256: str,
    require_sha: bool = True,
) -> str | None:
    """Validate that the provenance fields are complete when any is provided.

    ``require_sha`` is True at apply time (the SHA is the integrity anchor) and
    False at plan time (RC7-FIX-001: the gateway computes and returns the
    canonical SHA, so the caller does not need to supply one up front).

    Returns a ``missing_source_provenance:`` error string when incomplete, else None.
    """
    if not source_file:
        return None
    path_error = _validate_tagebuch_source_path(source_file)
    if path_error:
        return f"missing_source_provenance: {path_error}"
    if not source_heading.strip():
        return (
            "missing_source_provenance: source_heading is required when source_file is provided. "
            "Provide the '## HH:MM — <title>' heading of the Tagebuch entry."
        )
    if require_sha and not source_sha256.strip():
        return (
            "missing_source_provenance: source_sha256 is required when source_file is provided. "
            "Provide the SHA-256 of the entry section text at plan time."
        )
    return None


def _extract_tagebuch_entry_section(text: str, heading: str) -> str | None:
    """Extract the Tagebuch entry section from ``heading`` to the next ``## `` heading or EOF.

    Returns the raw section text (including the heading line) or None if not found.
    """
    lines = text.splitlines(keepends=True)
    start: int | None = None
    heading_stripped = heading.strip()
    for i, line in enumerate(lines):
        if line.rstrip("\r\n") == heading_stripped:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "".join(lines[start:end])


def _check_source_integrity(
    source_file: str,
    source_heading: str,
    source_sha256: str,
    config: GatewayConfig,
) -> str | None:
    """Verify that the Tagebuch source entry is unchanged since the plan was created.

    Returns an error code string on failure (e.g. 'source_deleted_replan_required'),
    or None if the source is intact.
    """
    for root in config.allowed_roots:
        candidate = Path(root) / source_file
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            section = _extract_tagebuch_entry_section(text, source_heading)
            if section is None:
                return "source_heading_not_found"
            actual_sha256 = hashlib.sha256(section.encode("utf-8")).hexdigest()
            if actual_sha256 != source_sha256.strip():
                return "source_changed_replan_required"
            return None
    return "source_deleted_replan_required"


def _resolve_canonical_source_sha256(
    source_file: str,
    source_heading: str,
    config: GatewayConfig,
) -> tuple[str | None, str | None]:
    """Resolve the canonical SHA-256 of a Tagebuch entry section + a reason hint.

    RC8-UX-001: distinguishes *why* the canonical SHA cannot be computed instead
    of collapsing both failure modes to a bare ``None``. Returns ``(sha, None)``
    on success, ``(None, "heading_not_found")`` when the file exists but the
    section heading is missing, and ``(None, "file_not_found")`` when no allowed
    root contains the file. The reason vocabulary mirrors the apply-time
    distinctions in ``_check_source_integrity`` (``source_heading_not_found`` /
    ``source_deleted_replan_required``).

    Uses the exact same read+extract+hash path as ``_check_source_integrity``,
    so the value returned at plan time is byte-for-byte what apply will verify.
    ``read_text`` applies universal-newline translation, so the hash is computed
    over LF-normalized content regardless of on-disk line endings — what makes
    the plan->apply SHA round-trip deterministic across platforms.
    """
    for root in config.allowed_roots:
        candidate = Path(root) / source_file
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            section = _extract_tagebuch_entry_section(text, source_heading)
            if section is None:
                return None, "heading_not_found"
            return hashlib.sha256(section.encode("utf-8")).hexdigest(), None
    return None, "file_not_found"


def _compute_canonical_source_sha256(
    source_file: str,
    source_heading: str,
    config: GatewayConfig,
) -> str | None:
    """Compute the canonical SHA-256 of a Tagebuch entry section (RC7-FIX-001).

    Thin wrapper over ``_resolve_canonical_source_sha256`` for callers that only
    need the digest. Returns the hex digest, or None if the file or heading is
    not found.
    """
    sha, _reason = _resolve_canonical_source_sha256(source_file, source_heading, config)
    return sha


def _plan_source_provenance(
    source_file: str,
    source_heading: str,
    source_sha256: str,
    config: GatewayConfig,
) -> dict[str, Any]:
    """Build the source_provenance block attached to a Governor plan payload.

    RC7-FIX-001: when the source file + heading resolve, return the canonical
    SHA the gateway computes (so apply matches deterministically). Otherwise
    fall back to the caller-supplied value for backward compatibility.

    RC8-UX-001: also expose ``source_sha256_resolution`` — ``"resolved"`` when
    the canonical SHA was computed, else the reason (``"file_not_found"`` /
    ``"heading_not_found"``) so a caller can tell why the canonical SHA is
    absent instead of seeing only ``source_sha256_canonical: false``.
    """
    canonical, reason = _resolve_canonical_source_sha256(source_file, source_heading, config)
    return {
        "source_file": source_file,
        "source_heading": source_heading,
        "source_sha256": canonical or source_sha256,
        "source_sha256_canonical": canonical is not None,
        "source_sha256_resolution": "resolved" if canonical is not None else reason,
    }


def _source_provenance_failure(operation: str, error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": operation,
        "error": error,
        "error_category": "source_provenance_invalid",
        "requirement_ids": ["FR-INNER-009", "FR-INNER-010"],
    }


# ---------------------------------------------------------------------------
# end RC6-INNER Phase 3
# ---------------------------------------------------------------------------


def _profile_name_from_onboarding_answers(onboarding_answers: dict[str, Any] | None) -> str:
    if not onboarding_answers:
        return ""
    for key, value in onboarding_answers.items():
        normalized = "".join(character for character in str(key).casefold() if character.isalnum())
        if normalized in {"profilename", "name"} and value is not None:
            return str(value).strip()
    return ""


def _profile_import_target_from_answers(onboarding_answers: dict[str, Any] | None) -> str:
    if not onboarding_answers:
        return ""
    for key, value in onboarding_answers.items():
        normalized = "".join(character for character in str(key).casefold() if character.isalnum())
        if normalized in {"targetprofilename", "targetprofile", "targetname", "profilename", "name"} and value is not None:
            return str(value).strip()
    return ""


def _sandbox_adapter(config: GatewayConfig) -> DockerSandboxAdapter:
    return DockerSandboxAdapter(
        config.docker,
        workspace_roots=config.allowed_roots,
        project_root=config.project_root,
        audit_log_file=config.audit_log_file,
        protected_path_patterns=config.protected_path_patterns,
    )


def _audit(config: GatewayConfig | None, audit_logger: AuditLogger | None) -> AuditLogger:
    loaded = _load_config(config)
    return audit_logger or JsonlAuditLogger(loaded.audit_log_file)


def _audit_preflight(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    config: GatewayConfig,
    audit_logger: AuditLogger | None,
    high_risk: bool,
) -> dict[str, Any] | None:
    try:
        _audit(config, audit_logger).record(
            _audit_started_event(tool_name, arguments, high_risk=high_risk)
        )
    except Exception:
        if high_risk:
            return _fail_closed(tool_name, "Audit logging failed closed.", ("FR-008", "NFR-002"))
    return None


def _audit_public_result(
    tool_name: str,
    result: dict[str, Any],
    *,
    config: GatewayConfig | None,
    audit_logger: AuditLogger | None,
    high_risk: bool = False,
) -> dict[str, Any] | None:
    try:
        _audit(config, audit_logger).record(
            _audit_completed_event(tool_name, result, high_risk=high_risk)
        )
    except Exception:
        if high_risk:
            return _fail_closed(tool_name, "Audit logging failed closed.", ("FR-008", "NFR-002"))
    return None


def _audit_started_event(tool_name: str, arguments: dict[str, Any], *, high_risk: bool) -> dict[str, Any]:
    return {
        "event": "tool_call_started",
        "tool_name": tool_name,
        "action_type": _action_type_for(tool_name),
        "high_risk": high_risk,
        "target_category": _target_category_for(tool_name),
        "argument_keys": sorted(str(key) for key in arguments),
        "redaction": "arguments_metadata_only",
    }


def _audit_completed_event(tool_name: str, result: dict[str, Any], *, high_risk: bool) -> dict[str, Any]:
    return {
        "event": "tool_call_completed",
        "tool_name": tool_name,
        "action_type": _action_type_for(tool_name),
        "high_risk": high_risk,
        "target_category": _target_category_for(tool_name),
        "result_status": _result_status(result),
        "policy_decision": _policy_decision_value(result.get("policy_decision")),
        "requirement_ids": list(result.get("requirement_ids") or ()),
        "error_category": result.get("error_category") or _error_category(result.get("error")),
        "result_metrics": _result_metrics(result),
        "redaction": "result_metadata_only",
    }


def _action_type_for(tool_name: str) -> str:
    if tool_name in {"plwc_write_workspace_file", "plwc_write_reflection", "plwc_governor_apply", REFLECTION_TOOL}:
        return "write"
    if tool_name in {"plwc_run_python_sandboxed", "plwc_run_shell_sandboxed", SANDBOX_RUN_TOOL}:
        return "sandbox_execution"
    if tool_name == WORKSPACE_OPERATION_TOOL:
        return "workspace_operation"
    if tool_name == DOCUMENT_OPERATION_TOOL:
        return "document_operation"
    if tool_name == DESCRIBE_TOOL:
        return "describe"
    if tool_name in {"plwc_read_workspace_file", "plwc_list_workspace", "plwc_search_workspace"}:
        return "workspace_read"
    if "profile" in tool_name or "governor" in tool_name:
        return "profile_operation"
    if tool_name.endswith("_status") or tool_name == PUBLIC_STATUS_TOOL:
        return "status"
    return "gateway_operation"


def _target_category_for(tool_name: str) -> str:
    if "workspace" in tool_name:
        return "workspace"
    if tool_name == DOCUMENT_OPERATION_TOOL:
        return "document"
    if "reflection" in tool_name or "profile" in tool_name or "governor" in tool_name:
        return "profile"
    if "sandbox" in tool_name:
        return "sandbox"
    if "claude_config" in tool_name:
        return "client_config"
    return "gateway"


def _result_status(result: dict[str, Any]) -> str:
    ok = result.get("ok")
    if ok is True:
        return "success"
    if ok is False:
        return "failure"
    return "unknown"


def _policy_decision_value(value: Any) -> str | None:
    if isinstance(value, PolicyDecision):
        return value.value
    if value is None:
        return None
    return str(value)


def _error_category(error: Any) -> str | None:
    if error is None:
        return None
    text = str(error).casefold()
    if "unsupported" in text or "not supported" in text:
        return "unsupported_operation"
    if "replacement" in text and "expected" in text and "found" in text:
        return "unexpected_replacement_count"
    if "at most" in text or "exceeds" in text or "limit" in text:
        return "limit_exceeded"
    if "required" in text or "must be" in text:
        return "validation_error"
    if "permission" in text or "access denied" in text:
        return "permission_error"
    if "not found" in text or "no such file" in text or "missing" in text:
        return "not_found"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "audit" in text:
        return "audit_error"
    if "docker" in text or "safe mode" in text:
        return "sandbox_unavailable"
    if "policy" in text or "denied" in text or "forbidden" in text or "protected" in text:
        return "policy_denied"
    return "adapter_error"


def _result_metrics(result: dict[str, Any]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    if "bytes_written" in result and result["bytes_written"] is not None:
        metrics["bytes_written"] = int(result["bytes_written"])
    if "file_size" in result and result["file_size"] is not None:
        metrics["document_bytes"] = int(result["file_size"])
    if "byte_count" in result and result["byte_count"] is not None:
        metrics["byte_count"] = int(result["byte_count"])
    if "replacements" in result and result["replacements"] is not None:
        metrics["replacements"] = int(result["replacements"])
    if isinstance(result.get("entries"), (list, tuple)):
        metrics["entry_count"] = len(result["entries"])
    if isinstance(result.get("matches"), (list, tuple)):
        metrics["match_count"] = len(result["matches"])
    if isinstance(result.get("files"), (list, tuple)):
        metrics["batch_item_count"] = len(result["files"])
    if isinstance(result.get("changed_files"), (list, tuple)):
        metrics["changed_count"] = len(result["changed_files"])
    if isinstance(result.get("read_files"), (list, tuple)):
        metrics["read_count"] = len(result["read_files"])
    if isinstance(result.get("content"), str):
        metrics["content_chars"] = len(result["content"])
    if isinstance(result.get("stdout"), str):
        metrics["stdout_chars"] = len(result["stdout"])
    if isinstance(result.get("stderr"), str):
        metrics["stderr_chars"] = len(result["stderr"])
    return metrics


def _default_compile_max_chars(compile_mode: str) -> int:
    if compile_mode == "working":
        return DEFAULT_WORKING_COMPILE_MAX_CHARS
    return DEFAULT_BOOT_COMPILE_MAX_CHARS


def _normalize_compile_max_chars(value: Any, compile_mode: str) -> int | None:
    if compile_mode == "full":
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed == 0:
        return _default_compile_max_chars(compile_mode)
    if parsed < MIN_COMPACT_COMPILE_MAX_CHARS or parsed > MAX_COMPACT_COMPILE_MAX_CHARS:
        return None
    return parsed


def _normalize_persona_layer_enabled(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    normalized = _normalize_dispatch_value(str(value))
    if normalized in {"", "default", "enabled", "enable", "on", "true", "yes", "include", "included"}:
        return True
    if normalized in {"disabled", "disable", "off", "false", "no", "omit", "omitted", "without_persona"}:
        return False
    return None


def _apply_profile_compile_mode(
    payload: dict[str, Any],
    *,
    compile_mode: str,
    compile_max_chars: int,
    semantic_memory: dict[str, Any] | None = None,
    persona_layer_enabled: bool = True,
    persona_layer_source: str = "default",
) -> None:
    data = payload.get("data")
    if not isinstance(data, dict):
        return
    full_layer = data.get("compiled_layer")
    if not isinstance(full_layer, str):
        return

    source_layer_chars = len(full_layer)
    persona_omission = None
    if not persona_layer_enabled:
        full_layer, persona_omission = _omit_compiled_persona_layer(full_layer)
        data["compiled_layer"] = full_layer
    full_chars = len(full_layer)
    data["compile_mode"] = compile_mode
    if source_layer_chars != full_chars:
        data["source_compiled_layer_chars"] = source_layer_chars
    data["full_compiled_layer_chars"] = full_chars
    data["compile_max_chars"] = compile_max_chars if compile_mode != "full" else None
    data["persona_layer"] = _compile_persona_layer_metadata(
        enabled=persona_layer_enabled,
        source=persona_layer_source,
        omitted=persona_omission,
    )
    requirement_ids = payload.setdefault("requirement_ids", [])
    if not isinstance(requirement_ids, list):
        if isinstance(requirement_ids, tuple):
            requirement_ids = list(requirement_ids)
        else:
            requirement_ids = []
        payload["requirement_ids"] = requirement_ids
    for requirement_id in PROFILE_COMPILE_MODE_REQUIREMENTS:
        if requirement_id not in requirement_ids:
            requirement_ids.append(requirement_id)
    if V1_PERSONA_LAYER_REQUIREMENT_ID not in requirement_ids:
        requirement_ids.append(V1_PERSONA_LAYER_REQUIREMENT_ID)
    if semantic_memory is not None and RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID not in requirement_ids:
        requirement_ids.append(RC14_QDRANT_LOAD_BEARING_REQUIREMENT_ID)
    semantic_memory_metadata = None
    semantic_memory_block = ""
    if isinstance(semantic_memory, dict):
        raw_metadata = semantic_memory.get("metadata")
        if isinstance(raw_metadata, dict):
            semantic_memory_metadata = dict(raw_metadata)
            data["semantic_memory"] = semantic_memory_metadata
        semantic_memory_block = str(semantic_memory.get("block") or "").strip()
    if compile_mode == "full":
        data["compiled_layer_chars"] = full_chars
        data["compile_compaction"] = {"mode": "full", "applied": False}
        return

    compact_layer, metadata = _compact_compiled_layer(
        full_layer,
        mode=compile_mode,
        max_chars=compile_max_chars,
        semantic_memory_block=semantic_memory_block,
        persona_layer_enabled=persona_layer_enabled,
    )
    if semantic_memory_metadata is not None:
        metadata["semantic_memory"] = semantic_memory_metadata
    data["compiled_layer"] = compact_layer
    data["compiled_layer_chars"] = len(compact_layer)
    data["compile_compaction"] = metadata


def _compile_persona_layer_metadata(
    *,
    enabled: bool,
    source: str,
    omitted: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "requirement_id": V1_PERSONA_LAYER_REQUIREMENT_ID,
        "enabled": enabled,
        "source": source,
        "extension_config_key": "persona_layer_disabled",
        "env_var": PERSONA_LAYER_DISABLED_ENV_VAR,
        "extension_config_default": False,
        "disable_value": True,
        "legacy_extension_config_key": "persona_layer_enabled",
        "legacy_env_var": PERSONA_LAYER_ENABLED_ENV_VAR,
        "omitted": not enabled,
        "omitted_section": "PERSONA" if not enabled else None,
        "omitted_line_count": int((omitted or {}).get("omitted_line_count", 0)),
        "omitted_core_persona_line_count": int((omitted or {}).get("omitted_core_persona_line_count", 0)),
        "core_persona_labels_omitted": list((omitted or {}).get("core_persona_labels_omitted", [])),
        "profile_files_mutated": False,
        "public_tool_expansion": False,
        "hard_gates_preserved": True,
        "governance_preserved": True,
    }


def _omit_compiled_persona_layer(compiled_layer: str) -> tuple[str, dict[str, Any]]:
    labels = {"CORE", "TEMPERAMENT", "PERSONA", "MEMORY", "TASK CONTEXT"}
    output: list[str] = []
    skipping = False
    current_label = ""
    omitted_line_count = 0
    omitted_core_persona_line_count = 0
    core_persona_labels_omitted: set[str] = set()
    for line in compiled_layer.splitlines():
        stripped = line.strip()
        is_section_header = stripped.endswith(":") and stripped[:-1] in labels
        if is_section_header:
            label = stripped[:-1]
            current_label = label
            if label == "PERSONA":
                skipping = True
                omitted_line_count += 1
                continue
            skipping = False
        if skipping:
            omitted_line_count += 1
            continue
        if current_label == "CORE":
            core_persona_label = _persona_layer_core_omit_label(line)
            if core_persona_label:
                omitted_line_count += 1
                omitted_core_persona_line_count += 1
                core_persona_labels_omitted.add(core_persona_label)
                continue
        output.append(line)
    return "\n".join(output).strip(), {
        "omitted_line_count": omitted_line_count,
        "omitted_core_persona_line_count": omitted_core_persona_line_count,
        "core_persona_labels_omitted": sorted(core_persona_labels_omitted),
    }


def _persona_layer_core_omit_label(line: str) -> str | None:
    match = PERSONA_LAYER_CORE_OMIT_RE.match(line)
    if not match:
        return None
    return match.group("label").casefold()


def _compact_compiled_layer(
    full_layer: str,
    *,
    mode: str,
    max_chars: int,
    semantic_memory_block: str = "",
    persona_layer_enabled: bool = True,
) -> tuple[str, dict[str, Any]]:
    blocks = _split_compiled_layer_blocks(full_layer)
    task_terms = _compile_terms(blocks.get("TASK CONTEXT", ""))
    section_metadata: dict[str, Any] = {}
    compact = ""
    entry_char_limit = _entry_max_chars_for_mode(mode)
    hard_truncated = False

    candidate_limits = _entry_char_candidates(mode)
    for candidate_limit in candidate_limits:
        entry_char_limit = candidate_limit
        compact, section_metadata = _build_compact_compiled_layer(
            blocks,
            mode=mode,
            task_terms=task_terms,
            entry_char_limit=entry_char_limit,
            semantic_memory_block=semantic_memory_block,
            persona_layer_enabled=persona_layer_enabled,
        )
        if len(compact) <= max_chars:
            break
    else:
        notice = "\n\n[compact layer truncated at configured character budget]"
        compact = compact[: max(0, max_chars - len(notice))].rstrip() + notice
        hard_truncated = True

    return compact, {
        "mode": mode,
        "applied": True,
        "max_chars": max_chars,
        "entry_max_chars": entry_char_limit,
        "hard_truncated": hard_truncated,
        "sections": section_metadata,
    }


def _split_compiled_layer_blocks(compiled_layer: str) -> dict[str, str]:
    labels = {"CORE", "TEMPERAMENT", "PERSONA", "MEMORY", "TASK CONTEXT"}
    blocks: dict[str, list[str]] = {"_prefix": []}
    current = "_prefix"
    for line in compiled_layer.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in labels:
            current = stripped[:-1]
            blocks.setdefault(current, [])
            continue
        blocks.setdefault(current, []).append(line)
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def _build_compact_compiled_layer(
    blocks: dict[str, str],
    *,
    mode: str,
    task_terms: set[str],
    entry_char_limit: int,
    semantic_memory_block: str = "",
    persona_layer_enabled: bool = True,
) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    prefix = blocks.get("_prefix", "").strip()
    if prefix:
        parts.append(prefix)
    parts.extend(
        [
            "",
            f"Compile mode: {mode} public facade",
            "Canonical profile files remain unchanged. Use profile retrieve/snapshot/governor review for omitted detail.",
        ]
    )

    metadata: dict[str, Any] = {}
    parts.extend(["", "CORE:", blocks.get("CORE", "").strip()])
    for label, filename in (("TEMPERAMENT", "TEMPERAMENT.md"), ("PERSONA", "PERSONA.md"), ("MEMORY", "memory.md")):
        if label == "PERSONA" and not persona_layer_enabled:
            metadata[filename] = {
                "active_entries": 0,
                "included_entries": 0,
                "omitted_entries": 0,
                "selection": "persona_layer_disabled",
            }
            continue
        compact_text, section_meta = _compact_lifecycle_block(
            blocks.get(label, ""),
            mode=mode,
            filename=filename,
            task_terms=task_terms,
            entry_char_limit=entry_char_limit,
        )
        metadata[filename] = section_meta
        parts.extend(["", f"{label}:", compact_text])
    if semantic_memory_block.strip():
        parts.extend(["", semantic_memory_block.strip()])
    parts.extend(["", "TASK CONTEXT:", blocks.get("TASK CONTEXT", "").strip()])
    return "\n".join(parts), metadata


def _compact_lifecycle_block(
    text: str,
    *,
    mode: str,
    filename: str,
    task_terms: set[str],
    entry_char_limit: int,
) -> tuple[str, dict[str, Any]]:
    entries = [entry for entry in pba._parse_profile_entries(text) if entry.get("status") == "ACTIVE"]
    if not entries:
        compact = _truncate_text(" ".join(text.split()), entry_char_limit * 2)
        return compact, {
            "active_entries": 0,
            "included_entries": 0,
            "omitted_entries": 0,
            "selection": "fallback_text",
        }

    limit = _entry_limit_for_mode(mode, filename)
    selected_indexes = _select_compact_entry_indexes(
        entries,
        mode=mode,
        limit=limit,
        task_terms=task_terms,
    )
    lines: list[str] = []
    for index in selected_indexes:
        entry = entries[index]
        lines.append(str(entry["heading"]))
        lines.append(_compact_entry_body(str(entry.get("body", "")), entry_char_limit))
        lines.append("")
    omitted = max(0, len(entries) - len(selected_indexes))
    if omitted:
        lines.append(f"[{omitted} active entries omitted from compact compile; canonical file unchanged.]")
    return "\n".join(lines).strip(), {
        "active_entries": len(entries),
        "included_entries": len(selected_indexes),
        "omitted_entries": omitted,
        "selection": "first_relevant_recent" if mode == "working" else "boot_anchors_recent",
    }


def _entry_limit_for_mode(mode: str, filename: str) -> int:
    if mode == "working":
        return WORKING_PROFILE_ENTRY_LIMITS.get(filename, 8)
    return BOOT_PROFILE_ENTRY_LIMITS.get(filename, 3)


def _entry_max_chars_for_mode(mode: str) -> int:
    if mode == "working":
        return WORKING_PROFILE_ENTRY_MAX_CHARS
    return BOOT_PROFILE_ENTRY_MAX_CHARS


def _entry_char_candidates(mode: str) -> tuple[int, ...]:
    if mode == "working":
        return (WORKING_PROFILE_ENTRY_MAX_CHARS, 260, 180, 120)
    return (BOOT_PROFILE_ENTRY_MAX_CHARS, 160, 120, 90)


def _select_compact_entry_indexes(
    entries: list[dict[str, Any]],
    *,
    mode: str,
    limit: int,
    task_terms: set[str],
) -> list[int]:
    if len(entries) <= limit:
        return list(range(len(entries)))

    anchor_count = min(3 if mode == "working" else 2, limit)
    selected: set[int] = set(range(anchor_count))
    if mode == "working" and task_terms:
        scored: list[tuple[int, int]] = []
        for index, entry in enumerate(entries):
            text = f"{entry.get('heading', '')} {entry.get('body', '')}"
            score = len(task_terms & _compile_terms(text))
            if score > 0:
                scored.append((score, index))
        for _score, index in sorted(scored, key=lambda item: (-item[0], -item[1])):
            if len(selected) >= limit:
                break
            selected.add(index)

    index = len(entries) - 1
    while len(selected) < limit and index >= 0:
        selected.add(index)
        index -= 1
    return sorted(selected)


def _compact_entry_body(body: str, max_chars: int) -> str:
    body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    content_lines = [line for line in body_lines if line.casefold().startswith("inhalt:")]
    if not content_lines:
        content_lines = body_lines[:1]
    if not content_lines:
        return "(empty entry)"
    return _truncate_text(" ".join(content_lines), max_chars)


def _compile_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w-]{4,}", text.casefold())
        if token not in {"inhalt", "belegt", "durch", "verhaltensrelevanz", "kandidat", "fuer"}
    }


def _truncate_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 3)].rstrip() + "..."


def _public_payload(result: Any) -> dict[str, Any]:
    if is_dataclass(result) and hasattr(result, "as_dict"):
        payload = result.as_dict()
    elif is_dataclass(result):
        payload = asdict(result)
    elif isinstance(result, dict):
        payload = dict(result)
    else:
        payload = {"ok": False, "error": str(result)}

    if isinstance(payload.get("policy_decision"), PolicyDecision):
        payload["policy_decision"] = payload["policy_decision"].value
    return payload


def _fail_closed(tool_name: str, reason: str, requirement_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": tool_name,
        "policy_decision": PolicyDecision.DENY.value,
        "error": reason,
        "requirement_ids": list(requirement_ids),
    }


if __name__ == "__main__":
    main()
