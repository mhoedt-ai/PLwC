import assert from "node:assert/strict";
import test from "node:test";

import {
  chatTurnIdentity,
  closestChatTurnContainer,
  collectChatTurnContainers,
  isChatTurnBoundary,
  resolveChatTurnRole,
} from "./chat-turn";

class TestElement {
  readonly children: TestElement[] = [];
  parentElement: TestElement | null = null;

  constructor(private readonly attributes = new Map<string, string>()) {}

  append(child: TestElement): void {
    child.parentElement = this;
    this.children.push(child);
  }

  closest(selector: string): TestElement | null {
    let current: TestElement | null = this;
    while (current) {
      if (selector === "[data-turn]" && current.getAttribute("data-turn") !== null) return current;
      if (
        selector === "[data-message-author-role]" &&
        current.getAttribute("data-message-author-role") !== null
      ) {
        return current;
      }
      current = current.parentElement;
    }
    return null;
  }

  getAttribute(name: string): string | null {
    return this.attributes.get(name) ?? null;
  }
}

function asElement(value: TestElement): Element {
  return value as unknown as Element;
}

function asHtmlElement(value: TestElement): HTMLElement {
  return value as unknown as HTMLElement;
}

test("resolves content from the current outer ChatGPT turn", () => {
  const turn = new TestElement(new Map([
    ["data-turn", "assistant"],
    ["data-turn-id", "request-live-1"],
    ["data-testid", "conversation-turn-88"],
  ]));
  const roleMarker = new TestElement(new Map([["data-message-author-role", "assistant"]]));
  const renderedContent = new TestElement();
  turn.append(roleMarker);
  turn.append(renderedContent);

  assert.equal(resolveChatTurnRole(asElement(renderedContent)), "assistant");
  assert.equal(closestChatTurnContainer(asElement(renderedContent)), asHtmlElement(turn));
  assert.equal(chatTurnIdentity(asHtmlElement(turn), 0), "request-live-1");
  assert.equal(isChatTurnBoundary(asElement(turn)), true);
});

test("fails closed when nested and outer ChatGPT roles disagree", () => {
  const turn = new TestElement(new Map([["data-turn", "assistant"]]));
  const conflictingMessage = new TestElement(new Map([["data-message-author-role", "user"]]));
  const code = new TestElement();
  turn.append(conflictingMessage);
  conflictingMessage.append(code);

  assert.equal(resolveChatTurnRole(asElement(code)), null);
  assert.equal(closestChatTurnContainer(asElement(code)), null);
});

test("collects each current or legacy turn exactly once", () => {
  const currentTurn = new TestElement(new Map([["data-turn", "assistant"]]));
  const currentMarker = new TestElement(new Map([["data-message-author-role", "assistant"]]));
  currentTurn.append(currentMarker);
  const legacyMessage = new TestElement(new Map([["data-message-author-role", "assistant"]]));
  const candidates = [currentTurn, currentMarker, legacyMessage];
  const documentValue = {
    querySelectorAll: () => candidates,
  } as unknown as Document;

  assert.deepEqual(
    collectChatTurnContainers(documentValue, "assistant"),
    [asHtmlElement(currentTurn), asHtmlElement(legacyMessage)],
  );
});
