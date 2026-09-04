import { isPlwcToolName, type PlwcToolName } from "./tool-call-parser";
import { normalizeChatRenderedJsonWhitespace } from "./chat-json";
import { assertValidToolResultTransport } from "../shared/tool-result";
import {
  isPlwcOnboardingContinuation,
  type PlwcOnboardingContinuation,
} from "./onboarding-continuation";
import {
  isPlwcToolCallCorrection,
  type PlwcToolCallCorrection,
} from "./onboarding-correction";

export const PLWC_TOOL_RESULT_MARKER = "# PLwC Tool Result";

export interface PlwcToolResultEnvelope {
  call_id: string;
  continuation?: PlwcOnboardingContinuation;
  correction?: PlwcToolCallCorrection;
  is_error: boolean;
  name: PlwcToolName;
  result: unknown;
}

export function formatPlwcToolResultMessage(envelope: PlwcToolResultEnvelope): string {
  const transport = assertValidToolResultTransport(envelope.name, envelope.result);
  if (envelope.continuation && !isPlwcOnboardingContinuation(envelope.continuation)) {
    throw new Error("Invalid PLwC onboarding continuation.");
  }
  if (envelope.correction && !isPlwcToolCallCorrection(envelope.correction)) {
    throw new Error("Invalid PLwC tool-call correction.");
  }
  // Chunk transports already carry explicit boundaries and hashes. Compact
  // serialization keeps every byte of semantic content while reducing the
  // controlled-editor/React workload for large ChatGPT messages.
  const payload = transport.chunked
    ? JSON.stringify(envelope)
    : JSON.stringify(envelope, null, 2);
  return `${PLWC_TOOL_RESULT_MARKER}\n\n\`\`\`json\n${payload}\n\`\`\``;
}

export function parsePlwcToolResultMessage(text: string): PlwcToolResultEnvelope | null {
  let normalized = text.trim();
  if (normalized.startsWith(PLWC_TOOL_RESULT_MARKER)) {
    normalized = normalized.slice(PLWC_TOOL_RESULT_MARKER.length).trim();
  }
  normalized = normalizeChatRenderedJsonWhitespace(stripFence(normalized));

  let value: unknown;
  try {
    value = JSON.parse(normalized);
  } catch {
    return null;
  }
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  if (keys.some((key) => !["call_id", "continuation", "correction", "is_error", "name", "result"].includes(key))) return null;
  if (
    typeof record.call_id !== "string" ||
    record.call_id.length === 0 ||
    record.call_id.length > 256 ||
    !isPlwcToolName(record.name) ||
    !Object.hasOwn(record, "result") ||
    (record.is_error !== undefined && typeof record.is_error !== "boolean") ||
    (record.continuation !== undefined && !isPlwcOnboardingContinuation(record.continuation)) ||
    (record.correction !== undefined && !isPlwcToolCallCorrection(record.correction))
  ) {
    return null;
  }
  const envelope = {
    call_id: record.call_id,
    ...(record.continuation === undefined
      ? {}
      : { continuation: record.continuation }),
    ...(record.correction === undefined
      ? {}
      : { correction: record.correction }),
    is_error: record.is_error === true,
    name: record.name,
    result: record.result,
  };
  try {
    assertValidToolResultTransport(envelope.name, envelope.result);
  } catch {
    return null;
  }
  return envelope;
}

export function parsePlwcToolResultFromText(text: string): PlwcToolResultEnvelope | null {
  const renderedMarker = PLWC_TOOL_RESULT_MARKER.replace(/^#\s*/u, "");
  const exactIndex = text.indexOf(PLWC_TOOL_RESULT_MARKER);
  const renderedIndex = text.indexOf(renderedMarker);
  const markerIndex = exactIndex >= 0 ? exactIndex : renderedIndex;
  if (markerIndex < 0) return null;

  const markerLength = exactIndex >= 0 ? PLWC_TOOL_RESULT_MARKER.length : renderedMarker.length;
  const resultText = text.slice(markerIndex + markerLength);
  const direct = parsePlwcToolResultMessage(resultText);
  if (direct) return direct;

  const firstBrace = resultText.indexOf("{");
  const lastBrace = resultText.lastIndexOf("}");
  if (firstBrace < 0 || lastBrace <= firstBrace) return null;
  return parsePlwcToolResultMessage(resultText.slice(firstBrace, lastBrace + 1));
}

export function hasPlwcToolResultForCall(texts: Iterable<string>, callId: string): boolean {
  return findPlwcToolResultForCall(texts, callId) !== null;
}

export function findPlwcToolResultForCall(
  texts: Iterable<string>,
  callId: string,
): PlwcToolResultEnvelope | null {
  for (const text of texts) {
    const result = parsePlwcToolResultMessage(text) ?? parsePlwcToolResultFromText(text);
    if (result?.call_id === callId) return result;
  }
  return null;
}

function stripFence(text: string): string {
  const lines = text.split(/\r?\n/u);
  if (/^```(?:json)?$/iu.test(lines[0]?.trim() ?? "") && lines.at(-1)?.trim() === "```") {
    return lines.slice(1, -1).join("\n").trim();
  }
  if (lines[0]?.trim().toLowerCase() === "json") return lines.slice(1).join("\n").trim();
  return text.trim().replace(/^json\s*(?=\{)/iu, "");
}
