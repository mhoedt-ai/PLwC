import type { CanonicalToolName, JsonObject } from "../shared/contracts";

export const PLWC_ONBOARDING_CONTINUATION_PROTOCOL =
  "plwc_onboarding_continuation.v1" as const;

export interface OnboardingContinuationSourceCall {
  arguments: Readonly<Record<string, unknown>>;
  callId: string;
  name: CanonicalToolName;
}

export interface PlwcOnboardingContinuation {
  instruction: string;
  next_call: {
    plwc_tool_call: {
      arguments: JsonObject;
      call_id: string;
      name: CanonicalToolName;
    };
  };
  protocol: typeof PLWC_ONBOARDING_CONTINUATION_PROTOCOL;
  state: "awaiting_user_confirmation" | "verify_active_profile";
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function hasOnlyKeys(
  value: Record<string, unknown>,
  allowed: readonly string[],
): boolean {
  const allowedKeys = new Set(allowed);
  return Object.keys(value).every((key) => allowedKeys.has(key));
}

function stringField(value: unknown): string {
  return typeof value === "string" ? value.trim().toLowerCase() : "";
}

export function derivePlwcCallId(callId: string, suffix: string): string {
  const candidate = `${callId}-${suffix}`;
  if (candidate.length <= 256) return candidate;

  let hash = 0x811c9dc5;
  for (const character of callId) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  const digest = hash.toString(16).padStart(8, "0");
  const trailer = `-${digest}-${suffix}`;
  return `${callId.slice(0, 256 - trailer.length)}${trailer}`;
}

function isSuccessfulProfileCreationResult(
  result: unknown,
  operation: "apply" | "plan",
): boolean {
  const resultRecord = record(result);
  const data = record(resultRecord?.data);
  if (
    resultRecord?.ok !== true ||
    stringField(resultRecord.operation) !== operation ||
    stringField(data?.plan_type) !== "profile_creation"
  ) {
    return false;
  }
  if (operation === "plan") {
    return data?.approved_for_apply === true ||
      stringField(data?.decision) === "approved_for_apply";
  }
  return data?.confirmed === true;
}

export function buildOnboardingContinuation(
  source: OnboardingContinuationSourceCall,
  result: unknown,
): PlwcOnboardingContinuation | null {
  if (
    source.name !== "plwc_governor" ||
    stringField(source.arguments.plan_type) !== "profile_creation"
  ) {
    return null;
  }

  const operation = stringField(source.arguments.operation);
  if (operation === "plan" && isSuccessfulProfileCreationResult(result, "plan")) {
    if (!record(source.arguments.onboarding_answers)) return null;
    return {
      instruction:
        "After explicit user confirmation, emit exactly next_call. Preserve its tool name, call_id, and complete arguments; do not route this Governor apply through plwc_describe.",
      next_call: {
        plwc_tool_call: {
          arguments: {
            ...source.arguments,
            confirmed: true,
            operation: "apply",
          },
          call_id: derivePlwcCallId(source.callId, "apply"),
          name: "plwc_governor",
        },
      },
      protocol: PLWC_ONBOARDING_CONTINUATION_PROTOCOL,
      state: "awaiting_user_confirmation",
    };
  }

  if (operation === "apply" && isSuccessfulProfileCreationResult(result, "apply")) {
    return {
      instruction:
        "Emit exactly next_call to verify the governed active profile after the successful onboarding apply.",
      next_call: {
        plwc_tool_call: {
          arguments: { scope: "runtime" },
          call_id: derivePlwcCallId(source.callId, "status"),
          name: "plwc_status",
        },
      },
      protocol: PLWC_ONBOARDING_CONTINUATION_PROTOCOL,
      state: "verify_active_profile",
    };
  }

  return null;
}

export function isPlwcOnboardingContinuation(
  value: unknown,
): value is PlwcOnboardingContinuation {
  const continuation = record(value);
  const nextCall = record(continuation?.next_call);
  const wrapper = record(nextCall?.plwc_tool_call);
  const argumentsValue = record(wrapper?.arguments);
  if (
    !continuation ||
    !nextCall ||
    !wrapper ||
    !hasOnlyKeys(continuation, ["instruction", "next_call", "protocol", "state"]) ||
    !hasOnlyKeys(nextCall, ["plwc_tool_call"]) ||
    !hasOnlyKeys(wrapper, ["arguments", "call_id", "name"]) ||
    continuation?.protocol !== PLWC_ONBOARDING_CONTINUATION_PROTOCOL ||
    !["awaiting_user_confirmation", "verify_active_profile"].includes(
      String(continuation?.state),
    ) ||
    typeof continuation?.instruction !== "string" ||
    continuation.instruction.trim() === "" ||
    continuation.instruction.length > 1_000 ||
    !argumentsValue ||
    typeof wrapper?.call_id !== "string" ||
    wrapper.call_id.length === 0 ||
    wrapper.call_id.length > 256 ||
    wrapper.call_id.trim() !== wrapper.call_id ||
    /[\u0000-\u001f\u007f]/u.test(wrapper.call_id) ||
    !["plwc_governor", "plwc_status"].includes(String(wrapper?.name))
  ) {
    return false;
  }
  if (continuation.state === "awaiting_user_confirmation") {
    return wrapper.name === "plwc_governor" &&
      argumentsValue.operation === "apply" &&
      argumentsValue.plan_type === "profile_creation" &&
      argumentsValue.confirmed === true &&
      record(argumentsValue.onboarding_answers) !== null;
  }
  return wrapper.name === "plwc_status" &&
    Object.keys(argumentsValue).length === 1 &&
    argumentsValue.scope === "runtime";
}
