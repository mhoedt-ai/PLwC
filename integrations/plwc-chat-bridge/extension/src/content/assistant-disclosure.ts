import { collectChatTurnContainers, resolveChatTurnRole } from "./chat-turn";

const ASSISTANT_REASONING_DISCLOSURE_PATTERN =
  /\b(?:nachgedacht|gedacht|thought|thinking|reasoned|reasoning)\b/iu;

function renderedControlText(control: HTMLElement): string {
  const innerText = (control as HTMLElement & { innerText?: string }).innerText;
  return (typeof innerText === "string" && innerText !== ""
    ? innerText
    : control.textContent ?? "").trim();
}

export function isCollapsedAssistantReasoningLabel(
  text: string,
  ariaExpanded: string | null,
): boolean {
  return ariaExpanded === "false" &&
    ASSISTANT_REASONING_DISCLOSURE_PATTERN.test(text.trim());
}

export function isCollapsedAssistantReasoningControl(
  control: HTMLElement,
): boolean {
  const interactive = control.tagName === "BUTTON" || control.getAttribute("role") === "button";
  return interactive &&
    resolveChatTurnRole(control) === "assistant" &&
    isCollapsedAssistantReasoningLabel(
      renderedControlText(control),
      control.getAttribute("aria-expanded"),
    );
}

export function hasCollapsedAssistantReasoningControl(turn: HTMLElement): boolean {
  return [...turn.querySelectorAll<HTMLElement>("button, [role='button']")]
    .some(isCollapsedAssistantReasoningControl);
}

/**
 * ChatGPT may not mount fenced output produced after reasoning until the
 * reasoning disclosure is opened. Reveal only the newest assistant turn and
 * at most once for that turn. The normal DOM observer then performs the
 * actual tool-call parsing and validation.
 */
export function revealLatestCollapsedAssistantReasoning(
  documentValue: Document,
  revealedTurns: WeakSet<HTMLElement>,
): number {
  const latestTurn = collectChatTurnContainers(documentValue, "assistant").at(-1);
  if (!latestTurn || revealedTurns.has(latestTurn)) return 0;

  let revealed = 0;
  for (const control of latestTurn.querySelectorAll<HTMLElement>("button, [role='button']")) {
    if (!isCollapsedAssistantReasoningControl(control)) continue;
    control.click();
    revealed += 1;
  }
  if (revealed > 0) revealedTurns.add(latestTurn);
  return revealed;
}
