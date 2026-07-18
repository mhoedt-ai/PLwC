import type { BridgeSettings } from "./messages";
import type { PolicyDecision } from "./policy";

export function shouldAutoRun(settings: BridgeSettings, policy: PolicyDecision): boolean {
  return settings.readOnlyAutoRun && policy.readOnly && !policy.requiresConfirmation;
}

export function shouldAutoSubmitResult(
  settings: BridgeSettings,
  policy: PolicyDecision,
  confirmed: boolean,
): boolean {
  return settings.autoSubmitResults && (policy.readOnly || confirmed);
}
