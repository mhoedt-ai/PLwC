import {
  parseVisiblePlwcToolCalls,
  resolveConversationId,
  type ParsedPlwcToolCall,
  type ToolCallTextCandidate,
} from "./tool-call-parser";
import { resolveChatTurnRole } from "./chat-turn";
import { revealLatestCollapsedAssistantReasoning } from "./assistant-disclosure";

const MAX_CANDIDATES = 240;
const MAX_CANDIDATE_CHARACTERS = 160_000;
const INITIAL_BASELINE_IDLE_MS = 1_000;
const INITIAL_BASELINE_MAX_MS = 12_000;
const SCAN_DEBOUNCE_MS = 120;
const RECONCILIATION_INTERVAL_MS = 1_000;
const TOOL_CALL_MARKERS = ['"plwc_tool_call"', "plwc_tool_call"];

function isVisible(element: HTMLElement): boolean {
  if (element.dataset.plwcMasked === "true") return true;
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
  const conversationId = resolveConversationId(documentValue);
  return elements.flatMap((element, index) => {
    if (resolveChatTurnRole(element) !== "assistant") return [];

    const text = element.textContent?.trim() ?? "";
    if (!TOOL_CALL_MARKERS.some(marker => text.includes(marker)) || text.length > MAX_CANDIDATE_CHARACTERS) return [];
    const editorCopy = Boolean(
      element.closest(".cm-editor, [data-cm-source]") || element.id.startsWith("cm-hidden-pre-"),
    );
    return [
      {
        conversationId,
        sourceId: element.id || `plwc-call-source-${index}`,
        sourceKind: editorCopy ? ("editor-copy" as const) : ("rendered" as const),
        text,
        visible: isVisible(element),
      },
    ];
  });
}

export type ToolCallRegistry = Map<string, ParsedPlwcToolCall>;

export interface ToolCallConflict {
  conflictingCall: ParsedPlwcToolCall;
  existingCall: ParsedPlwcToolCall;
  message: string;
}

export function recordExistingToolCalls(
  candidates: ToolCallTextCandidate[],
  registry: ToolCallRegistry,
  defaultConversationId = "unknown-conversation",
  recordedConflictVariants: Set<string> = new Set<string>(),
): void {
  for (const call of parseVisiblePlwcToolCalls(candidates, defaultConversationId)) {
    const existing = registry.get(call.callKey);
    if (!existing) {
      registry.set(call.callKey, call);
      continue;
    }
    if (existing.callSignatureKey !== call.callSignatureKey) {
      recordedConflictVariants.add(conflictVariantKey(call));
    }
  }
}

export function takeNewToolCalls(
  candidates: ToolCallTextCandidate[],
  registry: ToolCallRegistry,
  defaultConversationId = "unknown-conversation",
): ParsedPlwcToolCall[] {
  return takeNewToolCallObservation(candidates, registry, defaultConversationId).calls;
}

export function takeNewToolCallObservation(
  candidates: ToolCallTextCandidate[],
  registry: ToolCallRegistry,
  defaultConversationId = "unknown-conversation",
  recordedConflictVariants: Set<string> = new Set<string>(),
): Pick<ToolCallObservationScan, "calls" | "conflicts"> {
  const calls: ParsedPlwcToolCall[] = [];
  const conflicts: ToolCallConflict[] = [];
  for (const call of parseVisiblePlwcToolCalls(candidates, defaultConversationId)) {
    const existing = registry.get(call.callKey);
    if (!existing) {
      registry.set(call.callKey, call);
      calls.push(call);
      continue;
    }
    if (existing.callSignatureKey === call.callSignatureKey) continue;

    const variantKey = conflictVariantKey(call);
    if (recordedConflictVariants.has(variantKey)) continue;
    recordedConflictVariants.add(variantKey);
    conflicts.push({
      conflictingCall: call,
      existingCall: existing,
      message:
        `Conflicting PLwC tool call rejected: conversation_id ${JSON.stringify(call.conversationId)} ` +
        `and call_id ${JSON.stringify(call.callId)} were already assigned different tool arguments or a different tool name.`,
    });
  }
  return { calls, conflicts };
}

function conflictVariantKey(call: ParsedPlwcToolCall): string {
  return JSON.stringify([call.callKey, call.callSignatureKey]);
}

export interface ToolCallObservationScan {
  calls: ParsedPlwcToolCall[];
  conflicts: ToolCallConflict[];
  rescanAfterMs: number | null;
}

export class ToolCallObservationGate {
  private readonly registry = new Map<string, ParsedPlwcToolCall>();
  private readonly recordedConflictVariants = new Set<string>();
  private contextKey: string;
  private baselineStartedAt: number;
  private lastMutationAt: number;
  private recordingInitialBaseline = true;

  constructor(
    initialCandidates: ToolCallTextCandidate[],
    contextKey: string,
    now = Date.now(),
  ) {
    this.contextKey = contextKey;
    this.baselineStartedAt = now;
    this.lastMutationAt = now;
    recordExistingToolCalls(
      initialCandidates,
      this.registry,
      contextKey,
      this.recordedConflictVariants,
    );
  }

  noteMutation(now = Date.now()): void {
    this.lastMutationAt = now;
  }

  scan(
    candidates: ToolCallTextCandidate[],
    contextKey: string,
    now = Date.now(),
  ): ToolCallObservationScan {
    if (contextKey !== this.contextKey) {
      this.contextKey = contextKey;
      this.baselineStartedAt = now;
      this.lastMutationAt = now;
      this.recordingInitialBaseline = true;
      recordExistingToolCalls(
        candidates,
        this.registry,
        contextKey,
        this.recordedConflictVariants,
      );
      return { calls: [], conflicts: [], rescanAfterMs: INITIAL_BASELINE_IDLE_MS };
    }

    if (this.recordingInitialBaseline) {
      recordExistingToolCalls(
        candidates,
        this.registry,
        contextKey,
        this.recordedConflictVariants,
      );
      const idleFor = now - this.lastMutationAt;
      const baseliningFor = now - this.baselineStartedAt;
      if (idleFor < INITIAL_BASELINE_IDLE_MS && baseliningFor < INITIAL_BASELINE_MAX_MS) {
        return {
          calls: [],
          conflicts: [],
          rescanAfterMs: Math.min(
            INITIAL_BASELINE_IDLE_MS - idleFor,
            INITIAL_BASELINE_MAX_MS - baseliningFor,
          ),
        };
      }

      this.recordingInitialBaseline = false;
      return { calls: [], conflicts: [], rescanAfterMs: null };
    }

    const observation = takeNewToolCallObservation(
      candidates,
      this.registry,
      contextKey,
      this.recordedConflictVariants,
    );
    return {
      ...observation,
      rescanAfterMs: null,
    };
  }
}

export interface ToolCallObserverHandlers {
  onCall: (call: ParsedPlwcToolCall) => void;
  onConflict?: (conflict: ToolCallConflict) => void;
}

export function observePlwcToolCalls(
  handlers: ToolCallObserverHandlers,
  documentValue: Document = document,
): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const revealedReasoningTurns = new WeakSet<HTMLElement>();
  const gate = new ToolCallObservationGate(
    collectToolCallCandidates(documentValue),
    resolveConversationId(documentValue),
  );
  const scan = () => {
    timer = null;
    revealLatestCollapsedAssistantReasoning(documentValue, revealedReasoningTurns);
    const candidates = collectToolCallCandidates(documentValue);
    const result = gate.scan(
      candidates,
      resolveConversationId(documentValue),
    );
    for (const call of result.calls) handlers.onCall(call);
    for (const conflict of result.conflicts) handlers.onConflict?.(conflict);
    timer = setTimeout(
      scan,
      result.rescanAfterMs ?? RECONCILIATION_INTERVAL_MS,
    );
  };
  const schedule = () => {
    gate.noteMutation();
    if (timer) clearTimeout(timer);
    timer = setTimeout(scan, SCAN_DEBOUNCE_MS);
  };
  const observer = new MutationObserver(schedule);
  observer.observe(documentValue.body ?? documentValue.documentElement, {
    attributes: true,
    attributeFilter: ["aria-expanded", "data-message-author-role", "data-turn"],
    childList: true,
    characterData: true,
    subtree: true,
  });
  timer = setTimeout(scan, INITIAL_BASELINE_IDLE_MS);
  return () => {
    observer.disconnect();
    if (timer) clearTimeout(timer);
  };
}
