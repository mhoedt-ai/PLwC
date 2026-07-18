import { isPlwcToolName, type PlwcToolName } from "./tool-call-parser";

export const PLWC_TOOL_RESULT_MARKER = "# PLwC Tool Result";

export interface PlwcToolResultEnvelope {
  call_id: string;
  is_error: boolean;
  name: PlwcToolName;
  result: unknown;
}

export function formatPlwcToolResultMessage(envelope: PlwcToolResultEnvelope): string {
  const payload = JSON.stringify(envelope, null, 2);
  return `${PLWC_TOOL_RESULT_MARKER}\n\n\`\`\`json\n${payload}\n\`\`\``;
}

export function parsePlwcToolResultMessage(text: string): PlwcToolResultEnvelope | null {
  let normalized = text.trim();
  if (normalized.startsWith(PLWC_TOOL_RESULT_MARKER)) {
    normalized = normalized.slice(PLWC_TOOL_RESULT_MARKER.length).trim();
  }
  normalized = stripFence(normalized);

  let value: unknown;
  try {
    value = JSON.parse(normalized);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  if (keys.some((key) => !["call_id", "is_error", "name", "result"].includes(key))) return null;
  if (
    typeof record.call_id !== "string" ||
    record.call_id.length === 0 ||
    record.call_id.length > 256 ||
    !isPlwcToolName(record.name) ||
    !Object.hasOwn(record, "result") ||
    (record.is_error !== undefined && typeof record.is_error !== "boolean")
  ) {
    return null;
  }
  return {
    call_id: record.call_id,
    is_error: record.is_error === true,
    name: record.name,
    result: record.result,
  };
}

function stripFence(text: string): string {
  const lines = text.split(/\r?\n/u);
  if (/^```(?:json)?$/iu.test(lines[0]?.trim() ?? "") && lines.at(-1)?.trim() === "```") {
    return lines.slice(1, -1).join("\n").trim();
  }
  if (lines[0]?.trim().toLowerCase() === "json") return lines.slice(1).join("\n").trim();
  return text;
}
