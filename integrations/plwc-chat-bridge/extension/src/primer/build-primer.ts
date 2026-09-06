import {
  BRIDGE_VERSION,
  computeToolSchemaIntegrity,
  isJsonObject,
  type JsonObject,
  type McpTool,
  stableStringify,
  validateToolSet,
} from "../shared/contracts";
import { EXTENSION_BUILD_IDENTITY } from "../shared/build-identity";

export interface BridgePrimer {
  hash: string;
  integrityVerified: true;
  text: string;
  tools: McpTool[];
}

type WorkspaceGuidanceLanguage = "de" | "en";

export const WORKSPACE_GUIDANCE_RULES = [
  {
    de: "Speichere notwendige Zwischenprodukte ausschließlich unter Temp/<task-name>/.",
    en: "Store required intermediate products only under Temp/<task-name>/.",
    id: "intermediate_products",
  },
  {
    de: "Speichere Endergebnisse an dem vom Benutzer genannten Zielpfad.",
    en: "Store final results at the target path requested by the user.",
    id: "final_results",
  },
  {
    de: "Bereinige Temp/ niemals automatisch und lösche dort niemals Inhalte automatisch.",
    en: "Never clean up Temp/ automatically and never delete its contents automatically.",
    id: "no_temp_cleanup",
  },
  {
    de: "Lösche keine Dateien oder Verzeichnisse im Workspace.",
    en: "Do not delete files or directories in the workspace.",
    id: "no_workspace_delete",
  },
  {
    de: "Biete bei einem ausdrücklichen Löschwunsch an, das Element mit plwc_workspace_operation operation=move nach Trashcan/ zu verschieben.",
    en: "For an explicit deletion request, offer to move the item to Trashcan/ with plwc_workspace_operation operation=move.",
    id: "explicit_delete_offer",
  },
  {
    de: "Verschiebe niemals automatisch etwas nach Trashcan/.",
    en: "Never move anything to Trashcan/ automatically.",
    id: "no_automatic_trashcan",
  },
  {
    de: "Erstelle oder verwende kein Inbox/.",
    en: "Do not create or use Inbox/.",
    id: "no_inbox",
  },
] as const;

export const GUIDED_DOCUMENT_WORKFLOW_EXAMPLE = {
  intermediatePaths: [
    "Temp/document-acceptance/extracted/source.txt",
    "Temp/document-acceptance/rendered/page-1.png",
  ],
  taskName: "document-acceptance",
  userRequestedFinalTarget: "Deliverables/document-acceptance.pdf",
} as const;

function workspaceGuidanceLines(language: WorkspaceGuidanceLanguage): string[] {
  return WORKSPACE_GUIDANCE_RULES.map((rule) => `- [${rule.id}] ${rule[language]}`);
}

function exampleValue(schema: unknown): unknown {
  if (typeof schema !== "object" || schema === null || Array.isArray(schema)) {
    return "<value>";
  }
  const record = schema as JsonObject;
  if (record.default !== undefined) return record.default;
  if (Array.isArray(record.enum) && record.enum.length > 0) return record.enum[0];
  if (record.type === "boolean") return false;
  if (record.type === "integer" || record.type === "number") return 0;
  if (record.type === "array") return [];
  if (record.type === "object") return {};
  return `<${typeof record.type === "string" ? record.type : "value"}>`;
}

function callArguments(tool: McpTool): JsonObject {
  const properties =
    typeof tool.inputSchema.properties === "object" && tool.inputSchema.properties !== null
      ? (tool.inputSchema.properties as JsonObject)
      : {};
  const required = new Set(Array.isArray(tool.inputSchema.required) ? tool.inputSchema.required : []);
  const argumentsValue: JsonObject = Object.fromEntries(
    Object.keys(properties)
      .filter((name) => required.has(name))
      .sort()
      .map((name) => [name, exampleValue(properties[name])]),
  );
  if (tool.name === "plwc_status" && Object.hasOwn(properties, "scope")) {
    argumentsValue.scope = "runtime";
  }
  return argumentsValue;
}

function callMask(tool: McpTool): string {
  const callId = `${tool.name}-example`;
  return stableStringify({
    plwc_tool_call: {
      arguments: callArguments(tool),
      call_id: callId,
      name: tool.name,
    },
  });
}

export async function buildPrimer(value: unknown): Promise<BridgePrimer> {
  const validation = validateToolSet(value);
  if (!validation.valid) {
    const issues = [
      validation.missing.length ? `missing=${validation.missing.join(",")}` : "",
      validation.extra.length ? `extra=${validation.extra.join(",")}` : "",
      validation.duplicates.length ? `duplicates=${validation.duplicates.join(",")}` : "",
      validation.invalidSchemas.length ? `invalidSchemas=${validation.invalidSchemas.join(",")}` : "",
    ].filter(Boolean);
    throw new Error(`PLwC tool contract mismatch: ${issues.join("; ") || "invalid tools/list payload"}`);
  }

  const integrity = await computeToolSchemaIntegrity(validation);
  if (isJsonObject(value)) {
    if (value.integrityVerified !== undefined && value.integrityVerified !== true) {
      throw new Error("PLwC tool schema integrity was not verified by the extension background.");
    }
    if (typeof value.schemaSha256 === "string" && value.schemaSha256 !== integrity.schemaSha256) {
      throw new Error("PLwC tool schema integrity changed in transit.");
    }
  }
  const hash = integrity.schemaSha256;
  const lines = [
    "# PLwC Bridge Primer",
    `bridge_version: ${BRIDGE_VERSION}`,
    `build_id: ${EXTENSION_BUILD_IDENTITY.buildId}`,
    `node_bridge_version: ${EXTENSION_BUILD_IDENTITY.components.nodeBridge}`,
    `browser_extension_version: ${EXTENSION_BUILD_IDENTITY.components.browserExtension}`,
    `native_launcher_version: ${EXTENSION_BUILD_IDENTITY.components.nativeLauncher}`,
    `schema_sha256: ${hash}`,
    `integrity_verified: ${integrity.integrityVerified}`,
    "data_flow: Chat content selected for a tool call is sent through the local browser extension and loopback bridge to the local PLwC Gateway. The chat itself is processed by ChatGPT and is not claimed to remain local.",
    "confirmation_rules:",
    "- Read-only status, describe, profile, and recognized inspection operations may run without mutation confirmation.",
    "- Recognized workspace, document, reflection, and Governor writes require confirmation. The bridge may satisfy it only when the user enabled standing write confirmation in Settings, except for profile creation and activation.",
    "- Sandbox execution and unknown operations always require individual confirmation and are never covered by standing write confirmation.",
    "- Profile creation and activation always require individual confirmation and are never covered by standing confirmation.",
    "- plwc_governor with operation=apply requires confirmed=true after individual or eligible enabled standing write confirmation.",
    "- Unknown tools or operations must not run. Never retry a mutating call after an ambiguous timeout.",
    "tool_call_format: Emit each requested tool call as one fenced json code block containing exactly one PLwC wrapper object.",
    "tool_call_protocol:",
    "- The top-level object must have exactly one key: plwc_tool_call.",
    "- plwc_tool_call must contain name, call_id, and arguments.",
    "- arguments must be one JSON object containing all argument keys and JSON values.",
    "- Emit at most one tool call at a time. Wait for its marked result before emitting a dependent call.",
    "- A call is pending only when your current response contains a complete plwc_tool_call object. Never invent, skip, or wait for an unissued call_id.",
    "- After a marked result, either emit exactly one next call when work remains or provide the final summary when the task is complete. Never claim that a result is missing for a call you did not emit.",
    "- Never emit placeholders, prose inside the block, event records, unwrapped name/arguments objects, or calls not requested by the user.",
    "describe_guidance_protocol:",
    "- If a target tool's operation name, schema, required fields, or argument shape is unclear, emit one precise plwc_describe call before the target call.",
    "- Use the canonical scope for the target facade: workspace_operation, document_operation, profiles, reflection, governor, sandbox, status, or tools.",
    "- The plwc_describe operation filter is valid only for scope=workspace_operation and scope=document_operation. For those two scopes, include the exact intended operation, for example scope=document_operation with operation=create_pdf.",
    "- Never send operation with plwc_describe scope=status, governor, profiles, reflection, sandbox, or tools. Omit operation for those Describe scopes.",
    "- plwc_status is a separate tool, not a Describe operation. To inspect onboarding entry state, call plwc_status with exactly {\"scope\":\"first_run\"}.",
    "- Never guess an operation name or operation arguments from prose, prior chat, a near match, or a different tool's schema.",
    "- Follow the returned next_tool, next_operation, next_plan_type, required_fields, supported_operations, and example_call fields. Do not retry an unsupported operation with another guess.",
    "- Unknown target operations are never eligible for automatic execution, including when standing write or sandbox confirmation is enabled.",
    "large_work_protocol:",
    "- Do not serialize large generated files, long CSV tables, full source indexes, or bulk classification output through a plwc_workspace_operation write content parameter.",
    "- For batch analysis or large derived files, emit one small plwc_sandbox_run call that reads workspace files and writes the derived artifacts locally; keep stdout to paths, counts, and the next gate decision.",
    "- Use plwc_workspace_operation write only for concise direct files or small edits that comfortably fit in chat. If output may exceed a few thousand characters, prefer sandbox-written workspace artifacts.",
    "workspace_handling_rules_en:",
    ...workspaceGuidanceLines("en"),
    "workspace_handling_rules_de:",
    ...workspaceGuidanceLines("de"),
    "guided_document_workflow_example:",
    `- task_name: ${GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.taskName}`,
    `- user_requested_final_target: ${GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.userRequestedFinalTarget}`,
    "- required_intermediate_paths:",
    ...GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.intermediatePaths.map((path) => `  - ${path}`),
    "- EN: This example assumes the user requested the stated final target. Keep only actually required intermediate artifacts under the task-specific Temp/ directory, and place the final document at the user's target.",
    "- DE: Dieses Beispiel setzt voraus, dass der Benutzer den genannten Zielpfad angefordert hat. Lege nur tatsächlich notwendige Zwischenprodukte im auftragsspezifischen Temp/-Verzeichnis und das Enddokument am Benutzerziel ab.",
    "large_result_chunk_protocol:",
    "- If result_transport.chunked=true and protocol=plwc_result_chunks.v1, the complete original JSON result is transported in result_transport.chunks.",
    "- Require exactly total_chunks unique chunks with contiguous chunk_index values from 1 through total_chunks, and require received_chunks == total_chunks.",
    "- Recompute every chunk SHA-256 from chunk.text, concatenate chunks[].text in chunk_index order, recompute the complete SHA-256, compare it with sha256 and reconstructed_sha256, then parse the reconstructed JSON.",
    "- Treat the result as complete only when complete=true and no_omitted_content=true. If the chunk metadata is inconsistent, report a transport failure and rerun the call.",
    "- Do not request a narrower follow-up call merely because a complete result was chunked, and never answer from result_summary instead of the reconstructed JSON.",
    "legacy_large_result_compact_protocol:",
    "- Older chat messages may contain result_transport.compacted=true with protocol=plwc_result_compact.v1. Those legacy results omitted content and require a narrower follow-up call when the missing content matters.",
    "profile_compile_layer_chunk_protocol:",
    "- For plwc_profile operation=compile, compile_mode=boot, working, and full all use the same completeness rule for data.compiled_layer.",
    "- If result_transport.profile_compile_layer_chunked=true, the full layer is transported in data.compiled_layer_transport.chunks; concatenate chunks[].text in chunk_index order.",
    "- Treat the layer as complete only when received_chunks == total_chunks and sha256 == reconstructed_sha256 in the transport metadata.",
    "- For compile_mode=full, never claim full completeness unless the chunk metadata says complete=true and no_omitted_content=true.",
    "- Do not request a sandbox artifact for a chunked profile compile layer; the Chat Bridge has already transported the chunks in the result.",
    "- If chunk metadata is missing, inconsistent, or incomplete, report the transport failure and ask for a rerun or a narrower compile request.",
    "profile_context_protocol:",
    "- plwc_status profile_name inspects a requested onboarding target only. It never creates, selects, or activates a profile.",
    "- Keep requested_profile_name, active_profile_name, and profile_path semantically separate. A requested profile is not active merely because it was inspected.",
    "- To inspect a specific profile in detail, use plwc_profile operation=status with profile set explicitly. Do not treat a plwc_status response as proof that profile_name changed the active context.",
    "- If the requested profile does not exist, do not tell the user to select it in Extension settings first. Collect the onboarding answers and call plwc_governor operation=plan with plan_type=profile_creation, explicit profile, and the same onboarding_answers.profile_name.",
    "- When onboarding guidance returns next_tool, next_operation, next_plan_type, required_fields, or example_call, use those fields as the authoritative next step instead of inventing a profile action.",
    "- After the user reviews the profile_creation plan, call plwc_governor operation=apply with the same profile and onboarding answers plus confirmed=true. A successful apply creates and activates the new profile through governed PLwC state.",
    "- To switch to an existing valid profile, use the profile_activation Governor plan/apply flow with explicit confirmation. Never emulate activation with plwc_status, plwc_profile compile, or an unverified settings claim.",
    "- After a successful creation or activation apply, call plwc_status scope=runtime without profile_name and trust the returned governed active profile state. Manual Extension settings changes are not required.",
    "workspace_evidence_rules:",
    "- plwc_workspace_operation search scans text contents; it does not prove that a filename mentioned by an inventory, index, profile, or document exists at that location.",
    "- To locate a file by name, inspect real directory entries with operation=list and sufficient depth, then verify the selected path with operation=file_info.",
    "- Treat paths learned from inventories, indexes, profile text, prior chat, or search match lines only as unverified candidates. Never report them as found and never mutate them before file_info returns ok=true for that exact path.",
    "- Claim a workspace mutation succeeded only when its marked result contains ok=true. If ok=false or policy_decision=DENY, report the failure and do not issue a dependent mutation.",
    "tool_result_protocol:",
    "- The bridge returns a marked PLwC Tool Result message with the same call_id after execution.",
    "- Continue from that result and summarize it naturally. Do not reproduce the raw result JSON unless the user asks for it.",
    "- Never request confirmation a second time for a call whose marked result has already been returned.",
    "onboarding_continuation_protocol:",
    "- A marked result may contain continuation.protocol=plwc_onboarding_continuation.v1 and one exact continuation.next_call PLwC wrapper.",
    "- Preserve next_call.name, next_call.call_id, and all next_call.arguments exactly. Never replace a continuation Governor call with plwc_describe and never omit onboarding_answers.",
    "- state=awaiting_user_confirmation does not grant confirmation. Emit the exact Governor apply next_call only after the user explicitly confirms the reviewed plan.",
    "- state=verify_active_profile follows a successful apply. Emit the exact read-only runtime-status next_call before reporting which profile is active.",
    "tool_call_correction_protocol:",
    "- A marked result may contain correction.protocol=plwc_tool_call_correction.v1 and one exact correction.next_call PLwC wrapper.",
    "- Preserve correction.next_call.name, call_id, and arguments exactly. Do not retry the rejected call shape or substitute another tool.",
    "- reason=invalid_onboarding_describe_filter means onboarding was incorrectly requested through plwc_describe. Emit the supplied plwc_status scope=first_run call next.",
    "tools:",
  ];

  for (const tool of validation.tools) {
    lines.push(`- ${tool.name}`);
    lines.push(`  description: ${JSON.stringify(tool.description ?? "")}`);
    lines.push("  call_mask_json: |");
    lines.push(`    ${callMask(tool)}`);
    lines.push(`  input_schema: ${stableStringify(tool.inputSchema)}`);
  }

  return { hash, integrityVerified: true, text: `${lines.join("\n")}\n`, tools: validation.tools };
}
