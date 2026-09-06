import { CANONICAL_TOOL_NAMES, type CanonicalToolName } from '../shared/contracts';
import { createToolCallIdentity } from '../shared/tool-call-identity';
import { normalizeChatRenderedJsonWhitespace } from './chat-json';

export const PLWC_TOOL_NAMES = CANONICAL_TOOL_NAMES;

export type PlwcToolName = CanonicalToolName;
export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export interface ToolCallTextCandidate {
  conversationId?: string;
  text: string;
  visible: boolean;
  sourceId?: string;
  sourceKind?: 'rendered' | 'editor-copy' | 'unknown';
}

export interface ParsedPlwcToolCall {
  name: PlwcToolName;
  callId: string;
  callSignatureKey: string;
  callKey: string;
  conversationId: string;
  arguments: Readonly<Record<string, JsonValue>>;
  description?: string;
  sourceId?: string;
  sourceIndex: number;
}

type JsonRecord = Record<string, unknown>;

export const PLWC_TOOL_CALL_WRAPPER_KEY = 'plwc_tool_call';

interface ActiveCall {
  name: PlwcToolName;
  callId: string;
  arguments: Record<string, JsonValue>;
  description?: string;
}

const TOOL_NAMES = new Set<string>(PLWC_TOOL_NAMES);
const ARGUMENT_KEY = /^[A-Za-z_][A-Za-z0-9_]*$/;
const FORBIDDEN_ARGUMENT_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

/** Parse complete PLwC calls from explicitly visible text sources without touching the DOM. */
export function parseVisiblePlwcToolCalls(
  candidates: readonly ToolCallTextCandidate[],
  defaultConversationId = 'unknown-conversation',
): ParsedPlwcToolCall[] {
  const orderedCandidates = candidates
    .map((candidate, sourceIndex) => ({ candidate, sourceIndex }))
    .filter(({ candidate }) => candidate.visible === true && typeof candidate.text === 'string')
    .sort((left, right) => {
      const priorityDifference = sourcePriority(left.candidate) - sourcePriority(right.candidate);
      return priorityDifference || left.sourceIndex - right.sourceIndex;
    });

  const calls: ParsedPlwcToolCall[] = [];
  const seenCallVariants = new Set<string>();

  for (const { candidate, sourceIndex } of orderedCandidates) {
    const parsed = parseCandidate(candidate.text);
    if (!parsed) continue;

    for (const call of parsed) {
      let identity;
      try {
        identity = createToolCallIdentity(
          candidate.conversationId ?? defaultConversationId,
          call.callId,
          call.name,
          call.arguments,
        );
      } catch {
        continue;
      }
      const callVariantKey = JSON.stringify([identity.identityKey, identity.signatureKey]);
      if (seenCallVariants.has(callVariantKey)) continue;

      seenCallVariants.add(callVariantKey);
      calls.push({
        name: call.name,
        callId: call.callId,
        callKey: identity.identityKey,
        callSignatureKey: identity.signatureKey,
        conversationId: identity.conversationId,
        arguments: call.arguments,
        ...(call.description === undefined ? {} : { description: call.description }),
        ...(candidate.sourceId === undefined ? {} : { sourceId: candidate.sourceId }),
        sourceIndex,
      });
    }
  }

  return calls;
}

export function resolveConversationId(documentValue: Document): string {
  const locationValue = documentValue.defaultView?.location;
  if (!locationValue) return boundedConversationId(documentValue.URL || 'unknown-document');
  const conversationMatch = locationValue.pathname.match(/(?:^|\/)c\/([^/?#]+)/u);
  if (conversationMatch?.[1]) return boundedConversationId(`c/${conversationMatch[1]}`);
  return boundedConversationId(
    `${locationValue.pathname}${locationValue.search}` || documentValue.URL || 'unknown-document',
  );
}

export function isPlwcToolName(value: unknown): value is PlwcToolName {
  return typeof value === 'string' && TOOL_NAMES.has(value);
}

function boundedConversationId(value: string): string {
  return value.length <= 512 ? value : value.slice(0, 512);
}

function sourcePriority(candidate: ToolCallTextCandidate): number {
  if (candidate.sourceKind === 'rendered') return 0;
  if (candidate.sourceKind === 'editor-copy') return 2;
  return 1;
}

function parseCandidate(text: string): ActiveCall[] | null {
  const envelopeCall = parseToolCallEnvelope(text);
  return envelopeCall ? [envelopeCall] : null;
}

function parseToolCallEnvelope(text: string): ActiveCall | null {
  const normalized = normalizeJsonBlock(text);
  if (!normalized) return null;

  let value: unknown;
  try {
    value = JSON.parse(normalized);
  } catch {
    return null;
  }

  if (!isJsonRecord(value) || !hasOnlyKeys(value, [PLWC_TOOL_CALL_WRAPPER_KEY])) return null;
  const envelope = value[PLWC_TOOL_CALL_WRAPPER_KEY];
  if (!isJsonRecord(envelope)) return null;
  if (!hasOnlyKeys(envelope, ['name', 'call_id', 'arguments', 'description'])) return null;

  const callId = parseCallId(envelope.call_id);
  const args = parseArguments(envelope.arguments);
  if (!isPlwcToolName(envelope.name) || callId === null || args === null) return null;
  if (envelope.description !== undefined && typeof envelope.description !== 'string') return null;

  return {
    name: envelope.name,
    callId,
    arguments: args,
    ...(envelope.description === undefined ? {} : { description: envelope.description }),
  };
}

function normalizeJsonBlock(text: string): string | null {
  const lines = text.trim().split(/\r?\n|\u2028|\u2029/u);
  while (lines[0]?.trim().toLowerCase() === 'copy code') lines.shift();
  if (lines[0]?.trim().toLowerCase() === 'json') lines.shift();

  if (/^```json$/iu.test(lines[0]?.trim() ?? '')) {
    if (lines.at(-1)?.trim() !== '```') return null;
    lines.shift();
    lines.pop();
  } else if (lines.some(line => line.trim().startsWith('```'))) {
    return null;
  }

  const normalized = normalizeChatRenderedJsonWhitespace(
    lines.join('\n').trim().replace(/^json\s*(?=\{)/iu, ''),
  );
  return normalized.length > 0 ? normalized : null;
}

function parseCallId(value: unknown): string | null {
  if (typeof value === 'number') {
    return Number.isSafeInteger(value) && value > 0 ? String(value) : null;
  }

  if (typeof value !== 'string' || value.length === 0 || value.length > 256) return null;
  if (value.trim() !== value || /[\u0000-\u001f\u007f]/u.test(value)) return null;
  return value;
}

function isArgumentKey(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length <= 128 &&
    ARGUMENT_KEY.test(value) &&
    !FORBIDDEN_ARGUMENT_KEYS.has(value)
  );
}

function parseArguments(value: unknown): Record<string, JsonValue> | null {
  if (!isJsonRecord(value)) return null;
  const args: Record<string, JsonValue> = {};
  for (const [key, nestedValue] of Object.entries(value)) {
    if (!isArgumentKey(key) || !isJsonValue(nestedValue)) return null;
    Object.defineProperty(args, key, {
      value: nestedValue,
      enumerable: true,
      configurable: false,
      writable: false,
    });
  }
  return args;
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasOnlyKeys(record: JsonRecord, allowed: readonly string[]): boolean {
  const allowedKeys = new Set(allowed);
  return Object.keys(record).every(key => allowedKeys.has(key));
}

function isJsonValue(value: unknown): value is JsonValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
  if (typeof value === 'number') return Number.isFinite(value);
  if (Array.isArray(value)) return value.every(isJsonValue);
  if (!isJsonRecord(value)) return false;
  return Object.entries(value).every(
    ([key, nestedValue]) => key.length > 0 && !FORBIDDEN_ARGUMENT_KEYS.has(key) && isJsonValue(nestedValue),
  );
}
