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
];

export type ComposerSubmitResult =
  | "submitted"
  | "composer-not-found"
  | "composer-not-empty"
  | "send-button-not-found"
  | "submission-not-accepted";

export function findChatGptComposer(documentValue: Document = document): HTMLElement | null {
  return COMPOSER_SELECTORS.map((selector) => documentValue.querySelector(selector)).find(
    (candidate): candidate is HTMLElement => candidate instanceof HTMLElement,
  ) ?? null;
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
  }
  return null;
}

function findEnabledButton(
  documentValue: Document,
  selectors: readonly string[],
  scope: ParentNode,
): HTMLButtonElement | null {
  for (const selector of selectors) {
    for (const candidate of scope.querySelectorAll<HTMLButtonElement>(selector)) {
      if (candidate.disabled || candidate.getAttribute("aria-disabled") === "true") continue;
      const style = documentValue.defaultView?.getComputedStyle(candidate);
      if (style?.display === "none" || style?.visibility === "hidden") continue;
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
      send.click();
      for (let confirmationAttempt = 0; confirmationAttempt < 15; confirmationAttempt += 1) {
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
