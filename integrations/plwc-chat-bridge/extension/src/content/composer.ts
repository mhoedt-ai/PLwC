const COMPOSER_SELECTORS = [
  "#prompt-textarea",
  "[data-testid='composer-input']",
  "textarea",
  "div[contenteditable='true'][role='textbox']",
  "div[contenteditable='true']",
];

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
  /voice|speech|dictat|diktat|microphone|mikrofon|recording|aufnahme/i;

export type ComposerSubmitResult =
  | "submitted"
  | "composer-not-found"
  | "composer-not-empty"
  | "send-button-not-found"
  | "submission-not-accepted";

export type ComposerSubmitActivation = "form" | "click";

export function findChatGptComposer(documentValue: Document = document): HTMLElement | null {
  return COMPOSER_SELECTORS.map((selector) => documentValue.querySelector(selector)).find(
    (candidate): candidate is HTMLElement => candidate instanceof HTMLElement,
  ) ?? null;
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

  composer.focus();
  if (composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement) {
    const start = composer.selectionStart ?? composer.value.length;
    const end = composer.selectionEnd ?? start;
    const separator = start > 0 && !composer.value.slice(0, start).endsWith("\n") ? "\n" : "";
    composer.setRangeText(`${separator}${text}`, start, end, "end");
  } else if (composer.isContentEditable) {
    const existing = composer.textContent ?? "";
    composer.textContent = `${existing}${existing && !existing.endsWith("\n") ? "\n" : ""}${text}`;
  } else {
    return false;
  }

  composer.dispatchEvent(
    new InputEvent("input", { bubbles: true, data: text, inputType: "insertText" }),
  );
  return true;
}

export function isChatGptComposerEmpty(documentValue: Document = document): boolean {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return false;
  const value = composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement
    ? composer.value
    : composer.textContent ?? "";
  return value.trim() === "";
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

function findEnabledButton(
  documentValue: Document,
  selectors: readonly string[],
  scope: ParentNode,
  accept: (candidate: HTMLButtonElement) => boolean = () => true,
): HTMLButtonElement | null {
  for (const selector of selectors) {
    for (const candidate of scope.querySelectorAll<HTMLButtonElement>(selector)) {
      if (candidate.disabled || candidate.getAttribute("aria-disabled") === "true") continue;
      const style = documentValue.defaultView?.getComputedStyle(candidate);
      if (style?.display === "none" || style?.visibility === "hidden") continue;
      if (!accept(candidate)) continue;
      return candidate;
    }
  }
  return null;
}

/** Insert a bridge result into an empty composer and submit it through ChatGPT's own send control. */
export async function insertAndSubmitToChatGpt(
  text: string,
  documentValue: Document = document,
): Promise<ComposerSubmitResult> {
  const composer = findChatGptComposer(documentValue);
  if (!composer) return "composer-not-found";
  if (!isChatGptComposerEmpty(documentValue)) return "composer-not-empty";
  if (!insertIntoChatGptComposer(text, documentValue)) return "composer-not-found";

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const send = findChatGptSendButton(documentValue);
    if (send) {
      activateChatGptSendButton(send);
      for (let confirmationAttempt = 0; confirmationAttempt < 25; confirmationAttempt += 1) {
        if (
          isChatGptComposerEmpty(documentValue) ||
          send.disabled ||
          send.getAttribute("aria-disabled") === "true"
        ) {
          return "submitted";
        }
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      return "submission-not-accepted";
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return "send-button-not-found";
}
