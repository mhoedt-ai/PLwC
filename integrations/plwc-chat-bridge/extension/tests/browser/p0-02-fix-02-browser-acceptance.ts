import { insertIntoChatGptComposerVerified } from "../../src/content/composer";
import { buildOnboardingEntryCorrection } from "../../src/content/onboarding-correction";
import {
  formatPlwcToolResultMessage,
  parsePlwcToolResultMessage,
} from "../../src/content/tool-result-message";
import { presentToolResult } from "../../src/shared/tool-result";

export async function runP002Fix02BrowserAcceptance(
  documentValue?: Document,
): Promise<void> {
  const correction = buildOnboardingEntryCorrection(
    {
      arguments: { operation: "onboarding", scope: "status" },
      callId: "browser-onboarding-describe-001",
      name: "plwc_describe",
    },
    {
      error: "operation filtering is supported only for workspace_operation and document_operation scopes",
      ok: false,
      operation_filter: "onboarding",
    },
  );
  expect(
    correction?.next_call.plwc_tool_call.name === "plwc_status" &&
      correction.next_call.plwc_tool_call.arguments.scope === "first_run",
    "Invalid onboarding Describe did not produce the exact first-run status correction.",
  );
  const correctionMessage = formatPlwcToolResultMessage({
    call_id: "browser-onboarding-describe-001",
    correction,
    is_error: true,
    name: "plwc_describe",
    result: { ok: false, operation_filter: "onboarding" },
  });
  expect(
    parsePlwcToolResultMessage(correctionMessage)?.correction?.reason ===
      "invalid_onboarding_describe_filter",
    "The marked result lost its exact onboarding entry correction.",
  );

  const original = {
    ok: true,
    payload: Array.from({ length: 900 }, (_, index) => `browser-result-${index}-${"x".repeat(60)}`),
    scope: "first_run",
  };
  const message = formatPlwcToolResultMessage({
    call_id: "browser-first-run-large-001",
    is_error: false,
    name: "plwc_status",
    result: presentToolResult("plwc_status", original),
  });
  expect(parsePlwcToolResultMessage(message) !== null, "The complete fallback message did not parse.");
  expect(message.length > 12_000, "The fallback scenario was not large enough to detect truncation.");
  expect(message.includes("browser-result-899"), "The complete fallback lost the final result chunk.");
  expect(
    !message.includes("output truncated by PLwC Chat Bridge"),
    "The complete fallback used the bounded panel preview.",
  );

  if (!documentValue) return;
  const composer = documentValue.querySelector<HTMLElement>("#prompt-textarea");
  try {
    const insertion = await insertIntoChatGptComposerVerified(message, documentValue, {
      insertionConfirmationAttempts: 2,
      pollIntervalMs: 0,
    });
    expect(insertion === "inserted", `Browser composer rejected the verified insertion: ${insertion}.`);
    expect(
      (composer?.innerText ?? composer?.textContent ?? "").includes("browser-result-899"),
      "The browser composer did not retain the complete result after refocus.",
    );
  } finally {
    if (composer) composer.textContent = "";
  }
}

function expect(condition: boolean, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
