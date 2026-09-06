import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPlwcChainRecoveryMessage,
  ChainRecoveryObservationGate,
  isRecoverableEmptyPlwcChainStall,
  isRecoverablePlwcChainStall,
  isRecoverableStartupPlwcChainStall,
  PLWC_CHAIN_RECOVERY_MESSAGE,
} from "./chain-recovery";
import { buildOnboardingContinuation } from "./onboarding-continuation";
import { buildOnboardingEntryCorrection } from "./onboarding-correction";

test("detects a claimed missing PLwC result when no tool call was emitted", () => {
  assert.equal(
    isRecoverablePlwcChainStall(
      "Das Ergebnis des nächsten Laufs ...-046 ist noch nicht angekommen. Sobald es da ist, geht es weiter.",
    ),
    true,
  );
  assert.equal(
    isRecoverablePlwcChainStall(
      "The PLwC result for plwc-run-indexer-046 has not arrived yet, so I am waiting.",
    ),
    true,
  );
});

test("does not recover summaries or responses that already contain a real call", () => {
  assert.equal(isRecoverablePlwcChainStall("The task is complete; here is the final summary."), false);
  assert.equal(isRecoverablePlwcChainStall("I am waiting for your result, but no PLwC call is involved."), false);
  assert.equal(
    isRecoverablePlwcChainStall([
      "Das Ergebnis steht noch aus.",
      '{"plwc_tool_call":{"arguments":{"scope":"runtime"},"call_id":"plwc-status-047","name":"plwc_status"}}',
    ].join("\n")),
    false,
  );
});

test("recovers the German and English execution-refusal responses from onboarding", () => {
  assert.equal(
    isRecoverablePlwcChainStall(
      "Ich kann den PLwC-Apply-Schritt hier nicht direkt ausfÃ¼hren. Der nÃ¤chste Schritt ist plwc_governor(operation=apply).",
    ),
    true,
  );
  assert.equal(
    isRecoverablePlwcChainStall(
      "I cannot directly execute the PLwC apply call. Use plwc_governor(operation=apply).",
    ),
    true,
  );
});

test("recovers a claimed open call whose PLwC result never existed", () => {
  const text = [
    "Der letzte PLwC-Aufruf plwc-describe-workspace-move-20260809-037 wurde bereits vollständig ausgegeben und ist noch offen.",
    "Ich darf keinen abhängigen Verschiebe-Aufruf erfinden oder überspringen, bevor sein markiertes PLwC Tool Result da ist.",
  ].join(" ");

  assert.equal(isRecoverablePlwcChainStall(text), true);
  assert.equal(
    isRecoverableStartupPlwcChainStall({
      hasPlwcToolCall: false,
      key: "claimed-open-037",
      previousUserText: "bitte weiter machen",
      text,
    }),
    true,
  );
  assert.equal(
    isRecoverableStartupPlwcChainStall({
      hasPlwcToolCall: false,
      key: "claimed-open-unrelated",
      previousUserText: "Erkläre mir den Status.",
      text,
    }),
    false,
  );
});

test("recovers a completely empty assistant turn directly after a PLwC result", () => {
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      key: "empty-after-result",
      previousUserHasPlwcResult: true,
      previousUserText: "# PLwC Tool Result",
      recentUserHasPlwcResult: true,
      text: "",
    }),
    true,
  );
});

test("recovers an empty continuation response while a recent PLwC chain exists", () => {
  for (const previousUserText of [
    "weiter machen",
    "bitte weiter machen mit der monatlichen zusammen fassung",
    "Mach weiter",
    "please continue with the monthly summary",
  ]) {
    assert.equal(
      isRecoverableEmptyPlwcChainStall({
        key: `empty-${previousUserText}`,
        previousUserHasPlwcResult: false,
        previousUserText,
        recentUserHasPlwcResult: true,
        text: "",
      }),
      true,
    );
  }
});

test("does not recover unrelated or nonempty responses as empty chain stalls", () => {
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      hasCollapsedReasoning: true,
      key: "empty-collapsed-reasoning",
      previousUserHasPlwcResult: true,
      previousUserText: "# PLwC Tool Result",
      recentUserHasPlwcResult: true,
      text: "",
    }),
    false,
  );
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      hasPlwcToolCall: true,
      key: "empty-with-call",
      previousUserHasPlwcResult: true,
      previousUserText: "# PLwC Tool Result",
      recentUserHasPlwcResult: true,
      text: "",
    }),
    false,
  );
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      key: "empty-unrelated",
      previousUserText: "Erkläre mir diesen Absatz.",
      recentUserHasPlwcResult: true,
      text: "",
    }),
    false,
  );
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      key: "empty-no-chain",
      previousUserText: "weiter machen",
      recentUserHasPlwcResult: false,
      text: "",
    }),
    false,
  );
  assert.equal(
    isRecoverableEmptyPlwcChainStall({
      key: "summary",
      previousUserHasPlwcResult: true,
      previousUserText: "# PLwC Tool Result",
      recentUserHasPlwcResult: true,
      text: "Die monatliche Zusammenfassung ist fertig.",
    }),
    false,
  );
});

test("recovery message forbids waiting for an unissued call id", () => {
  assert.match(PLWC_CHAIN_RECOVERY_MESSAGE, /no new result can arrive/u);
  assert.match(PLWC_CHAIN_RECOVERY_MESSAGE, /exactly one complete fenced JSON PLwC tool call/u);
  assert.match(PLWC_CHAIN_RECOVERY_MESSAGE, /plwc_tool_call wrapper/u);
  assert.match(PLWC_CHAIN_RECOVERY_MESSAGE, /final summary without a tool call/u);
});

test("recovery message preserves the exact correlated onboarding continuation", () => {
  const continuation = buildOnboardingContinuation(
    {
      arguments: {
        onboarding_answers: { profile_name: "Worker", preferred_name: "Mirco" },
        operation: "plan",
        plan_type: "profile_creation",
        profile: "Worker",
      },
      callId: "profile-plan-001",
      name: "plwc_governor",
    },
    {
      data: { approved_for_apply: true, plan_type: "profile_creation" },
      ok: true,
      operation: "plan",
    },
  );
  assert.ok(continuation);

  const message = buildPlwcChainRecoveryMessage(continuation);
  assert.match(message, /"call_id":"profile-plan-001-apply"/u);
  assert.match(message, /"name":"plwc_governor"/u);
  assert.match(message, /"operation":"apply"/u);
  assert.match(message, /"confirmed":true/u);
  assert.match(message, /Do not replace this Governor call with plwc_describe/u);
});

test("recovery message preserves the exact corrected onboarding entry call", () => {
  const correction = buildOnboardingEntryCorrection(
    {
      arguments: { operation: "onboarding", scope: "status" },
      callId: "onboarding-describe-001",
      name: "plwc_describe",
    },
    {
      error: "operation filtering is supported only for workspace_operation and document_operation scopes",
      ok: false,
      operation_filter: "onboarding",
    },
  );
  assert.ok(correction);

  const message = buildPlwcChainRecoveryMessage(correction);
  assert.match(message, /"name":"plwc_status"/u);
  assert.match(message, /"scope":"first_run"/u);
  assert.match(message, /Emit the exact corrected read-only call now/u);
});

test("does not recover a historical response hydrated after a conversation change", () => {
  const firstOld = { key: "first-old", text: "First chat summary." };
  const firstNew = {
    key: "first-new",
    text: "The PLwC result for plwc-run-047 has not arrived yet.",
  };
  const secondOld = {
    key: "second-old",
    text: "The PLwC result for plwc-run-011 has not arrived yet.",
  };
  const secondHydrated = {
    key: "second-hydrated",
    text: "The PLwC result for plwc-run-012 has not arrived yet.",
  };
  const gate = new ChainRecoveryObservationGate(firstOld, "/c/first", 0);

  assert.equal(gate.scan(firstOld, false, "/c/first", 1_000).responseToInspect, null);
  assert.equal(gate.scan(firstNew, false, "/c/first", 1_100).responseToInspect?.key, "first-new");

  gate.noteMutation(2_000);
  assert.equal(gate.scan(secondOld, false, "/c/second", 2_500).responseToInspect, null);
  gate.noteMutation(2_600);
  assert.equal(
    gate.scan(secondHydrated, false, "/c/second", 3_000).responseToInspect,
    null,
  );
  assert.equal(
    gate.scan(secondHydrated, false, "/c/second", 3_600).responseToInspect,
    null,
  );
});

test("can inspect one narrowly approved empty response after the startup baseline", () => {
  const initialBlank = {
    key: "initial-blank",
    previousUserHasPlwcResult: false,
    previousUserText: "bitte weiter machen",
    recentUserHasPlwcResult: true,
    text: "",
  };
  const gate = new ChainRecoveryObservationGate(
    initialBlank,
    "/c/current",
    0,
    true,
  );

  assert.equal(gate.scan(initialBlank, false, "/c/current", 500).responseToInspect, null);
  assert.equal(
    gate.scan(initialBlank, false, "/c/current", 1_000).responseToInspect?.key,
    "initial-blank",
  );
  assert.equal(gate.scan(initialBlank, false, "/c/current", 1_500).responseToInspect, null);
});

test("detects a recoverable empty response hydrated during the startup baseline", () => {
  const hydratedBlank = {
    key: "hydrated-blank",
    previousUserHasPlwcResult: false,
    previousUserText: "bitte weiter machen",
    recentUserHasPlwcResult: true,
    text: "",
  };
  const gate = new ChainRecoveryObservationGate(
    null,
    "/c/current",
    0,
    false,
    true,
  );

  gate.noteMutation(400);
  assert.equal(gate.scan(hydratedBlank, false, "/c/current", 700).responseToInspect, null);
  assert.equal(
    gate.scan(hydratedBlank, false, "/c/current", 1_400).responseToInspect?.key,
    "hydrated-blank",
  );
  assert.equal(gate.scan(hydratedBlank, false, "/c/current", 1_900).responseToInspect, null);
});
