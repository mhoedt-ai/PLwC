import { isChatGptResponseBusy } from "./composer";
import type { PlwcOnboardingContinuation } from "./onboarding-continuation";
import type { PlwcToolCallCorrection } from "./onboarding-correction";
import { stableStringify } from "../shared/contracts";
import { chatTurnIdentity, collectChatTurnContainers } from "./chat-turn";
import { PLWC_TOOL_RESULT_MARKER } from "./tool-result-message";
import { hasCollapsedAssistantReasoningControl } from "./assistant-disclosure";

const MISSING_RESULT_PATTERN =
  /(?:ergebnis|result|tool[- ]?result)[\s\S]{0,220}(?:noch nicht (?:angekommen|eingetroffen|da)|nicht (?:angekommen|eingetroffen)|ausstehend|fehlt|has not (?:arrived|been received)|not (?:arrived|received)|pending)/iu;
const WAITING_FOR_RESULT_PATTERN =
  /(?:warte|warten|waiting)[\s\S]{0,160}(?:ergebnis|result|tool[- ]?result)/iu;
const PLWC_CALL_REFERENCE_PATTERN =
  /(?:plwc(?:[_-][A-Za-z0-9]+){1,16}|\.\.\.-\d{2,})/u;
const EXECUTION_REFUSAL_PATTERN =
  /(?:(?:ich\s+kann|kann\s+ich)[\s\S]{0,180}(?:nicht\s+(?:direkt\s+)?(?:ausf(?:Ã¼|ue)hren|aufrufen|starten))|(?:i\s+(?:cannot|can't)|unable\s+to)[\s\S]{0,180}(?:execute|call|run))/iu;
const CLAIMED_OPEN_CALL_PATTERN =
  /(?:aufruf|call)[\s\S]{0,260}(?:(?:noch|still)\s+)?(?:offen|open|pending)[\s\S]{0,320}(?:ergebnis|result)/iu;
const CONTEXT_BASELINE_IDLE_MS = 1_000;
const CONTEXT_BASELINE_MAX_MS = 12_000;
const SCAN_DELAY_MS = 500;
const RECONCILIATION_INTERVAL_MS = 1_500;
const RECENT_PLWC_RESULT_USER_TURNS = 8;
const CONTINUE_CHAIN_PATTERN =
  /^(?=.{1,320}$)(?:(?:bitte\s+)?(?:weiter(?:\s+machen)?|mach(?:e)?\s+weiter|fortsetzen)|(?:please\s+)?continue)\b/iu;

const PLWC_CHAIN_RECOVERY_LINES = [
  "# PLwC Chain Recovery",
  "No executable PLwC tool call was present in your last response, so no new result can arrive.",
  "Do not invent, skip, or wait for an unissued call_id.",
  "If work remains, emit exactly one complete fenced JSON PLwC tool call using the plwc_tool_call wrapper and a new unique call_id, then wait for its matching PLwC Tool Result.",
  "If the task is complete, provide the final summary without a tool call.",
];

export function buildPlwcChainRecoveryMessage(
  guidance?: PlwcOnboardingContinuation | PlwcToolCallCorrection | null,
): string {
  const lines = [...PLWC_CHAIN_RECOVERY_LINES];
  if (guidance) {
    lines.push(
      "The latest verified PLwC result supplied this exact next-call contract:",
      stableStringify(guidance.next_call),
    );
    if ("reason" in guidance) {
      lines.push(
        guidance.instruction,
        "Emit the exact corrected read-only call now.",
      );
    } else if (guidance.state === "awaiting_user_confirmation") {
      lines.push(
        "If the user's latest message explicitly confirms the reviewed plan, emit that exact call now; otherwise ask for confirmation.",
        "Do not replace this Governor call with plwc_describe and do not omit the onboarding_answers.",
      );
    } else {
      lines.push("Emit that exact read-only runtime verification call now.");
    }
  }
  return lines.join("\n");
}

export const PLWC_CHAIN_RECOVERY_MESSAGE = buildPlwcChainRecoveryMessage();

export function isRecoverablePlwcChainStall(text: string): boolean {
  if (text.includes("plwc_tool_call")) return false;
  if (!PLWC_CALL_REFERENCE_PATTERN.test(text)) return false;
  return MISSING_RESULT_PATTERN.test(text) ||
    WAITING_FOR_RESULT_PATTERN.test(text) ||
    EXECUTION_REFUSAL_PATTERN.test(text) ||
    CLAIMED_OPEN_CALL_PATTERN.test(text);
}

export interface AssistantResponseSnapshot {
  hasCollapsedReasoning?: boolean;
  hasPlwcToolCall?: boolean;
  key: string;
  previousUserHasPlwcResult?: boolean;
  previousUserText?: string;
  recentUserHasPlwcResult?: boolean;
  text: string;
}

export function isRecoverableEmptyPlwcChainStall(
  response: AssistantResponseSnapshot,
): boolean {
  if (response.text.trim() !== "") return false;
  if (response.hasCollapsedReasoning === true) return false;
  if (response.hasPlwcToolCall === true) return false;
  if (response.previousUserHasPlwcResult === true) return true;
  if (response.recentUserHasPlwcResult !== true) return false;
  return CONTINUE_CHAIN_PATTERN.test(response.previousUserText?.trim() ?? "");
}

export function isRecoverableStartupPlwcChainStall(
  response: AssistantResponseSnapshot,
): boolean {
  if (isRecoverableEmptyPlwcChainStall(response)) return true;
  if (response.hasCollapsedReasoning === true) return false;
  if (response.hasPlwcToolCall === true) return false;
  if (!CONTINUE_CHAIN_PATTERN.test(response.previousUserText?.trim() ?? "")) return false;
  return isRecoverablePlwcChainStall(response.text);
}

function chatContextKey(documentValue: Document): string {
  const locationValue = documentValue.defaultView?.location;
  if (!locationValue) return documentValue.URL || "unknown-document";
  return `${locationValue.pathname}${locationValue.search}`;
}

function renderedTurnText(turn: HTMLElement): string {
  const innerText = (turn as HTMLElement & { innerText?: string }).innerText;
  return (typeof innerText === "string" ? innerText : turn.textContent ?? "").trim();
}

function latestAssistantResponse(documentValue: Document): AssistantResponseSnapshot | null {
  const responses = collectChatTurnContainers(documentValue, "assistant");
  const response = responses.at(-1);
  if (!response) return null;
  const userTurns = collectChatTurnContainers(documentValue, "user");
  const previousUser = userTurns.at(-1);
  const previousUserText = previousUser ? renderedTurnText(previousUser) : "";
  const hasPlwcResult = (turn: HTMLElement): boolean => {
    const text = turn.textContent ?? "";
    return turn.querySelector('[data-plwc-chat-card-kind="result"]') !== null ||
      text.includes(PLWC_TOOL_RESULT_MARKER);
  };
  const text = renderedTurnText(response);
  const identity = chatTurnIdentity(response, responses.length - 1);
  const hasRawToolCall = [...response.querySelectorAll<HTMLElement>("pre, code")]
    .some((element) => (element.textContent ?? "").includes("plwc_tool_call"));
  return {
    hasCollapsedReasoning: hasCollapsedAssistantReasoningControl(response),
    hasPlwcToolCall:
      response.querySelector('[data-plwc-chat-card-kind="call"]') !== null || hasRawToolCall,
    key: identity,
    previousUserHasPlwcResult: previousUser ? hasPlwcResult(previousUser) : false,
    previousUserText,
    recentUserHasPlwcResult: userTurns
      .slice(-RECENT_PLWC_RESULT_USER_TURNS)
      .some(hasPlwcResult),
    text,
  };
}

export interface ChainRecoveryObservationScan {
  responseToInspect: AssistantResponseSnapshot | null;
  rescanAfterMs: number | null;
}

export class ChainRecoveryObservationGate {
  private contextKey: string;
  private lastResponseKey: string;
  private baselineStartedAt: number;
  private lastMutationAt: number;
  private recordingContextBaseline = true;
  private inspectInitialResponseAfterBaseline: boolean;
  private inspectRecoverableStartupBaselineResponses: boolean;

  constructor(
    initialResponse: AssistantResponseSnapshot | null,
    contextKey: string,
    now = Date.now(),
    inspectInitialResponseAfterBaseline = false,
    inspectRecoverableStartupBaselineResponses = false,
  ) {
    this.contextKey = contextKey;
    this.lastResponseKey = initialResponse?.key ?? "";
    this.baselineStartedAt = now;
    this.lastMutationAt = now;
    this.inspectInitialResponseAfterBaseline = inspectInitialResponseAfterBaseline;
    this.inspectRecoverableStartupBaselineResponses = inspectRecoverableStartupBaselineResponses;
  }

  noteMutation(now = Date.now()): void {
    this.lastMutationAt = now;
  }

  scan(
    response: AssistantResponseSnapshot | null,
    responseBusy: boolean,
    contextKey: string,
    now = Date.now(),
  ): ChainRecoveryObservationScan {
    if (contextKey !== this.contextKey) {
      this.contextKey = contextKey;
      this.lastResponseKey = response?.key ?? "";
      this.baselineStartedAt = now;
      this.lastMutationAt = now;
      this.recordingContextBaseline = true;
      this.inspectInitialResponseAfterBaseline = false;
      this.inspectRecoverableStartupBaselineResponses = false;
      return { responseToInspect: null, rescanAfterMs: CONTEXT_BASELINE_IDLE_MS };
    }

    if (this.recordingContextBaseline) {
      this.lastResponseKey = response?.key ?? "";
      if (this.inspectRecoverableStartupBaselineResponses) {
        this.inspectInitialResponseAfterBaseline = response !== null &&
          isRecoverableStartupPlwcChainStall(response);
      }
      if (responseBusy) {
        return { responseToInspect: null, rescanAfterMs: SCAN_DELAY_MS };
      }

      const idleFor = now - this.lastMutationAt;
      const baseliningFor = now - this.baselineStartedAt;
      if (idleFor < CONTEXT_BASELINE_IDLE_MS && baseliningFor < CONTEXT_BASELINE_MAX_MS) {
        return {
          responseToInspect: null,
          rescanAfterMs: Math.min(
            CONTEXT_BASELINE_IDLE_MS - idleFor,
            CONTEXT_BASELINE_MAX_MS - baseliningFor,
          ),
        };
      }

      this.recordingContextBaseline = false;
      const responseToInspect = this.inspectInitialResponseAfterBaseline ? response : null;
      this.inspectInitialResponseAfterBaseline = false;
      this.inspectRecoverableStartupBaselineResponses = false;
      return { responseToInspect, rescanAfterMs: null };
    }

    if (responseBusy) {
      return { responseToInspect: null, rescanAfterMs: SCAN_DELAY_MS };
    }
    if (!response || response.key === this.lastResponseKey) {
      return { responseToInspect: null, rescanAfterMs: null };
    }

    this.lastResponseKey = response.key;
    return { responseToInspect: response, rescanAfterMs: null };
  }
}

export function observePlwcChainStalls(
  onStall: () => void | Promise<void>,
  documentValue: Document = document,
): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const initialResponse = latestAssistantResponse(documentValue);
  const gate = new ChainRecoveryObservationGate(
    initialResponse,
    chatContextKey(documentValue),
    Date.now(),
    initialResponse !== null && isRecoverableStartupPlwcChainStall(initialResponse),
    true,
  );

  const scan = () => {
    timer = null;
    const response = latestAssistantResponse(documentValue);
    const result = gate.scan(
      response,
      isChatGptResponseBusy(documentValue),
      chatContextKey(documentValue),
    );
    if (
      result.responseToInspect &&
      (
        isRecoverablePlwcChainStall(result.responseToInspect.text) ||
        isRecoverableEmptyPlwcChainStall(result.responseToInspect)
      )
    ) {
      void onStall();
    }
    timer = setTimeout(
      scan,
      result.rescanAfterMs ?? RECONCILIATION_INTERVAL_MS,
    );
  };
  const schedule = () => {
    gate.noteMutation();
    if (timer) clearTimeout(timer);
    timer = setTimeout(scan, SCAN_DELAY_MS);
  };
  const observer = new MutationObserver(schedule);
  observer.observe(documentValue.body ?? documentValue.documentElement, {
    attributes: true,
    attributeFilter: ["aria-expanded", "data-message-author-role", "data-turn"],
    childList: true,
    characterData: true,
    subtree: true,
  });
  return () => {
    observer.disconnect();
    if (timer) clearTimeout(timer);
  };
}
