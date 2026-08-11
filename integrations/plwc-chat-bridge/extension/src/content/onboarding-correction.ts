import type { CanonicalToolName, JsonObject } from "../shared/contracts";
import {
  derivePlwcCallId,
  type OnboardingContinuationSourceCall,
} from "./onboarding-continuation";

export const PLWC_TOOL_CALL_CORRECTION_PROTOCOL = "plwc_tool_call_correction.v1" as const;

export interface PlwcToolCallCorrection {
  instruction: string;
  next_call: {
    plwc_tool_call: {
      arguments: JsonObject;
      call_id: string;
      name: CanonicalToolName;
    };
  };
  protocol: typeof PLWC_TOOL_CALL_CORRECTION_PROTOCOL;
  reason: "invalid_onboarding_describe_filter";
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function normalized(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

function hasOnlyKeys(value: Record<string, unknown>, allowed: readonly string[]): boolean {
  const keys = new Set(allowed);
  return Object.keys(value).every((key) => keys.has(key));
}

export function buildOnboardingEntryCorrection(
  source: OnboardingContinuationSourceCall,
  result: unknown,
): PlwcToolCallCorrection | null {
  const resultRecord = record(result);
  const invalidFilter = resultRecord?.ok === false && (
    normalized(resultRecord.operation_filter) === "onboarding" ||
    /operation filtering is supported only/iu.test(String(resultRecord.error ?? ""))
  );
  if (
    source.name !== "plwc_describe" ||
    normalized(source.arguments.scope) !== "status" ||
    normalized(source.arguments.operation) !== "onboarding" ||
    !invalidFilter
  ) {
    return null;
  }

  return {
    instruction:
      "The onboarding entry was requested through an unsupported Describe operation filter. Emit exactly next_call; do not retry onboarding as plwc_describe.",
    next_call: {
      plwc_tool_call: {
        arguments: { scope: "first_run" },
        call_id: derivePlwcCallId(source.callId, "first-run"),
        name: "plwc_status",
      },
    },
    protocol: PLWC_TOOL_CALL_CORRECTION_PROTOCOL,
    reason: "invalid_onboarding_describe_filter",
  };
}

export function isPlwcToolCallCorrection(value: unknown): value is PlwcToolCallCorrection {
  const correction = record(value);
  const nextCall = record(correction?.next_call);
  const wrapper = record(nextCall?.plwc_tool_call);
  const argumentsValue = record(wrapper?.arguments);
  return Boolean(
    correction &&
    nextCall &&
    wrapper &&
    argumentsValue &&
    hasOnlyKeys(correction, ["instruction", "next_call", "protocol", "reason"]) &&
    hasOnlyKeys(nextCall, ["plwc_tool_call"]) &&
    hasOnlyKeys(wrapper, ["arguments", "call_id", "name"]) &&
    correction.protocol === PLWC_TOOL_CALL_CORRECTION_PROTOCOL &&
    correction.reason === "invalid_onboarding_describe_filter" &&
    typeof correction.instruction === "string" &&
    correction.instruction.trim() !== "" &&
    correction.instruction.length <= 1_000 &&
    wrapper.name === "plwc_status" &&
    typeof wrapper.call_id === "string" &&
    wrapper.call_id.length > 0 &&
    wrapper.call_id.length <= 256 &&
    wrapper.call_id.trim() === wrapper.call_id &&
    !/[\u0000-\u001f\u007f]/u.test(wrapper.call_id) &&
    Object.keys(argumentsValue).length === 1 &&
    argumentsValue.scope === "first_run"
  );
}
