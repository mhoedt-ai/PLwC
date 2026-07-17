// Derived from Saurabh Patel's 2025 MIT-licensed JSONL parser; see ../../../UPSTREAM.md.

import { CANONICAL_TOOL_NAMES, type CanonicalToolName } from '../shared/contracts';

export const PLWC_TOOL_NAMES = CANONICAL_TOOL_NAMES;

export type PlwcToolName = CanonicalToolName;
export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export interface ToolCallTextCandidate {
  text: string;
  visible: boolean;
  sourceId?: string;
  sourceKind?: 'rendered' | 'editor-copy' | 'unknown';
}

export interface ParsedPlwcToolCall {
  name: PlwcToolName;
  callId: string;
  callKey: string;
  arguments: Readonly<Record<string, JsonValue>>;
  description?: string;
  sourceId?: string;
  sourceIndex: number;
}

type JsonRecord = Record<string, unknown>;

interface ActiveCall {
  name: PlwcToolName;
  callId: string;
  arguments: Record<string, JsonValue>;
  description?: string;
}

const TOOL_NAMES = new Set<string>(PLWC_TOOL_NAMES);
const ARGUMENT_KEY = /^[A-Za-z_][A-Za-z0-9_]*$/;
const FORBIDDEN_ARGUMENT_KEYS = new Set(['__proto__', 'constructor', 'prototype']);

/** Parse complete JSONL calls from explicitly visible text sources without touching the DOM. */
export function parseVisiblePlwcToolCalls(
  candidates: readonly ToolCallTextCandidate[],
): ParsedPlwcToolCall[] {
  const orderedCandidates = candidates
    .map((candidate, sourceIndex) => ({ candidate, sourceIndex }))
    .filter(({ candidate }) => candidate.visible === true && typeof candidate.text === 'string')
    .sort((left, right) => {
      const priorityDifference = sourcePriority(left.candidate) - sourcePriority(right.candidate);
      return priorityDifference || left.sourceIndex - right.sourceIndex;
    });

  const calls: ParsedPlwcToolCall[] = [];
  const seenCallKeys = new Set<string>();

  for (const { candidate, sourceIndex } of orderedCandidates) {
    const parsed = parseCandidate(candidate.text);
    if (!parsed) continue;

    for (const call of parsed) {
      const callKey = createCallKey(call);
      if (seenCallKeys.has(callKey)) continue;

      seenCallKeys.add(callKey);
      calls.push({
        name: call.name,
        callId: call.callId,
        callKey,
        arguments: call.arguments,
        ...(call.description === undefined ? {} : { description: call.description }),
        ...(candidate.sourceId === undefined ? {} : { sourceId: candidate.sourceId }),
        sourceIndex,
      });
    }
  }

  return calls;
}

export function isPlwcToolName(value: unknown): value is PlwcToolName {
  return typeof value === 'string' && TOOL_NAMES.has(value);
}

function sourcePriority(candidate: ToolCallTextCandidate): number {
  if (candidate.sourceKind === 'rendered') return 0;
  if (candidate.sourceKind === 'editor-copy') return 2;
  return 1;
}

function parseCandidate(text: string): ActiveCall[] | null {
  const lines = normalizeJsonlLines(text);
  if (!lines || lines.length === 0) return null;

  const calls: ActiveCall[] = [];
  let active: ActiveCall | undefined;

  for (const line of lines) {
    let event: unknown;
    try {
      event = JSON.parse(line);
    } catch {
      return null;
    }

    if (!isJsonRecord(event) || typeof event.type !== 'string') return null;

    switch (event.type) {
      case 'function_call_start': {
        if (active || !hasOnlyKeys(event, ['type', 'name', 'call_id'])) return null;
        const callId = parseCallId(event.call_id);
        if (!isPlwcToolName(event.name) || callId === null) return null;
        active = { name: event.name, callId, arguments: {} };
        break;
      }

      case 'description': {
        if (!active || !hasOnlyKeys(event, ['type', 'text', 'call_id'])) return null;
        if (typeof event.text !== 'string' || active.description !== undefined) return null;
        if (!matchesActiveCallId(event, active.callId)) return null;
        active.description = event.text;
        break;
      }

      case 'parameter': {
        if (!active || !hasOnlyKeys(event, ['type', 'key', 'value', 'call_id'])) return null;
        if (!isArgumentKey(event.key) || !Object.hasOwn(event, 'value')) return null;
        if (!matchesActiveCallId(event, active.callId) || !isJsonValue(event.value)) return null;
        if (Object.hasOwn(active.arguments, event.key)) return null;
        Object.defineProperty(active.arguments, event.key, {
          value: event.value,
          enumerable: true,
          configurable: false,
          writable: false,
        });
        break;
      }

      case 'function_call_end': {
        if (!active || !hasOnlyKeys(event, ['type', 'call_id'])) return null;
        const callId = parseCallId(event.call_id);
        if (callId === null || callId !== active.callId) return null;
        calls.push(active);
        active = undefined;
        break;
      }

      default:
        return null;
    }
  }

  return !active && calls.length > 0 ? calls : null;
}

function normalizeJsonlLines(text: string): string[] | null {
  const lines = text
    .split(/\r?\n|\u2028|\u2029/u)
    .map(line => line.trim())
    .filter(Boolean);

  if (lines.length === 0) return [];

  const openingFence = /^```(?:jsonl|json)?$/iu;
  const firstLine = lines[0];
  if (firstLine !== undefined && openingFence.test(firstLine)) {
    if (lines.at(-1) !== '```') return null;
    lines.shift();
    lines.pop();
  } else if (lines.some(line => line.startsWith('```'))) {
    return null;
  }

  if (lines[0]?.toLowerCase() === 'jsonl' || lines[0]?.toLowerCase() === 'json') {
    lines.shift();
  }

  if (lines[0]?.toLowerCase() === 'copy code') {
    lines.shift();
  }

  return lines;
}

function parseCallId(value: unknown): string | null {
  if (typeof value === 'number') {
    return Number.isSafeInteger(value) && value > 0 ? String(value) : null;
  }

  if (typeof value !== 'string' || value.length === 0 || value.length > 256) return null;
  if (value.trim() !== value || /[\u0000-\u001f\u007f]/u.test(value)) return null;
  return value;
}

function matchesActiveCallId(event: JsonRecord, activeCallId: string): boolean {
  if (!Object.hasOwn(event, 'call_id')) return true;
  return parseCallId(event.call_id) === activeCallId;
}

function isArgumentKey(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length <= 128 &&
    ARGUMENT_KEY.test(value) &&
    !FORBIDDEN_ARGUMENT_KEYS.has(value)
  );
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

function createCallKey(call: ActiveCall): string {
  return stableJson({
    arguments: call.arguments,
    callId: call.callId,
    name: call.name,
  });
}

function stableJson(value: JsonValue): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableJson).join(',')}]`;

  return `{${Object.keys(value)
    .sort()
    .map(key => `${JSON.stringify(key)}:${stableJson(value[key]!)}`)
    .join(',')}}`;
}
