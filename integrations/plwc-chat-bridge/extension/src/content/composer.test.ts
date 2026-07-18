import assert from "node:assert/strict";
import test from "node:test";

import {
  activateChatGptSendButton,
  findChatGptComposerSurface,
  isChatGptSendButtonCandidate,
  submitInsertedChatGptComposer,
} from "./composer";

type Rect = Pick<DOMRect, "bottom" | "height" | "left" | "right" | "top" | "width">;

function mockElement(rect: Rect, parentElement: HTMLElement | null = null): HTMLElement {
  return {
    getBoundingClientRect: () => rect as DOMRect,
    parentElement,
  } as unknown as HTMLElement;
}

test("uses the rounded composer shell for vertical launcher alignment", () => {
  const outer = mockElement({ bottom: 980, height: 80, left: 600, right: 1_500, top: 900, width: 900 });
  const shell = mockElement(
    { bottom: 965.6, height: 52, left: 666, right: 1_434, top: 913.6, width: 768 },
    outer,
  );
  const editorRow = mockElement(
    { bottom: 969, height: 59, left: 710, right: 1_257, top: 910, width: 547 },
    shell,
  );
  const composer = mockElement(
    { bottom: 968, height: 42, left: 717, right: 1_251, top: 926, width: 534 },
    editorRow,
  );
  const radii = new Map<HTMLElement, string>([
    [outer, "28px"],
    [shell, "28px"],
  ]);
  const documentValue = {
    defaultView: {
      getComputedStyle: (element: HTMLElement) => {
        const radius = radii.get(element) ?? "0px";
        return {
          borderBottomLeftRadius: radius,
          borderBottomRightRadius: radius,
          borderTopLeftRadius: radius,
          borderTopRightRadius: radius,
        } as CSSStyleDeclaration;
      },
    },
  } as unknown as Document;

  assert.equal(findChatGptComposerSurface(composer, documentValue), shell);
});

function mockButton(label: string | null): HTMLButtonElement {
  return {
    getAttribute: (name: string) => name === "aria-label" ? label : null,
    textContent: "",
  } as unknown as HTMLButtonElement;
}

test("accepts the current localized composer submit control", () => {
  assert.equal(isChatGptSendButtonCandidate(mockButton("Nachricht übermitteln")), true);
  assert.equal(isChatGptSendButtonCandidate(mockButton("Send message")), true);
});

test("does not mistake the shared composer voice control for submit", () => {
  assert.equal(isChatGptSendButtonCandidate(mockButton("Voice starten")), false);
  assert.equal(isChatGptSendButtonCandidate(mockButton("Diktat starten")), false);
  assert.equal(isChatGptSendButtonCandidate(mockButton("Antwortgenerierung beenden")), false);
});

test("submits through the owning ChatGPT form with the active button", () => {
  let requestedWith: HTMLButtonElement | null = null;
  let clicks = 0;
  const form = {
    requestSubmit: (button: HTMLButtonElement) => {
      requestedWith = button;
    },
  } as unknown as HTMLFormElement;
  const send = {
    click: () => { clicks += 1; },
    closest: () => form,
    form,
    type: "submit",
  } as unknown as HTMLButtonElement;

  assert.equal(activateChatGptSendButton(send), "form");
  assert.equal(requestedWith, send);
  assert.equal(clicks, 0);
});

test("falls back to a direct click outside a submit form", () => {
  let clicks = 0;
  const send = {
    click: () => { clicks += 1; },
    closest: () => null,
    form: null,
    type: "button",
  } as unknown as HTMLButtonElement;

  assert.equal(activateChatGptSendButton(send), "click");
  assert.equal(clicks, 1);
});

test("retries a rejected native submit with a direct click", async () => {
  let composerEmpty = false;
  let nativeSubmits = 0;
  let clicks = 0;
  const form = {
    requestSubmit: () => { nativeSubmits += 1; },
  } as unknown as HTMLFormElement;
  const send = {
    click: () => {
      clicks += 1;
      composerEmpty = true;
    },
    closest: () => form,
    form,
    type: "submit",
  } as unknown as HTMLButtonElement;

  const result = await submitInsertedChatGptComposer(
    {
      findSendButton: () => send,
      isComposerEmpty: () => composerEmpty,
      wait: async () => undefined,
    },
    { confirmationAttempts: 1, maxSubmitAttempts: 2, pollIntervalMs: 0 },
  );

  assert.equal(result, "submitted");
  assert.equal(nativeSubmits, 1);
  assert.equal(clicks, 1);
});

test("reports a missing submit control only after the configured wait", async () => {
  let waits = 0;
  const result = await submitInsertedChatGptComposer(
    {
      findSendButton: () => null,
      isComposerEmpty: () => false,
      wait: async () => { waits += 1; },
    },
    { pollIntervalMs: 0, sendButtonWaitAttempts: 3 },
  );

  assert.equal(result, "send-button-not-found");
  assert.equal(waits, 3);
});
