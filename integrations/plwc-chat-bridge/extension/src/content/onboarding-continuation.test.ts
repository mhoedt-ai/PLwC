import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOnboardingContinuation,
  PLWC_ONBOARDING_CONTINUATION_PROTOCOL,
} from "./onboarding-continuation";

const onboardingAnswers = {
  profile_name: "Worker",
  preferred_name: "Mirco",
  role_use_case: "Private assistant",
  tone: "informal",
};

test("turns an approved profile creation plan into one exact Governor apply continuation", () => {
  const sourceArguments = {
    confirmed: false,
    onboarding_answers: onboardingAnswers,
    operation: "plan",
    plan_type: "profile_creation",
    profile: "Worker",
  };

  const continuation = buildOnboardingContinuation(
    {
      arguments: sourceArguments,
      callId: "plwc_governor_profile_creation_plan_001",
      name: "plwc_governor",
    },
    {
      data: {
        approved_for_apply: true,
        confirmed: false,
        decision: "approved_for_apply",
        plan_type: "profile_creation",
      },
      ok: true,
      operation: "plan",
      policy_decision: "ALLOW",
    },
  );

  assert.ok(continuation);
  assert.equal(continuation.protocol, PLWC_ONBOARDING_CONTINUATION_PROTOCOL);
  assert.equal(continuation.state, "awaiting_user_confirmation");
  assert.deepEqual(continuation.next_call, {
    plwc_tool_call: {
      arguments: {
        confirmed: true,
        onboarding_answers: onboardingAnswers,
        operation: "apply",
        plan_type: "profile_creation",
        profile: "Worker",
      },
      call_id: "plwc_governor_profile_creation_plan_001-apply",
      name: "plwc_governor",
    },
  });
  assert.deepEqual(sourceArguments, {
    confirmed: false,
    onboarding_answers: onboardingAnswers,
    operation: "plan",
    plan_type: "profile_creation",
    profile: "Worker",
  });
});

test("does not offer apply for a denied or incomplete profile creation plan", () => {
  const source = {
    arguments: {
      onboarding_answers: onboardingAnswers,
      operation: "plan",
      plan_type: "profile_creation",
      profile: "Worker",
    },
    callId: "plan-denied",
    name: "plwc_governor" as const,
  };

  assert.equal(buildOnboardingContinuation(source, {
    data: { approved_for_apply: false, plan_type: "profile_creation" },
    ok: false,
    operation: "plan",
  }), null);
  assert.equal(buildOnboardingContinuation(source, {
    data: { approved_for_apply: false, plan_type: "profile_creation" },
    ok: true,
    operation: "plan",
  }), null);
});

test("turns a successful profile creation apply into an exact runtime verification call", () => {
  const continuation = buildOnboardingContinuation(
    {
      arguments: {
        confirmed: true,
        onboarding_answers: onboardingAnswers,
        operation: "apply",
        plan_type: "profile_creation",
        profile: "Worker",
      },
      callId: "plwc_governor_profile_creation_plan_001-apply",
      name: "plwc_governor",
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

  assert.ok(continuation);
  assert.equal(continuation.state, "verify_active_profile");
  assert.deepEqual(continuation.next_call, {
    plwc_tool_call: {
      arguments: { scope: "runtime" },
      call_id: "plwc_governor_profile_creation_plan_001-apply-status",
      name: "plwc_status",
    },
  });
});

test("keeps derived continuation call ids within the parser limit", () => {
  const continuation = buildOnboardingContinuation(
    {
      arguments: {
        onboarding_answers: onboardingAnswers,
        operation: "plan",
        plan_type: "profile_creation",
      },
      callId: "x".repeat(256),
      name: "plwc_governor",
    },
    {
      data: { approved_for_apply: true, plan_type: "profile_creation" },
      ok: true,
      operation: "plan",
    },
  );

  assert.ok(continuation);
  assert.equal(continuation.next_call.plwc_tool_call.call_id.length, 256);
  assert.match(continuation.next_call.plwc_tool_call.call_id, /-[0-9a-f]{8}-apply$/u);
});
