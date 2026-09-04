export type ChatTurnRole = "assistant" | "user";

const TURN_SELECTOR = "[data-turn]";
const MESSAGE_SELECTOR = "[data-message-author-role]";

function parseChatTurnRole(value: string | null): ChatTurnRole | null {
  return value === "assistant" || value === "user" ? value : null;
}

export function resolveChatTurnRole(element: Element): ChatTurnRole | null {
  const turn = element.closest<HTMLElement>(TURN_SELECTOR);
  const message = element.closest<HTMLElement>(MESSAGE_SELECTOR);
  const turnRole = parseChatTurnRole(turn?.getAttribute("data-turn") ?? null);
  const messageRole = parseChatTurnRole(message?.getAttribute("data-message-author-role") ?? null);

  if (turnRole !== null && messageRole !== null && turnRole !== messageRole) return null;
  return messageRole ?? turnRole;
}

export function closestChatTurnContainer(element: Element): HTMLElement | null {
  const role = resolveChatTurnRole(element);
  if (role === null) return null;

  const turn = element.closest<HTMLElement>(TURN_SELECTOR);
  if (parseChatTurnRole(turn?.getAttribute("data-turn") ?? null) === role) return turn;

  const message = element.closest<HTMLElement>(MESSAGE_SELECTOR);
  return parseChatTurnRole(message?.getAttribute("data-message-author-role") ?? null) === role
    ? message
    : null;
}

export function collectChatTurnContainers(
  documentValue: Document,
  role: ChatTurnRole,
): HTMLElement[] {
  const candidates = documentValue.querySelectorAll<HTMLElement>(
    `[data-turn='${role}'], [data-message-author-role='${role}']`,
  );
  const containers: HTMLElement[] = [];
  const seen = new Set<HTMLElement>();
  for (const candidate of candidates) {
    const container = closestChatTurnContainer(candidate);
    if (container === null || resolveChatTurnRole(container) !== role || seen.has(container)) continue;
    seen.add(container);
    containers.push(container);
  }
  return containers;
}

export function isChatTurnBoundary(element: Element): boolean {
  return parseChatTurnRole(element.getAttribute("data-turn")) !== null ||
    parseChatTurnRole(element.getAttribute("data-message-author-role")) !== null;
}

export function chatTurnIdentity(container: HTMLElement, fallbackIndex: number): string {
  return container.getAttribute("data-turn-id") ??
    container.getAttribute("data-message-id") ??
    container.getAttribute("data-testid") ??
    String(fallbackIndex);
}
