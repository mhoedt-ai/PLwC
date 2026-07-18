import type { BridgeSettings } from "./messages";
import type { PolicyDecision } from "./policy";

export function shouldAutoRun(settings: BridgeSettings, policy: PolicyDecision): boolean {
  if (policy.requiresConfirmation) {
    return settings.autoConfirmWrites && policy.automaticConfirmationAllowed === true;
  }
  return settings.readOnlyAutoRun && policy.readOnly;
}

export function shouldAutoSubmitResult(
  settings: BridgeSettings,
  policy: PolicyDecision,
  confirmed: boolean,
): boolean {
  return settings.autoSubmitResults && (policy.readOnly || confirmed);
}
