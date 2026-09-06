import {
  ToolCallObservationGate,
  type ToolCallObservationScan,
} from "../../src/content/tool-call-observer";
import type { ToolCallTextCandidate } from "../../src/content/tool-call-parser";
import {
  claimToolCallExecution,
  parseProcessedToolCallRegistry,
} from "../../src/shared/tool-call-execution-registry";
import { createToolCallIdentity } from "../../src/shared/tool-call-identity";

export function runP001BrowserAcceptance(): void {
  verifyBrowserRestartRegistry();
  verifyOldChatBaseline();
  verifyConversationSwitch();
  verifyDelayedHistoryHydration();
  verifyPayloadConflict();
}

function verifyBrowserRestartRegistry(): void {
  const identity = createToolCallIdentity("c/restart", "call-1", "plwc_status", {
    scope: "runtime",
  });
  const first = claimToolCallExecution(parseProcessedToolCallRegistry(undefined), identity, 100);
  expect(first.kind === "claimed", "Browser restart fixture could not claim the initial call.");
  const restored = parseProcessedToolCallRegistry(JSON.parse(JSON.stringify(first.registry)));
  const duplicate = claimToolCallExecution(restored, identity, 200);
  expect(duplicate.kind === "duplicate", "Browser restart fixture reopened a processed call.");
}

function verifyOldChatBaseline(): void {
  const existing = candidate("plwc_status", "old-call", "runtime");
  const gate = new ToolCallObservationGate([existing], "c/old", 0);
  const result = gate.scan([existing], "c/old", 1_000);
  expectNoCalls(result, "Old chat fixture reclassified an existing call.");
}

function verifyConversationSwitch(): void {
  const firstOld = candidate("plwc_status", "first-old", "runtime");
  const firstNew = candidate("plwc_profile", "first-new", "runtime");
  const secondOld = candidate("plwc_status", "second-old", "runtime");
  const gate = new ToolCallObservationGate([firstOld], "c/first", 0);
  gate.scan([firstOld], "c/first", 1_000);
  expect(
    gate.scan([firstOld, firstNew], "c/first", 1_100).calls.length === 1,
    "Conversation switch fixture did not admit a genuinely new call.",
  );
  expectNoCalls(
    gate.scan([secondOld], "c/second", 2_000),
    "Conversation switch fixture offered history from the second chat.",
  );
  gate.scan([secondOld], "c/second", 3_000);
  expectNoCalls(
    gate.scan([firstOld, firstNew], "c/first", 4_000),
    "Conversation switch fixture re-offered a call after returning to the first chat.",
  );
}

function verifyDelayedHistoryHydration(): void {
  const existing = candidate("plwc_status", "old-status", "runtime");
  const hydrated = candidate("plwc_profile", "old-profile", "runtime");
  const fresh = candidate("plwc_status", "new-status", "runtime");
  const gate = new ToolCallObservationGate([existing], "c/hydration", 0);
  gate.noteMutation(100);
  expectNoCalls(
    gate.scan([existing, hydrated], "c/hydration", 220),
    "Delayed hydration fixture offered history during the idle window.",
  );
  gate.scan([existing, hydrated], "c/hydration", 1_200);
  const result = gate.scan([existing, hydrated, fresh], "c/hydration", 1_300);
  expect(
    result.calls.length === 1 && result.calls[0]?.callId === "new-status",
    "Delayed hydration fixture did not isolate the new call.",
  );
}

function verifyPayloadConflict(): void {
  const original = candidate("plwc_status", "shared-call", "runtime");
  const changed = candidate("plwc_status", "shared-call", "config");
  const gate = new ToolCallObservationGate([original], "c/conflict", 0);
  gate.scan([original], "c/conflict", 1_000);
  const result = gate.scan([original, changed], "c/conflict", 1_100);
  expect(
    result.calls.length === 0 && result.conflicts.length === 1,
    "Payload conflict fixture did not reject the changed call.",
  );
}

function candidate(name: string, callId: string, scope: string): ToolCallTextCandidate {
  return {
    sourceKind: "rendered",
    text: JSON.stringify({
      plwc_tool_call: {
        arguments: { scope },
        call_id: callId,
        name,
      },
    }),
    visible: true,
  };
}

function expectNoCalls(result: ToolCallObservationScan, message: string): void {
  expect(result.calls.length === 0 && result.conflicts.length === 0, message);
}

function expect(condition: boolean, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
