import { isRecoverablePlwcChainStall } from "../../src/content/chain-recovery";
import { buildOnboardingContinuation } from "../../src/content/onboarding-continuation";
import { parseVisiblePlwcToolCalls } from "../../src/content/tool-call-parser";
import {
  formatPlwcToolResultMessage,
  parsePlwcToolResultMessage,
} from "../../src/content/tool-result-message";
import { stableStringify } from "../../src/shared/contracts";

const answers = {
  profile_name: "Worker",
  preferred_name: "Mirco",
  role_use_case: "Private assistant",
  tone: "informal",
};

export function runP002Fix01BrowserAcceptance(): void {
  const planSource = {
    arguments: {
      onboarding_answers: answers,
      operation: "plan",
      plan_type: "profile_creation",
      profile: "Worker",
    },
    callId: "browser-profile-plan-001",
    name: "plwc_governor" as const,
  };
  const planResult = {
    data: {
      approved_for_apply: true,
      confirmed: false,
      decision: "approved_for_apply",
      plan_type: "profile_creation",
    },
    ok: true,
    operation: "plan",
    policy_decision: "ALLOW",
  };
  const applyContinuation = buildOnboardingContinuation(planSource, planResult);
  expect(applyContinuation !== null, "Approved plan did not produce an apply continuation.");
  const planMessage = formatPlwcToolResultMessage({
    call_id: planSource.callId,
    continuation: applyContinuation,
    is_error: false,
    name: planSource.name,
    result: planResult,
  });
  expect(
    parsePlwcToolResultMessage(planMessage)?.continuation?.state ===
      "awaiting_user_confirmation",
    "Marked plan result lost its onboarding continuation.",
  );
  const [applyCall] = parseVisiblePlwcToolCalls([{
    conversationId: "c/browser-onboarding",
    sourceKind: "rendered",
    text: stableStringify(applyContinuation.next_call),
    visible: true,
  }]);
  expect(
    applyCall?.name === "plwc_governor" &&
      applyCall.arguments.operation === "apply" &&
      applyCall.arguments.confirmed === true &&
      applyCall.arguments.onboarding_answers !== undefined,
    "The exact plan continuation did not parse as a confirmed Governor apply.",
  );
  expect(
    isRecoverablePlwcChainStall(
      "Ich kann den PLwC-Apply-Schritt hier nicht direkt ausfÃ¼hren. Der nÃ¤chste Schritt ist plwc_governor(operation=apply).",
    ),
    "The observed German execution-refusal response was not recoverable.",
  );

  const statusContinuation = buildOnboardingContinuation(
    {
      arguments: applyCall.arguments,
      callId: applyCall.callId,
      name: applyCall.name,
    },
    {
      data: {
        active_profile_name: "Worker",
        confirmed: true,
        onboarding_complete: true,
        plan_type: "profile_creation",
      },
      ok: true,
      operation: "apply",
      policy_decision: "ALLOW",
    },
  );
  expect(
    statusContinuation?.next_call.plwc_tool_call.name === "plwc_status" &&
      statusContinuation.next_call.plwc_tool_call.arguments.scope === "runtime",
    "Successful apply did not produce the governed runtime verification call.",
  );
}

function expect(condition: boolean, message: string): asserts condition {
  if (!condition) throw new Error(message);
}
