import {
  BRIDGE_VERSION,
  type JsonObject,
  type McpTool,
  sha256,
  stableStringify,
  validateToolSet,
} from "../shared/contracts";

export interface BridgePrimer {
  hash: string;
  text: string;
  tools: McpTool[];
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

function callMask(tool: McpTool): string[] {
  const callId = `${tool.name}-example`;
  const parameters = Object.entries(callArguments(tool)).map(([key, value]) =>
    stableStringify({ call_id: callId, key, type: "parameter", value }),
  );
  return [
    stableStringify({ call_id: callId, name: tool.name, type: "function_call_start" }),
    ...parameters,
    stableStringify({ call_id: callId, type: "function_call_end" }),
  ];
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

  const schemaPayload = validation.tools.map((tool) => ({
    description: tool.description ?? "",
    inputSchema: tool.inputSchema,
    name: tool.name,
  }));
  const hash = await sha256(stableStringify(schemaPayload));
  const lines = [
    "# PLwC Bridge Primer",
    `bridge_version: ${BRIDGE_VERSION}`,
    `schema_sha256: ${hash}`,
    "data_flow: Chat content selected for a tool call is sent through the local browser extension and loopback bridge to the local PLwC Gateway. The chat itself is processed by ChatGPT and is not claimed to remain local.",
    "confirmation_rules:",
    "- Read-only status, describe, profile, and recognized inspection operations may run without mutation confirmation.",
    "- Recognized workspace, document, reflection, and Governor writes require confirmation. The bridge may satisfy it only when the user enabled standing write confirmation in Settings.",
    "- Sandbox execution and unknown operations always require individual confirmation and are never covered by standing write confirmation.",
    "- plwc_governor with operation=apply requires confirmed=true after individual or enabled standing write confirmation.",
    "- Unknown tools or operations must not run. Never retry a mutating call after an ambiguous timeout.",
    "tool_call_format: Emit each requested tool call as one fenced jsonl code block containing only the event lines below.",
    "tool_call_protocol:",
    "- Begin with one function_call_start event containing type, name, and a unique call_id.",
    "- Emit one parameter event per argument with the same call_id, key, and JSON value.",
    "- Finish with one function_call_end event containing the same call_id.",
    "- Emit at most one tool call at a time. Wait for its marked result before emitting a dependent call.",
    "- Never emit placeholders, prose inside the block, direct name/arguments objects, or calls not requested by the user.",
    "workspace_evidence_rules:",
    "- plwc_workspace_operation search scans text contents; it does not prove that a filename mentioned by an inventory, index, profile, or document exists at that location.",
    "- To locate a file by name, inspect real directory entries with operation=list and sufficient depth, then verify the selected path with operation=file_info.",
    "- Treat paths learned from inventories, indexes, profile text, prior chat, or search match lines only as unverified candidates. Never report them as found and never mutate them before file_info returns ok=true for that exact path.",
    "- Claim a workspace mutation succeeded only when its marked result contains ok=true. If ok=false or policy_decision=DENY, report the failure and do not issue a dependent mutation.",
    "tool_result_protocol:",
    "- The bridge returns a marked PLwC Tool Result message with the same call_id after execution.",
    "- Continue from that result and summarize it naturally. Do not reproduce the raw result JSON unless the user asks for it.",
    "- Never request confirmation a second time for a call whose marked result has already been returned.",
    "tools:",
  ];

  for (const tool of validation.tools) {
    lines.push(`- ${tool.name}`);
    lines.push(`  description: ${JSON.stringify(tool.description ?? "")}`);
    lines.push("  call_mask_jsonl: |");
    for (const event of callMask(tool)) lines.push(`    ${event}`);
    lines.push(`  input_schema: ${stableStringify(tool.inputSchema)}`);
  }

  return { hash, text: `${lines.join("\n")}\n`, tools: validation.tools };
}
