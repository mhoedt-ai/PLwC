const COMPOSER_SELECTORS = [
  "#prompt-textarea",
  "[data-testid='composer-input']",
  "[data-testid='composer']",
  "form textarea",
  "form [contenteditable]:not([contenteditable='false'])",
  "form [role='textbox']",
  "textarea",
  "[data-lexical-editor='true']",
  "[contenteditable]:not([contenteditable='false'])",
  "[role='textbox']",
];

const EDITABLE_COMPOSER_SELECTOR = [
  "textarea",
  "input",
  "[data-lexical-editor='true']",
  "[contenteditable]:not([contenteditable='false'])",
  "[role='textbox']",
].join(",");

const SEND_BUTTON_TEST_ID_SELECTORS = [
  "button[data-testid='send-button']",
  "button[data-testid='fruitjuice-send-button']",
];

const SEND_BUTTON_LABEL_SELECTORS = [
  "button[aria-label*='Send' i]",
  "button[aria-label*='Senden' i]",
  "button[aria-label*='Übermitteln' i]",
  "button[title*='Send' i]",
  "button[title*='Senden' i]",
  "button[title*='Übermitteln' i]",
];

const SEND_BUTTON_STRUCTURAL_SELECTORS = [
  "button[class*='composer-submit-button']",
  "button[type='submit']",
];

const NON_SEND_COMPOSER_CONTROL_PATTERN =
  /voice|speech|dictat|diktat|microphone|mikrofon|recording|aufnahme|stop|cancel|abbrechen|beenden|generating|generation/i;
const BUSY_COMPOSER_CONTROL_PATTERN =
  /stop|cancel|abbrechen|beenden|generating|generation|antwortgenerierung|streaming|thinking|denkt nach/i;

export type ComposerSubmitResult =
  | "submitted"
  | "chat-not-ready"
  | "composer-not-found"
  | "composer-not-empty"
  | "composer-rejected-insertion"
  | "send-button-not-found"
  | "submission-not-accepted";

export type ComposerInsertionResult =
  | "inserted"
  | "composer-not-found"
  | "composer-rejected-insertion";

export type ComposerSubmitActivation = "form" | "click";

type InsertedComposerSubmitResult = Extract<
  ComposerSubmitResult,
  | "submitted"
  | "composer-rejected-insertion"
  | "send-button-not-found"
  | "submission-not-accepted"
>;

export interface ComposerSubmitOptions {
  autoSubmitDelayMs?: number;
  confirmationAttempts?: number;
  insertionConfirmationAttempts?: number;
  maxSubmitAttempts?: number;
  pollIntervalMs?: number;
  readinessWaitAttempts?: number;
  sendButtonWaitAttempts?: number;
}

export interface ChatGptComposerLock {
  ariaDisabled: string | null;
  composer: HTMLElement;
  contentEditable: string | null;
  disabled?: boolean;
}

interface ComposerSubmissionHooks {
  findSendButton: () => HTMLButtonElement | null;
  isComposerEmpty: () => boolean;
  wait: (milliseconds: number) => Promise<void>;
}

interface ComposerReadinessHooks {
  isChatBusy: () => boolean;
  isComposerEmpty: () => boolean;
  wait: (milliseconds: number) => Promise<void>;
}

interface ComposerInsertionConfirmationHooks {
  hasExpectedText: () => boolean;
  refocus: () => void;
  wait: (milliseconds: number) => Promise<void>;
}

export function findChatGptComposer(documentValue: Document = document): HTMLElement | null {
  for (const selector of COMPOSER_SELECTORS) {
    for (const candidate of documentValue.querySelectorAll(selector)) {
      const composer = resolveComposerCandidate(candidate, documentValue);
      if (composer) return composer;
    }
  }
  return null;
}

export function lockChatGptComposerElement(composer: HTMLElement): ChatGptComposerLock {
  const lock: ChatGptComposerLock = {
    ariaDisabled: composer.getAttribute("aria-disabled"),
    composer,
    contentEditable: composer.getAttribute("contenteditable"),
  };
  if (isTextControl(composer)) {
    const control = composer as HTMLTextAreaElement | HTMLInputElement;
    lock.disabled = control.disabled;
    control.disabled = true;
  } else {
    composer.setAttribute("contenteditable", "false");
  }
  composer.setAttribute("aria-disabled", "true");
  composer.blur();
  return lock;
}

export function unlockChatGptComposerElement(lock: ChatGptComposerLock): void {
  const { composer } = lock;
  if (lock.disabled !== undefined) {
    (composer as HTMLTextAreaElement | HTMLInputElement).disabled = lock.disabled;
  }
  restoreAttribute(composer, "contenteditable", lock.contentEditable);
  restoreAttribute(composer, "aria-disabled", lock.ariaDisabled);
}

export function findChatGptComposerSurface(
  composer: HTMLElement,
  documentValue: Document = document,
): HTMLElement {
  const containmentTolerance = 4;
  const composerRect = composer.getBoundingClientRect();
  let surface = composer;
  let current = composer.parentElement;
  for (let depth = 0; current && depth < 6; depth += 1, current = current.parentElement) {
    const rect = current.getBoundingClientRect();
    const style = documentValue.defaultView?.getComputedStyle(current);
    const radius = Math.max(
      Number.parseFloat(style?.borderTopLeftRadius ?? "0") || 0,
      Number.parseFloat(style?.borderTopRightRadius ?? "0") || 0,
      Number.parseFloat(style?.borderBottomLeftRadius ?? "0") || 0,
      Number.parseFloat(style?.borderBottomRightRadius ?? "0") || 0,
    );
    const containsComposer =
      rect.top <= composerRect.top + containmentTolerance &&
      rect.bottom >= composerRect.bottom - containmentTolerance &&
      rect.left <= composerRect.left + containmentTolerance &&
      rect.right >= composerRect.right - containmentTolerance;
    const plausibleComposerRow =
      containsComposer &&
      rect.height >= 40 &&
      rect.height <= 120 &&
      rect.width >= composerRect.width &&
      rect.width <= composerRect.width + 360;
    if (plausibleComposerRow && radius >= 16) surface = current;
  }
  return surface;
}

export function insertIntoChatGptComposer(text: string, documentValue: Document = document): boolean {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return false;

  const existing = composerText(composer);
  const separator = existing && !existing.endsWith("\n") ? "\n" : "";
  const insertion = `${separator}${text}`;
  composer.focus();
  if (isTextControl(composer)) {
    setNativeTextControlValue(composer, `${existing}${insertion}`);
    composer.setSelectionRange?.(composer.value.length, composer.value.length);
    dispatchInsertionEvent(composer, insertion, documentValue);
  } else if (composer.isContentEditable) {
    placeCaretAtEnd(composer, documentValue);
    const accepted = typeof documentValue.execCommand === "function" &&
      documentValue.execCommand("insertText", false, insertion);
    if (!accepted) {
      composer.textContent = `${existing}${insertion}`;
      dispatchInsertionEvent(composer, insertion, documentValue);
    }
  } else {
    return false;
  }
  return true;
}

export async function confirmChatGptComposerInsertion(
  hooks: ComposerInsertionConfirmationHooks,
  options: ComposerSubmitOptions = {},
): Promise<boolean> {
  if (!hooks.hasExpectedText()) return false;
  hooks.refocus();
  const attempts = Math.max(1, options.insertionConfirmationAttempts ?? 3);
  const pollIntervalMs = options.pollIntervalMs ?? 50;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await hooks.wait(pollIntervalMs);
    if (!hooks.hasExpectedText()) return false;
  }
  return true;
}

export async function insertIntoChatGptComposerVerified(
  text: string,
  documentValue: Document = document,
  options: ComposerSubmitOptions = {},
): Promise<ComposerInsertionResult> {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return "composer-not-found";
  const existing = composerText(composer);
  const expected = `${existing}${existing && !existing.endsWith("\n") ? "\n" : ""}${text}`;
  if (!insertIntoChatGptComposer(text, documentValue)) return "composer-rejected-insertion";

  const accepted = await confirmChatGptComposerInsertion(
    {
      hasExpectedText: () => normalizedComposerText(composerText(composer)) ===
        normalizedComposerText(expected),
      refocus: () => {
        composer.blur();
        composer.focus();
      },
      wait: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
    },
    options,
  );
  return accepted ? "inserted" : "composer-rejected-insertion";
}

export function isChatGptComposerEmpty(documentValue: Document = document): boolean {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return false;
  return composerText(composer).trim() === "";
}

export function findChatGptSendButton(documentValue: Document = document): HTMLButtonElement | null {
  const byTestId = findEnabledButton(documentValue, SEND_BUTTON_TEST_ID_SELECTORS, documentValue);
  if (byTestId) return byTestId;

  const composer = findChatGptComposer(documentValue);
  let scope = composer?.parentElement ?? null;
  for (let depth = 0; scope && depth < 7; depth += 1, scope = scope.parentElement) {
    const byLabel = findEnabledButton(documentValue, SEND_BUTTON_LABEL_SELECTORS, scope);
    if (byLabel) return byLabel;
    const byStructure = findEnabledButton(
      documentValue,
      SEND_BUTTON_STRUCTURAL_SELECTORS,
      scope,
      isChatGptSendButtonCandidate,
    );
    if (byStructure) return byStructure;
  }
  return null;
}

export function isChatGptResponseBusy(documentValue: Document = document): boolean {
  const composer = findChatGptComposer(documentValue);
  let scope: HTMLElement | null = composer?.parentElement ?? documentValue.body;
  for (let depth = 0; scope && depth < 7; depth += 1, scope = scope.parentElement) {
    for (const button of scope.querySelectorAll<HTMLButtonElement>("button")) {
      if (!isVisibleButton(button, documentValue)) continue;
      const descriptor = [
        button.getAttribute("aria-label"),
        button.getAttribute("title"),
        button.getAttribute("data-testid"),
        button.textContent,
      ].filter(Boolean).join(" ");
      if (BUSY_COMPOSER_CONTROL_PATTERN.test(descriptor)) return true;
    }
  }
  return false;
}

export async function waitForChatGptResultInsertionReadiness(
  hooks: ComposerReadinessHooks,
  options: ComposerSubmitOptions = {},
): Promise<Extract<ComposerSubmitResult, "chat-not-ready" | "composer-not-empty" | "submitted">> {
  const pollIntervalMs = options.pollIntervalMs ?? 100;
  const readinessWaitAttempts = options.readinessWaitAttempts ?? 900;
  for (let attempt = 0; attempt < readinessWaitAttempts; attempt += 1) {
    if (!hooks.isComposerEmpty()) return "composer-not-empty";
    if (!hooks.isChatBusy()) return "submitted";
    await hooks.wait(pollIntervalMs);
  }
  return "chat-not-ready";
}

export function isChatGptSendButtonCandidate(candidate: HTMLButtonElement): boolean {
  const descriptor = [
    candidate.getAttribute("aria-label"),
    candidate.getAttribute("title"),
    candidate.getAttribute("data-testid"),
    candidate.textContent,
  ].filter(Boolean).join(" ");
  return !NON_SEND_COMPOSER_CONTROL_PATTERN.test(descriptor);
}

export function activateChatGptSendButton(send: HTMLButtonElement): ComposerSubmitActivation {
  const form = send.form ?? send.closest<HTMLFormElement>("form");
  if (form && send.type === "submit" && typeof form.requestSubmit === "function") {
    try {
      form.requestSubmit(send);
      return "form";
    } catch {
      // Fall through for host forms that reject an isolated-world submitter.
    }
  }
  send.click();
  return "click";
}

export async function submitInsertedChatGptComposer(
  hooks: ComposerSubmissionHooks,
  options: ComposerSubmitOptions = {},
): Promise<InsertedComposerSubmitResult> {
  const pollIntervalMs = options.pollIntervalMs ?? 100;
  const confirmationAttempts = options.confirmationAttempts ?? 25;
  const maxSubmitAttempts = options.maxSubmitAttempts ?? 6;
  const sendButtonWaitAttempts = options.sendButtonWaitAttempts ?? 300;
  const autoSubmitDelayMs = Math.max(0, options.autoSubmitDelayMs ?? 0);
  if (autoSubmitDelayMs > 0) await hooks.wait(autoSubmitDelayMs);

  let sawSendButton = false;
  let submitAttempts = 0;
  for (let waitAttempt = 0; waitAttempt < sendButtonWaitAttempts; waitAttempt += 1) {
    if (hooks.isComposerEmpty()) {
      return submitAttempts > 0 ? "submitted" : "composer-rejected-insertion";
    }
    const send = hooks.findSendButton();
    if (!send) {
      await hooks.wait(pollIntervalMs);
      continue;
    }
    sawSendButton = true;
    if (submitAttempts >= maxSubmitAttempts) break;

    if (submitAttempts % 2 === 0) activateChatGptSendButton(send);
    else send.click();
    submitAttempts += 1;

    for (let confirmationAttempt = 0; confirmationAttempt < confirmationAttempts; confirmationAttempt += 1) {
      await hooks.wait(pollIntervalMs);
      if (hooks.isComposerEmpty()) return "submitted";
    }
  }
  return sawSendButton ? "submission-not-accepted" : "send-button-not-found";
}

function findEnabledButton(
  documentValue: Document,
  selectors: readonly string[],
  scope: ParentNode,
  accept: (candidate: HTMLButtonElement) => boolean = () => true,
): HTMLButtonElement | null {
  for (const selector of selectors) {
    for (const candidate of scope.querySelectorAll<HTMLButtonElement>(selector)) {
      if (!isVisibleButton(candidate, documentValue)) continue;
      if (!accept(candidate)) continue;
      return candidate;
    }
  }
  return null;
}

function isVisibleButton(candidate: HTMLButtonElement, documentValue: Document): boolean {
  if (candidate.disabled || candidate.getAttribute("aria-disabled") === "true") return false;
  const style = documentValue.defaultView?.getComputedStyle(candidate);
  return style?.display !== "none" && style?.visibility !== "hidden";
}

function restoreAttribute(element: HTMLElement, name: string, value: string | null): void {
  if (value === null) element.removeAttribute(name);
  else element.setAttribute(name, value);
}

function composerText(composer: HTMLElement): string {
  if (isTextControl(composer)) return composer.value;
  const innerText = (composer as HTMLElement & { innerText?: string }).innerText;
  return typeof innerText === "string" && innerText !== ""
    ? innerText
    : composer.textContent ?? "";
}

function normalizedComposerText(value: string): string {
  return value.replace(/[\s\u00a0]+/gu, "");
}

function setNativeTextControlValue(
  control: HTMLTextAreaElement | HTMLInputElement,
  value: string,
): void {
  const prototype = control.tagName === "TEXTAREA"
    ? control.ownerDocument?.defaultView?.HTMLTextAreaElement?.prototype
    : control.ownerDocument?.defaultView?.HTMLInputElement?.prototype;
  const setter = prototype
    ? Object.getOwnPropertyDescriptor(prototype, "value")?.set
    : undefined;
  if (setter) setter.call(control, value);
  else control.value = value;
}

function dispatchInsertionEvent(
  composer: HTMLElement,
  text: string,
  documentValue: Document,
): void {
  const InputEventConstructor = documentValue.defaultView?.InputEvent;
  if (InputEventConstructor) {
    composer.dispatchEvent(
      new InputEventConstructor("input", {
        bubbles: true,
        data: text,
        inputType: "insertText",
      }),
    );
    return;
  }
  const EventConstructor = documentValue.defaultView?.Event;
  if (EventConstructor) composer.dispatchEvent(new EventConstructor("input", { bubbles: true }));
}

function placeCaretAtEnd(composer: HTMLElement, documentValue: Document): void {
  const selection = documentValue.getSelection?.();
  if (!selection || typeof documentValue.createRange !== "function") return;
  const range = documentValue.createRange();
  range.selectNodeContents(composer);
  range.collapse(false);
  selection.removeAllRanges();
  selection.addRange(range);
}

function resolveComposerCandidate(candidate: Element, documentValue: Document): HTMLElement | null {
  if (!(candidate instanceof HTMLElement)) return null;
  if (isUsableComposerElement(candidate, documentValue)) return candidate;
  const nested = candidate.querySelector(EDITABLE_COMPOSER_SELECTOR);
  return nested instanceof HTMLElement && isUsableComposerElement(nested, documentValue) ? nested : null;
}

function isUsableComposerElement(candidate: HTMLElement, documentValue: Document): boolean {
  if (closestChatTurnContainer(candidate)) return false;
  if (candidate.getAttribute("aria-disabled") === "true") return false;
  if (!isVisibleComposerElement(candidate, documentValue)) return false;
  if (isTextControl(candidate)) return !candidate.disabled;
  const contentEditable = candidate.getAttribute("contenteditable");
  const editableAttribute = contentEditable !== null && contentEditable.toLowerCase() !== "false";
  return (
    candidate.isContentEditable ||
    editableAttribute ||
    candidate.getAttribute("role") === "textbox" ||
    candidate.getAttribute("data-lexical-editor") === "true"
  );
}

function isTextControl(candidate: HTMLElement): candidate is HTMLTextAreaElement | HTMLInputElement {
  return candidate.tagName === "TEXTAREA" || candidate.tagName === "INPUT";
}

function isVisibleComposerElement(candidate: HTMLElement, documentValue: Document): boolean {
  const style = documentValue.defaultView?.getComputedStyle(candidate);
  return style?.display !== "none" && style?.visibility !== "hidden";
}

/** Insert a bridge result into an empty composer and submit it through ChatGPT's own send control. */
export async function insertAndSubmitToChatGpt(
  text: string,
  documentValue: Document = document,
  options: ComposerSubmitOptions = {},
): Promise<ComposerSubmitResult> {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return "composer-not-found";
  if (!isChatGptComposerEmpty(documentValue)) return "composer-not-empty";
  const readiness = await waitForChatGptResultInsertionReadiness(
    {
      isChatBusy: () => isChatGptResponseBusy(documentValue),
      isComposerEmpty: () => isChatGptComposerEmpty(documentValue),
      wait: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
    },
    options,
  );
  if (readiness !== "submitted") return readiness;
  const insertion = await insertIntoChatGptComposerVerified(text, documentValue, options);
  if (insertion !== "inserted") return insertion;
  return submitInsertedChatGptComposer(
    {
      findSendButton: () => findChatGptSendButton(documentValue),
      isComposerEmpty: () => isChatGptComposerEmpty(documentValue),
      wait: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
    },
    options,
  );
}
import { closestChatTurnContainer } from "./chat-turn";
