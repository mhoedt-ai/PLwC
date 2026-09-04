const CHAT_RENDERED_JSON_WHITESPACE = /[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]/u;

/**
 * Chat renderers can replace indentation with Unicode spacing characters that
 * JSON does not accept as whitespace. Normalize only outside JSON strings so
 * user and tool content remains byte-for-byte unchanged.
 */
export function normalizeChatRenderedJsonWhitespace(text: string): string {
  let normalized = "";
  let inString = false;
  let escaped = false;

  for (const character of text) {
    if (inString) {
      normalized += character;
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === '"') {
        inString = false;
      }
      continue;
    }

    if (character === '"') {
      inString = true;
      normalized += character;
      continue;
    }

    normalized += CHAT_RENDERED_JSON_WHITESPACE.test(character) ? " " : character;
  }

  return normalized;
}
