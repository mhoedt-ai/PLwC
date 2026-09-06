import type { ToolCallIdentity } from "./tool-call-identity";

export const PROCESSED_TOOL_CALLS_STORAGE_KEY = "processedToolCallsV1";
export const MAX_PROCESSED_TOOL_CALLS = 5_000;

export interface ProcessedToolCall {
  callId: string;
  claimedAt: number;
  conversationId: string;
  identityKey: string;
  signatureKey: string;
}

export interface ProcessedToolCallRegistry {
  entries: ProcessedToolCall[];
  version: 1;
}

export type ToolCallClaimOutcome =
  | { kind: "claimed"; registry: ProcessedToolCallRegistry }
  | { kind: "duplicate"; existing: ProcessedToolCall; registry: ProcessedToolCallRegistry }
  | { kind: "conflict"; existing: ProcessedToolCall; registry: ProcessedToolCallRegistry }
  | { kind: "capacity"; registry: ProcessedToolCallRegistry };

export function parseProcessedToolCallRegistry(value: unknown): ProcessedToolCallRegistry {
  if (value === undefined) return emptyProcessedToolCallRegistry();
  if (!isRecord(value) || value.version !== 1 || !Array.isArray(value.entries)) {
    throw new Error("Invalid persisted PLwC tool call registry.");
  }

  const entries = value.entries.map((entry) => {
    if (
      !isRecord(entry) ||
      typeof entry.callId !== "string" ||
      typeof entry.claimedAt !== "number" ||
      !Number.isFinite(entry.claimedAt) ||
      typeof entry.conversationId !== "string" ||
      typeof entry.identityKey !== "string" ||
      typeof entry.signatureKey !== "string"
    ) {
      throw new Error("Invalid persisted PLwC tool call registry entry.");
    }
    return {
      callId: entry.callId,
      claimedAt: entry.claimedAt,
      conversationId: entry.conversationId,
      identityKey: entry.identityKey,
      signatureKey: entry.signatureKey,
    };
  });
  if (entries.length > MAX_PROCESSED_TOOL_CALLS) {
    throw new Error("Persisted PLwC tool call registry exceeds its safe capacity.");
  }

  return { entries, version: 1 };
}

export function claimToolCallExecution(
  registry: ProcessedToolCallRegistry,
  identity: ToolCallIdentity,
  now = Date.now(),
): ToolCallClaimOutcome {
  const existing = registry.entries.find((entry) => entry.identityKey === identity.identityKey);
  if (existing) {
    return {
      existing,
      kind: existing.signatureKey === identity.signatureKey ? "duplicate" : "conflict",
      registry,
    };
  }
  if (registry.entries.length >= MAX_PROCESSED_TOOL_CALLS) {
    return { kind: "capacity", registry };
  }

  const claimed: ProcessedToolCall = {
    callId: identity.callId,
    claimedAt: now,
    conversationId: identity.conversationId,
    identityKey: identity.identityKey,
    signatureKey: identity.signatureKey,
  };
  return {
    kind: "claimed",
    registry: {
      entries: [...registry.entries, claimed],
      version: 1,
    },
  };
}

function emptyProcessedToolCallRegistry(): ProcessedToolCallRegistry {
  return { entries: [], version: 1 };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
