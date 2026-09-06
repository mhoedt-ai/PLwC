import type { ToolCallResponse } from "./messages";
import type { PolicyDecision } from "./policy";

interface TransportFailure {
  code: string;
  deliveryState: "not_sent" | "outcome_unknown" | "response_received";
  message: string;
}

export function awaitingConfirmationResponse(policy: PolicyDecision): ToolCallResponse {
  return {
    isError: false,
    policy,
    result: {
      confirmation_required: true,
      ok: false,
      reason: policy.reason,
      state: "awaiting_confirmation",
    },
    state: "awaiting_confirmation",
  };
}

export function outcomeUnknownResponse(
  policy: PolicyDecision,
  failure: TransportFailure,
): ToolCallResponse | null {
  if (policy.readOnly || failure.deliveryState !== "outcome_unknown") return null;
  return {
    isError: true,
    policy,
    result: {
      error_code: failure.code,
      message: failure.message,
      mutation_may_have_executed: true,
      ok: false,
      retry_allowed: false,
      state: "outcome_unknown",
    },
    state: "outcome_unknown",
  };
}
