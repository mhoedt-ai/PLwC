# Tools

## Public Tool Rule

PLwC may expose public tools only through:

```text
plwc-gateway
```

No Source A or Source B MCP server is public under its original name.

## Classification States

- `KEEP_PUBLIC`: expose as a PLwC public capability through `plwc-gateway`.
- `KEEP_INTERNAL`: keep as internal library logic, fixture, reference or test
  pattern only.
- `WRAP_WITH_POLICY`: keep behavior, but only after PLwC policy approval and
  audit logging.
- `REPLACE_WITH_GOVERNED_TOOL`: implement a PLwC-native governed tool instead
  of exposing the raw source tool.
- `REMOVE_UNSAFE`: do not expose or preserve as runtime behavior in PLwC.

## PLwC Public Tool Candidates

For `0.2.0-dev`, the public boundary is an eight-tool facade. This is a
public-surface refactor, not feature expansion. The previous 19 public tool
names remain historical `0.1.0` evidence and internal handler references only;
they are no longer exposed as public MCP tools on this branch. All prior
behavior remains reachable through the facade dispatch parameters below.

The controlled `0.2.0-dev` MCPB package smoke on 2026-05-21 confirmed the
same boundary in the installable artifact: one public server,
`plwc-gateway`, exactly these eight public tools, and no old individual public
tool names in the manifest or extracted FastMCP registry. The stabilized
package smoke also confirmed PPTX Creation V2, PDF Creation V2, `create_pptx`, ODT/ODS/ODP inspect/extract,
configured active profile precedence, reflection supporting evidence,
duplicate no-op, cross-profile reflection denial and DOCX Creation V2 JSON
`input_path`, image, long-form, strict-validation and legacy compatibility
behavior through the facade tools. The current package smoke also confirmed
XLSX Creation V2 JSON `input_path`, multi-sheet workbooks, formatting, sheet
structure controls, safe formula policy, large-workbook support, strict
negative contract cases, legacy compatibility and `read_image`
PNG/JPEG/WEBP/GIF reads, resize behavior, ImageContent transfer and negative
format/path/limit cases.

The latest PBA2/Governor package smoke for artifact SHA256
`e28baa065d5f04dad534742c13ee52ea16613ec881ed4617837a6aac2b58bfd1`
also confirmed reusable reflection insight acceptance, supporting-evidence
classification, exact duplicate no-op, modal-only technical-noise rejection,
cross-profile reflection denial, explicit persona promotion,
`reflection_condensation` apply by runtime `plan_id`, full `approved_plan`
backward compatibility, pending-plan storage outside workspace/profile roots
and protected-boundary denials. These remain under the existing
`plwc_reflection` and `plwc_governor` facade tools.

A real project-asset smoke with `Atlantis_Roman/Cover.png` confirmed the same
behavior on a realistic cover image: the approximately `3.37 MB` source image
exceeded the default `2048 KB` transfer limit, `resize_to="50%"` succeeded, the
gateway returned a `512x768 px` ImageContent payload of approximately `754 KB`,
and the JSON text block did not include raw `image_data`.

Sora-session XLSX V2 smoke on 2026-05-21 confirmed legacy creation, JSON
`input_path`, a two-sheet data/summary workbook, freeze panes, boolean
`auto_filter`, column widths, cross-sheet formulas, `14` extracted cells,
`4` extracted formulas and unsafe `HYPERLINK` / external URL formula rejection.

These are target PLwC capabilities, not source server names:

| PLwC tool | Classification | Source influence |
| --- | --- | --- |
| `plwc_status` | `KEEP_PUBLIC` | Facade for runtime, sandbox, first-run onboarding and Claude Desktop config status through `scope=runtime\|sandbox\|first_run\|config` |
| `plwc_describe` | `KEEP_PUBLIC` | Read-only schema/help metadata for public facades, onboarding payload keys, operation names, required fields and common denial reasons |
| `plwc_profile` | `KEEP_PUBLIC` | Facade for PBA profile status, snapshot, retrieval, Tagebuch scan and compile through `operation=status\|snapshot\|retrieve\|scan_tagebuch\|compile`; compile defaults to bounded `compile_mode=boot`, supports `working` with `task_context`, and keeps `full` for audit/diagnosis |
| `plwc_reflection` | `KEEP_PUBLIC` | Facade for governed PBA reflection writes through `operation=write`; optional `target="memory.md"` metadata marks entries for `reflection_memory_promotion`; when target is used, `candidate_for` must also be `memory.md` |
| `plwc_governor` | `KEEP_PUBLIC` | Facade for PBA Governor plan/apply through `operation=plan\|apply`; `plan_type=profile_creation` creates first/onboarding profile plans; mutation-bearing applies require `confirmed=true` |
| `plwc_sandbox_run` | `KEEP_PUBLIC` | Facade for Docker-only Python/shell sandbox execution through `lang=python\|shell`; no host-shell fallback |
| `plwc_workspace_operation` | `KEEP_PUBLIC` | Bundled governed workspace operations: list, search, read, write, file info, create directory, move/rename, batch read and exact replace; no delete or raw Commander passthrough |
| `plwc_document_operation` | `KEEP_PUBLIC` | Bundled governed Document Worker operations: DOCX Creation V2, XLSX Creation V2, existing PPTX/PDF creation, PDF inspect/merge/split/extract/rotate/text extraction, workspace raster image reads, ZIP inspect/extract/create and Office/OpenDocument inspect/extract; no conversion, non-ZIP archives, encrypted/password ZIPs, delete, OCR, macro execution, formula execution, signing, redaction or raw worker passthrough |

### 0.2.0-dev Facade Contract Notes

- `plwc_workspace_operation(operation="list")` requires `path`; use `"."` for
  the workspace root.
- `plwc_workspace_operation(operation="exact_replace")` requires
  `expected_replacements`.
- `move` and `rename` use `source_path` and `target_path`; `delete` is not
  supported by design.
- `plwc_document_operation(operation="create_docx")` now provides DOCX
  Creation V2. It accepts either legacy inline `content.title`,
  `content.paragraphs` and optional `content.table`, or a V2 JSON document
  specification through inline `content` or workspace `input_path`.
- DOCX V2 `input_path` must be a workspace-relative `.json` file. Absolute
  paths, parent traversal, protected profile/governance paths and unsupported
  extensions are rejected. Supplying both inline `content` and `input_path` is
  rejected as ambiguous.
- DOCX V2 JSON supports optional `schema_version` with default
  `docx_v2_1`; unknown future schema versions fail closed with
  `validation_error`.
- DOCX V2 JSON supports `document` metadata, A4/A5 page setup, portrait or
  landscape orientation, millimeter margins, body/title/heading1/heading2/
  heading3 styles, paragraph style overrides, title/heading/paragraph/quote/
  page-break elements, mixed paragraph `runs`, `bullet_list` and
  `numbered_list`, PNG/JPEG images from safe workspace paths and basic tables.
- Paragraph elements may use either `text` or `runs`. Using both is rejected.
  Run objects support `text`, `bold`, `italic` and `underline`; unknown run
  fields are rejected.
- List elements support flat `items` only. Nested lists are not implemented in
  this slice and malformed or empty list items are rejected.
- DOCX V2 is a practical layout builder, not full desktop publishing. It does
  not use LibreOffice/Pandoc, does not guarantee exact print typography, does
  not embed fonts, does not implement CUSTOM page sizes and does not accept
  Markdown/plain-text/HTML/template DOCX as `input_path` in this slice.
- `plwc_document_operation(operation="edit_docx")` provides a governed,
  declarative editor for an existing workspace `.docx`. It reads `input_path`
  and writes a new `output_path` (read-A→write-B); both must be
  workspace-relative `.docx`, `output_path` must not already exist and
  `overwrite=true` is denied. In-place editing is a v2 non-goal.
- `edit_docx` `content` is `{ "schema_version": "edit_docx_1", "edits": [...] }`
  with a non-empty `edits` list (max 200 ops). The five v1 edit types are
  `replace_text` (literal find/replace across body and table paragraphs, with
  optional `max_replacements`), `set_core_property` (`title`/`author`/`subject`/
  `keywords`), `append_paragraph` (text plus optional allowed style),
  `set_footer_text` and `set_header_text` (text plus optional centered `PAGE`
  field). Unknown fields, unknown edit types and unknown schema versions are
  rejected.
- `edit_docx` accepts no raw XML/HTML/formula/active-content strings in edit
  values, rejects `.docm` macro-enabled inputs, parses document XML only with
  `defusedxml` and never executes or preserves macros. It is a new `operation`
  under the existing facade, not a new public tool, and adds no conversion,
  OCR, signing, redaction, forms or delete behavior.
- `plwc_document_operation(operation="create_xlsx")` now provides XLSX
  Creation V2. It accepts either legacy inline `content.sheet_name` and
  `content.rows`, or a V2 JSON workbook specification through inline `content`
  or workspace `input_path`.
- XLSX V2 `input_path` must be a workspace-relative `.json` file. Absolute
  paths, parent traversal, protected profile/governance paths and unsupported
  extensions are rejected. Supplying both inline `content` and `input_path` is
  rejected as ambiguous.
- XLSX V2 JSON supports optional `schema_version` with default `xlsx_v2_1`;
  unknown future schema versions fail closed with `validation_error`.
- XLSX V2 JSON supports workbook metadata, multiple unique sheets, scalar and
  structured cell objects, cell formatting, freeze panes, auto filter, column
  widths, row heights and bounded merged cell ranges.
- XLSX V2 `auto_filter` is boolean only. `auto_filter=true` applies a filter
  to the used data range / first row, and `auto_filter=false` leaves the sheet
  unfiltered. Range-string values such as `"A1:C10"` are rejected with
  `validation_error`; future range support should use a separate explicit
  field such as `auto_filter_range`.
- XLSX V2 formula policy is explicit and conservative: plain value strings
  beginning with `=` are stored as literal text, formulas are written only from
  explicit `formula` fields, and PLwC never executes or verifies formulas.
  External workbook references, URLs, external data functions and macro-like
  formula patterns are rejected.
- XLSX V2 is a workbook builder, not a calculation engine. It does not use
  LibreOffice/Pandoc, does not execute macros, does not fetch external links
  and does not accept CSV/template workbook `input_path` in this slice.
- `plwc_document_operation(operation="create_pdf")` now provides PDF
  Creation V2. It accepts either legacy inline `content.title` /
  `content.lines`, or a V2 JSON document specification through inline
  `content` or workspace `input_path`.
- PDF V2 `input_path` must be a workspace-relative `.json` file. Absolute
  paths, parent traversal, protected profile/governance paths and
  unsupported extensions are rejected. Supplying both inline `content` and
  `input_path` is rejected as ambiguous.
- PDF V2 JSON supports optional `schema_version` with default `pdf_v2_1`;
  unknown future schema versions fail closed with `validation_error`.
- PDF V2 JSON supports document metadata (title, author, language), A4 and
  A5 page sizes (plus an optional custom `{name, width_mm, height_mm}`
  size), portrait and landscape orientation, millimeter margins,
  body/title/heading1..3/quote styles, paragraph runs
  (bold/italic/underline), `bullet_list` and `numbered_list`, basic tables
  with optional `header_row`, workspace-only PNG/JPEG images with
  align/width_mm/height_mm and explicit `page_break`.
- PDF V2 images and image content elements only accept workspace-relative
  `.png`, `.jpg` or `.jpeg` paths. External URLs, UNC paths, absolute
  paths, parent traversal, profile/governance paths, oversized files and
  other formats are rejected with structured error categories.
- PDF V2 text fields accept arbitrary user text. Strings beginning with
  `=`, containing `<script>` or `<?xml` substrings are stored verbatim and
  never interpreted, rendered or executed by PLwC.
- PDF V2 is a layout-PDF builder, not a PDF editor and not a renderer of
  arbitrary HTML/CSS. It does not implement OCR, redaction, digital
  signing, form filling, form creation, PDF/A, LibreOffice/Pandoc
  conversion, JavaScript in PDFs, attachments/embedded files, external
  URL fetching or network access.
- `plwc_document_operation(operation="create_pptx")` now provides PPTX
  Creation V2. It accepts either legacy inline `content.title` /
  `content.slides[{title, bullets[string]}]` (also via top-level `title` /
  `slides` shorthand), or a V2 JSON presentation specification through inline
  `content` or workspace `input_path`.
- PPTX V2 `input_path` must be a workspace-relative `.json` file. Absolute
  paths, parent traversal, protected profile/governance paths and unsupported
  extensions are rejected. Supplying both inline `content` and `input_path` is
  rejected as ambiguous.
- PPTX V2 JSON supports optional `schema_version` with default `pptx_v2_1`;
  unknown future schema versions fail closed with `validation_error`.
- PPTX V2 JSON supports presentation metadata (title, author, slide_size),
  five slide layouts (`title`, `content`, `section_header`, `image`, `blank`),
  five content element types (`bullets`, `paragraph`, `table`, `image`,
  `text_box`), bullet levels 0–3 with bold/italic/font_size/color
  formatting, plain-text speaker notes per slide, and the slide sizes
  `16:9`, `4:3`, `A4_portrait` and custom (`width_mm`/`height_mm` between
  100 and 1200 mm).
- PPTX V2 image elements and image slides only accept workspace-relative
  `.png`, `.jpg` or `.jpeg` paths. External URLs, UNC paths, absolute paths,
  parent traversal, profile/governance paths, oversized files and other
  formats are rejected with structured error categories.
- PPTX V2 slide text fields (`title`, `subtitle`, `body`, `paragraph`,
  `bullets`, `table` cells, `text_box`, `notes`) accept arbitrary user text.
  Strings beginning with `=`, containing `<script>` or `<?xml` substrings are
  stored verbatim and never interpreted, rendered or executed by PLwC.
- PPTX V2 speaker notes are written to the PPTX notes layer and can be
  read back via `extract_pptx_text(include_notes=true)`. With
  `include_notes` omitted or `false`, the extractor preserves the existing
  body-only behavior.
- PPTX V2 is a layout-capable builder, not a rendering or automation
  system. It does not implement animations, transitions, font embedding,
  PowerPoint VBA/macros, OLE embeddings, external relationships,
  LibreOffice/Pandoc conversion or PDF Creation V2.
- `plwc_document_operation(operation="create_zip")` requires `output_path` plus
  `input_path` or `input_paths`; `content` is not used.
- `plwc_document_operation(operation="read_image")` reads workspace-relative
  raster images and returns image metadata in the text result plus an MCP image
  content block for Claude vision input. The operation supports PNG, JPG/JPEG,
  WEBP and GIF input; GIF reads only the first frame. BMP, SVG and TIFF are
  rejected.
- `read_image` accepts `input_path`, optional `max_size_kb`, optional
  `resize_to` and optional `format`. The default transfer limit is 2048 KB and
  the hard limit is 5120 KB. `resize_to` accepts `WIDTHxHEIGHT` fit-box syntax
  or `N%` proportional scaling. Output `format` may be `png`, `jpeg` or `webp`;
  omitted format defaults to PNG.
- `read_image` never returns base64 image bytes in the text block delivered to
  Claude Desktop. The gateway strips `image_data` from the JSON text part and
  emits a separate MCP image content block with the declared media type.
- Larger images are not accepted by default merely because they are under the
  hard limit. The default `2048 KB` limit is enforced; callers can explicitly
  request `resize_to` when a larger workspace image needs a smaller transfer
  payload within the hard `5120 KB` limit.
- `read_image` input paths must stay inside the workspace. External URLs,
  absolute paths, parent traversal and profile/governance paths are rejected.
- Creation `input_path` support is available for DOCX V2, XLSX V2,
  PPTX V2 and PDF V2 JSON specifications.
- `plwc_reflection(operation="write")` writes only to the resolved active
  profile. Similar reusable insights can be accepted as supporting evidence;
  exact duplicate content/evidence/date may return `duplicate_noop`. Reflection
  write does not apply memory/persona promotion thresholds. If `profile` is
  provided and does not match the resolved active profile, the write is denied
  without mutating `reflection.md`.
- `plwc_reflection(operation="write")` is English-first for public input:
  recommended marker values are `observation`, `hypothesis`, `wish`, `concern`,
  `pattern` and `inner_perspective`; recommended trust values are `low`,
  `medium` and `high`. Additional aliases such as `worry`, `risk`,
  `recurring_pattern`, `behavior pattern`, `inner-perspective`, `weak`,
  `moderate` and `strong` are accepted. Stored entries remain canonical PBA2
  values such as `Beobachtung`, `Muster`, `mittel` and `hoch`.
- `plwc_governor(operation="plan", plan_type="reflection_condensation")`
  returns a stable `plan_id` and stores the approved plan snapshot under
  governed runtime state (`state/pending_plans`), outside workspace roots and
  outside profile roots. `plwc_governor(operation="apply",
  plan_type="reflection_condensation", plan_id="...", confirmed=true)` applies
  that stored plan after hash validation. The older
  `onboarding_answers.approved_plan` apply payload remains supported.
- `reflection_condensation` `plan_id` apply does not bypass confirmation or
  protected profile/governance boundaries. Unknown, malformed, cross-profile or
  tampered pending plans fail closed; repeat apply after successful consumption
  returns an already-processed/duplicate no-op without a second profile
  mutation.

## 0.2.0-dev Legacy Public Tool Mapping

| Previous public tool | 0.2.0-dev facade mapping |
| --- | --- |
| `plwc_runtime_status` | `plwc_status(scope="runtime")` |
| `plwc_sandbox_status` | `plwc_status(scope="sandbox")` |
| `plwc_first_run_status` | `plwc_status(scope="first_run")` |
| `plwc_generate_claude_config` | `plwc_status(scope="config")` |
| `plwc_profile_status` | `plwc_profile(operation="status")` |
| `plwc_profile_snapshot` | `plwc_profile(operation="snapshot")` |
| `plwc_compile_profile` | `plwc_profile(operation="compile")` |
| `plwc_write_reflection` | `plwc_reflection(operation="write")` |
| `plwc_governor_plan` | `plwc_governor(operation="plan")` |
| `plwc_governor_apply` | `plwc_governor(operation="apply")` |
| `plwc_run_python_sandboxed` | `plwc_sandbox_run(lang="python")` |
| `plwc_run_shell_sandboxed` | `plwc_sandbox_run(lang="shell")` |
| `plwc_list_workspace` | `plwc_workspace_operation(operation="list")` |
| `plwc_search_workspace` | `plwc_workspace_operation(operation="search")` |
| `plwc_read_workspace_file` | `plwc_workspace_operation(operation="read")` |
| `plwc_write_workspace_file` | `plwc_workspace_operation(operation="write")` |

## Source A MCP Entry Points

| Entry point | Observed behavior | Classification | PLwC decision |
| --- | --- | --- | --- |
| `src/pba_adapters/mcp/server.py` | FastMCP server named `plfc` | `REMOVE_UNSAFE` | Do not expose or start |
| `src/pba_adapters/mcp/http_server.py` | Streamable HTTP MCP app with optional token auth | `REMOVE_UNSAFE` | Do not expose; no PBA HTTP endpoint |
| `src/pba_adapters/mcp/manifest.json` | MCPB manifest for `plfc` | `REMOVE_UNSAFE` | Do not package |
| `examples/mcp/*.json` | Client configs for PBA MCP | `REMOVE_UNSAFE` | Do not reuse as active config |
| `start_pba_http.bat` | Starts PBA HTTP server | `REMOVE_UNSAFE` | Do not migrate |
| `PLfC-0.1.0.mcpb` | Source bundle artifact | `REMOVE_UNSAFE` | Do not import into PLwC |

## Source A Tool Mapping

| Source tool | Source module | Classification | PLwC mapping |
| --- | --- | --- | --- |
| `pba_snapshot` | `pba_adapters.mcp.server` | `WRAP_WITH_POLICY` | `plwc_profile(operation="snapshot")` |
| `pba_compile` | `pba_adapters.mcp.server` | `WRAP_WITH_POLICY` | `plwc_profile(operation="compile")` |
| `pba_write_reflection` | `pba_adapters.mcp.server` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_reflection(operation="write")` |
| `pba_governor_plan` | `pba_adapters.mcp.server` | `WRAP_WITH_POLICY` | `plwc_governor(operation="plan")` |
| `pba_governor_apply` | `pba_adapters.mcp.server` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_governor(operation="apply")` |
| `pba_import_profile` | `pba_adapters.mcp.server` | `REPLACE_WITH_GOVERNED_TOOL` | Future governed onboarding import |

## Source A Module Classification

| Module or path | Classification | Notes |
| --- | --- | --- |
| `src/pba_core/compiler` | `KEEP_INTERNAL` | Prompt compilation core |
| `src/pba_core/runtime` | `KEEP_INTERNAL` | Profile loading, snapshot and runtime state |
| `src/pba_core/governor` | `KEEP_INTERNAL` | Condensation, semantics, change plans and apply logic |
| `src/pba_core/storage` | `KEEP_INTERNAL` | Must be reachable only through governed profile tools |
| `src/pba_adapters/api.py` | `KEEP_INTERNAL` | Preferred stable adapter reference |
| `src/pba_adapters/cli` | `KEEP_INTERNAL` | Useful for contracts and tests, not public |
| `src/pba_adapters/llm` | `KEEP_INTERNAL` | Adapter boundary reference |
| `src/pba_adapters/setup` | `KEEP_INTERNAL` | Reference only; PLwC owns onboarding |
| `src/pba_adapters/mcp` | `REMOVE_UNSAFE` | Source MCP boundary must not be public |
| `profiles/template` | `KEEP_INTERNAL` | Template reference; do not mutate source |
| `tests` | `KEEP_INTERNAL` | Test reference for PLwC contract tests |
| `Legacy/pba` | `REMOVE_UNSAFE` | Legacy runtime code is not a PLwC dependency |
| `install_pba2.bat` | `REMOVE_UNSAFE` | Source installer can create wrong boundary |
| `launcher.py` | `KEEP_INTERNAL` | Reference only |

## Source B MCP Entry Points

| Entry point | Observed behavior | Classification | PLwC decision |
| --- | --- | --- | --- |
| `src/index.ts` | Starts Desktop Commander MCP over stdio | `REMOVE_UNSAFE` | Do not expose or start |
| `src/server.ts` | Registers `desktop-commander` tools | `REMOVE_UNSAFE` | Tool behavior must be wrapped or replaced |
| `server.json` | MCP registry package metadata | `REMOVE_UNSAFE` | Do not publish |
| `server.yaml` | Docker/server package metadata | `REMOVE_UNSAFE` | Do not publish |
| `manifest.template.json` | MCPB manifest for Desktop Commander | `REMOVE_UNSAFE` | Do not package |
| `plugin.yaml` | Plugin metadata | `REMOVE_UNSAFE` | Do not expose |
| `smithery.yaml` | External server config | `REMOVE_UNSAFE` | Do not expose |
| `desktop-commander-*.mcpb` | Source bundle artifact | `REMOVE_UNSAFE` | Do not import into PLwC |

## Source B Tool Mapping

| Source tool | Classification | PLwC mapping |
| --- | --- | --- |
| `get_config` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_status(scope="runtime")` with redaction |
| `set_config_value` | `REMOVE_UNSAFE` | Manual local config only |
| `read_file` | `WRAP_WITH_POLICY` | `plwc_workspace_operation(operation="read")` |
| `read_multiple_files` | `WRAP_WITH_POLICY` | Internal `SafeFilesystemAdapter.read_multiple_text` with limits; not a separate public tool |
| `write_file` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_workspace_operation(operation="write")` |
| `write_pdf` | `REPLACE_WITH_GOVERNED_TOOL` | Future governed document tool |
| `create_directory` | `WRAP_WITH_POLICY` | Internal `SafeFilesystemAdapter.create_directory`; not a separate public tool |
| `list_directory` | `WRAP_WITH_POLICY` | `plwc_workspace_operation(operation="list")` |
| `move_file` | `REPLACE_WITH_GOVERNED_TOOL` | Internal `SafeFilesystemAdapter.move_path`; not a separate public tool |
| `start_search` | `WRAP_WITH_POLICY` | `plwc_workspace_operation(operation="search")` |
| `get_more_search_results` | `WRAP_WITH_POLICY` | `plwc_workspace_operation(operation="search")` pagination |
| `stop_search` | `WRAP_WITH_POLICY` | `plwc_workspace_operation(operation="search")` control |
| `list_searches` | `KEEP_INTERNAL` | Internal search status only |
| `get_file_info` | `WRAP_WITH_POLICY` | Internal `SafeFilesystemAdapter.file_info`; not a separate public tool |
| `edit_block` | `REPLACE_WITH_GOVERNED_TOOL` | Internal exact `SafeFilesystemAdapter.replace_text`; fuzzy write remains excluded |
| `run_shell_sandboxed` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_sandbox_run(lang="shell")` with server-selected profile |
| `run_python_sandboxed` | `REPLACE_WITH_GOVERNED_TOOL` | `plwc_sandbox_run(lang="python")` with server-selected profile |
| `make_slideshow` | `REPLACE_WITH_GOVERNED_TOOL` | Future governed media tool |
| `start_process` | `REMOVE_UNSAFE` | No direct host shell |
| `read_process_output` | `REMOVE_UNSAFE` | No host process sessions |
| `interact_with_process` | `REMOVE_UNSAFE` | No host process sessions or `node:local` |
| `force_terminate` | `REMOVE_UNSAFE` | No host process sessions |
| `list_sessions` | `REMOVE_UNSAFE` | No host process sessions |
| `list_processes` | `REMOVE_UNSAFE` | No host process enumeration |
| `kill_process` | `REMOVE_UNSAFE` | No direct PID termination |
| `get_usage_stats` | `KEEP_INTERNAL` | Optional redacted diagnostics only |
| `get_recent_tool_calls` | `KEEP_INTERNAL` | Replace with PLwC audit views if needed |
| `track_ui_event` | `REMOVE_UNSAFE` | No telemetry event tool |
| `give_feedback_to_desktop_commander` | `REMOVE_UNSAFE` | No browser-opening feedback tool |
| `get_prompts` | `REMOVE_UNSAFE` | Not part of PLwC boundary |

## Source B Module Classification

| Module or path | Classification | Notes |
| --- | --- | --- |
| `src/security/policy.ts` | `KEEP_INTERNAL` | Reference for local policy loading and fail-closed checks |
| `src/security/pathGuard.ts` | `KEEP_INTERNAL` | Strong allowed-root and traversal reference |
| `src/security/commandGuard.ts` | `KEEP_INTERNAL` | Sandbox command filter reference |
| `src/security/profiles.ts` | `KEEP_INTERNAL` | Sandbox profile defaults; PLwC owns final policy |
| `src/sandbox/dockerRunner.ts` | `WRAP_WITH_POLICY` | Docker args are built server-side from policy |
| `src/sandbox/dockerShell.ts` | `REPLACE_WITH_GOVERNED_TOOL` | No raw user-selected profile |
| `src/sandbox/dockerPython.ts` | `REPLACE_WITH_GOVERNED_TOOL` | No raw user-selected profile |
| `src/sandbox/dockerMedia.ts` | `REPLACE_WITH_GOVERNED_TOOL` | Future governed media adapter |
| `src/tools/filesystem.ts` | `WRAP_WITH_POLICY` | Reads are useful; writes require governed replacements |
| `src/tools/edit.ts` | `REPLACE_WITH_GOVERNED_TOOL` | Must enforce protected file rules |
| `src/tools/improved-process-tools.ts` | `REMOVE_UNSAFE` | Host shell and `node:local` are not allowed |
| `src/tools/process.ts` | `REMOVE_UNSAFE` | Process listing and killing are not allowed |
| `src/search-manager.ts` | `WRAP_WITH_POLICY` | Useful after path and result limits |
| `src/utils/files` | `KEEP_INTERNAL` | File type handlers are adapter reference |
| `src/ui` | `KEEP_INTERNAL` | Optional future UI resources; not public initially |
| `src/remote-device` | `REMOVE_UNSAFE` | Remote channel creates second control path |
| `src/npm-scripts` | `REMOVE_UNSAFE` | Setup/remove/remote scripts target source MCP |
| `setup-claude-server.js` | `REMOVE_UNSAFE` | Would install wrong public server |
| `uninstall-claude-server.js` | `REMOVE_UNSAFE` | Source-specific management |
| `track-installation.js` | `REMOVE_UNSAFE` | No hidden telemetry |
| `scripts/build-mcpb.cjs` | `KEEP_INTERNAL` | Packaging reference only |
| `docker/toolbox/Dockerfile` | `KEEP_INTERNAL` | Toolbox image reference; image is policy-owned |
| `test` | `KEEP_INTERNAL` | Security and behavior test reference |

## Public Surface Decision

The only `KEEP_PUBLIC` entry in the MCP server layer is the target
`plwc-gateway`.

Source tools may influence public PLwC capabilities only after one of these
transforms:

- wrap read-only behavior with PLwC policy and audit
- replace write or execution behavior with governed PLwC tools
- remove unsafe runtime behavior entirely
