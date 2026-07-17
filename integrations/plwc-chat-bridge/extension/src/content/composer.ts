const COMPOSER_SELECTORS = [
  "#prompt-textarea",
  "[data-testid='composer-input']",
  "textarea",
  "div[contenteditable='true'][role='textbox']",
  "div[contenteditable='true']",
];

export function insertIntoChatGptComposer(text: string, documentValue: Document = document): boolean {
  const composer = COMPOSER_SELECTORS.map((selector) => documentValue.querySelector(selector)).find(
    (candidate): candidate is HTMLElement => candidate instanceof HTMLElement,
  );
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
