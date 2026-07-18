import {
  parseVisiblePlwcToolCalls,
  type ParsedPlwcToolCall,
  type ToolCallTextCandidate,
} from "./tool-call-parser";

const MAX_CANDIDATES = 240;
const MAX_CANDIDATE_CHARACTERS = 160_000;

function isVisible(element: HTMLElement): boolean {
  const rect = element.getBoundingClientRect();
  const style = getComputedStyle(element);
  return (
    rect.width > 0 &&
    rect.height > 0 &&
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    Number(style.opacity || 1) > 0
  );
}

export function collectToolCallCandidates(documentValue: Document = document): ToolCallTextCandidate[] {
  const elements = [...documentValue.querySelectorAll<HTMLElement>("pre, code")].slice(-MAX_CANDIDATES);
  return elements.flatMap((element, index) => {
    const text = element.textContent?.trim() ?? "";
    if (!text.includes("function_call_start") || text.length > MAX_CANDIDATE_CHARACTERS) return [];
    const editorCopy = Boolean(
      element.closest(".cm-editor, [data-cm-source]") || element.id.startsWith("cm-hidden-pre-"),
    );
    return [
      {
        sourceId: element.id || `plwc-call-source-${index}`,
        sourceKind: editorCopy ? ("editor-copy" as const) : ("rendered" as const),
        text,
        visible: isVisible(element),
      },
    ];
  });
}

export function recordExistingToolCalls(
  candidates: ToolCallTextCandidate[],
  seen: Set<string>,
): void {
  for (const call of parseVisiblePlwcToolCalls(candidates)) seen.add(call.callKey);
}

export function takeNewToolCalls(
  candidates: ToolCallTextCandidate[],
  seen: Set<string>,
): ParsedPlwcToolCall[] {
  return parseVisiblePlwcToolCalls(candidates).filter((call) => {
    if (seen.has(call.callKey)) return false;
    seen.add(call.callKey);
    return true;
  });
}

export function observePlwcToolCalls(
  onCall: (call: ParsedPlwcToolCall) => void,
  documentValue: Document = document,
): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const seen = new Set<string>();
  recordExistingToolCalls(collectToolCallCandidates(documentValue), seen);
  const scan = () => {
    timer = null;
    for (const call of takeNewToolCalls(collectToolCallCandidates(documentValue), seen)) onCall(call);
  };
  const schedule = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(scan, 120);
  };
  const observer = new MutationObserver(schedule);
  observer.observe(documentValue.body ?? documentValue.documentElement, {
    childList: true,
    characterData: true,
    subtree: true,
  });
  return () => {
    observer.disconnect();
    if (timer) clearTimeout(timer);
  };
}
