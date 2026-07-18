import type { BridgeSettings } from "./messages";
import type { PolicyDecision } from "./policy";

export interface AutomaticRunOutcome {
  completed: boolean;
  sourceId?: string;
}

export class AutomaticRunQueue {
  private tail: Promise<AutomaticRunOutcome | null> = Promise.resolve(null);

  enqueue(
    sourceId: string | undefined,
    run: () => Promise<boolean>,
    onPaused: () => void,
  ): Promise<AutomaticRunOutcome> {
    const next = this.tail
      .catch(() => null)
      .then(async (previous): Promise<AutomaticRunOutcome> => {
        if (sourceId && previous?.sourceId === sourceId && !previous.completed) {
          onPaused();
          return previous;
        }
        const completed = await run();
        return { completed, ...(sourceId === undefined ? {} : { sourceId }) };
      });
    this.tail = next;
    return next;
  }
}

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
