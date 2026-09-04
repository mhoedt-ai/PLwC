import assert from "node:assert/strict";
import test from "node:test";

import {
  isCollapsedAssistantReasoningLabel,
  revealLatestCollapsedAssistantReasoning,
} from "./assistant-disclosure";

class TestElement {
  readonly children: TestElement[] = [];
  clickCount = 0;
  parentElement: TestElement | null = null;

  constructor(
    readonly tagName: string,
    readonly textContent: string,
    private readonly attributes = new Map<string, string>(),
  ) {}

  append(child: TestElement): void {
    child.parentElement = this;
    this.children.push(child);
  }

  click(): void {
    this.clickCount += 1;
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

  querySelectorAll(selector: string): TestElement[] {
    if (selector !== "button, [role='button']") return [];
    return this.children.filter((child) =>
      child.tagName === "BUTTON" || child.getAttribute("role") === "button"
    );
  }
}

test("recognizes collapsed German and English reasoning disclosures", () => {
  for (const label of [
    "11s nachgedacht",
    "12 Sekunden nachgedacht",
    "Thought for 9s",
    "Thinking for 3 seconds",
    "Reasoned for 7s",
  ]) {
    assert.equal(isCollapsedAssistantReasoningLabel(label, "false"), true, label);
  }
});

test("does not reopen expanded or unrelated controls", () => {
  assert.equal(isCollapsedAssistantReasoningLabel("11s nachgedacht", "true"), false);
  assert.equal(isCollapsedAssistantReasoningLabel("11s nachgedacht", null), false);
  assert.equal(isCollapsedAssistantReasoningLabel("Mehr anzeigen", "false"), false);
  assert.equal(isCollapsedAssistantReasoningLabel("Antwort kopieren", null), false);
});

test("reveals a collapsed reasoning turn only once", () => {
  const turn = new TestElement(
    "SECTION",
    "",
    new Map([["data-turn", "assistant"]]),
  );
  const reasoning = new TestElement(
    "BUTTON",
    "11s nachgedacht",
    new Map([["aria-expanded", "false"]]),
  );
  turn.append(reasoning);
  const documentValue = {
    querySelectorAll: () => [turn],
  } as unknown as Document;
  const revealedTurns = new WeakSet<HTMLElement>();

  assert.equal(
    revealLatestCollapsedAssistantReasoning(documentValue, revealedTurns),
    1,
  );
  assert.equal(reasoning.clickCount, 1);
  assert.equal(
    revealLatestCollapsedAssistantReasoning(documentValue, revealedTurns),
    0,
  );
  assert.equal(reasoning.clickCount, 1);
});
