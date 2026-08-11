export interface ClipboardTextWriter {
  writeText(text: string): Promise<void>;
}

export async function copyCompleteToolResultMessage(
  message: string,
  clipboard: ClipboardTextWriter | null | undefined = globalThis.navigator?.clipboard,
  documentValue?: Document,
): Promise<void> {
  if (clipboard) {
    try {
      await clipboard.writeText(message);
      return;
    } catch {
      // Continue with the user-gesture copy fallback below.
    }
  }

  const targetDocument = documentValue ?? globalThis.document;
  if (!targetDocument) throw new Error("The complete PLwC result could not be copied.");
  const buffer = targetDocument.createElement("textarea");
  buffer.value = message;
  buffer.setAttribute("aria-hidden", "true");
  buffer.style.position = "fixed";
  buffer.style.left = "-10000px";
  (targetDocument.body ?? targetDocument.documentElement).append(buffer);
  buffer.select();
  const copied = targetDocument.execCommand("copy");
  buffer.remove();
  if (!copied) throw new Error("The complete PLwC result could not be copied.");
}
