import { decidePolicy } from "../shared/policy";
import type { CanonicalToolName } from "../shared/contracts";
import {
  classifyToolResult,
  describeToolResultPresentation,
  toolResultMetadataRows,
} from "../shared/tool-result";
import {
  parseVisiblePlwcToolCalls,
  resolveConversationId,
  type ParsedPlwcToolCall,
} from "./tool-call-parser";
import {
  findPlwcToolResultForCall,
  PLWC_TOOL_RESULT_MARKER,
  parsePlwcToolResultFromText,
  parsePlwcToolResultMessage,
  type PlwcToolResultEnvelope,
} from "./tool-result-message";
import {
  closestChatTurnContainer,
  collectChatTurnContainers,
  isChatTurnBoundary,
  resolveChatTurnRole,
} from "./chat-turn";

export type ChatRunState =
  | "scheduled"
  | "awaiting_confirmation"
  | "running"
  | "succeeded"
  | "denied"
  | "failed"
  | "conflict"
  | "unknown";

export function runStateLabel(state: ChatRunState): string {
  return state === "awaiting_confirmation" ? "CONFIRM REQUIRED" : state.toUpperCase();
}

export function resultAwareRunStateLabel(
  state: ChatRunState,
  name?: CanonicalToolName,
  result?: unknown,
): string {
  if (state === "unknown") return "Transport failed";
  if (state === "conflict") return runStateLabel(state);
  if (name !== undefined && result !== undefined) {
    const presentation = describeToolResultPresentation(
      name,
      state !== "succeeded",
      result,
    );
    if (presentation.failureLabel !== null) return presentation.failureLabel;
    if (presentation.artifactTrust === "unvalidated") return "Unvalidated artifact";
  }
  if (state === "failed") return "Gateway failed";
  return runStateLabel(state);
}

export interface ChatToolRunSnapshot {
  call: ParsedPlwcToolCall;
  error?: string;
  result?: unknown;
  resultSubmitted?: boolean;
  state: ChatRunState;
}

interface CardBinding {
  expanded: boolean;
  host: HTMLElement;
  raw: HTMLElement;
  rawDisplay: string;
  rawDisplayPriority: string;
  rawVisible: boolean;
}

interface ChatRendererHandlers {
  onInsertResult?: (call: ParsedPlwcToolCall) => void | Promise<void>;
  onRun?: (call: ParsedPlwcToolCall, confirmed: boolean) => void | Promise<void>;
}

interface CompactBadge {
  className: string;
  text: string;
  title?: string;
}

const CARD_THEME = `
:host { all: initial; display: block; margin: 12px 0; color-scheme: dark; }
*, *::before, *::after { box-sizing: border-box; }
button, input { font: inherit; letter-spacing: 0; }
.card {
  width: 100%; overflow: hidden; color: #8fd99a; background: #020403;
  border: 1px solid #1b5b2b; border-radius: 8px;
  font-family: Consolas, "Lucida Console", "Courier New", monospace;
  font-size: 13px; line-height: 1.45; letter-spacing: 0;
}
.header {
  min-height: 42px; display: flex; flex-wrap: wrap; align-items: center;
  gap: 7px 9px; padding: 6px 9px; background: #050806;
}
.card.expanded .header { border-bottom: 1px solid #123d1e; }
.compact-title { min-width: 120px; flex: 1 1 160px; color: #5cff7a; font-weight: 700; overflow-wrap: anywhere; }
.compact-alert { flex: 0 0 auto; padding: 2px 5px; color: #ffbf66; border: 1px solid #8a6426; white-space: nowrap; }
.details-toggle { width: 30px; height: 30px; min-height: 30px; flex: 0 0 30px; display: grid; place-items: center; padding: 0; font-size: 18px; line-height: 1; }
.detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }
.identity { min-width: 0; flex: 1; }
.kind { color: #6f9d78; font-size: 11px; }
.name { color: #5cff7a; font-weight: 700; overflow-wrap: anywhere; }
.state { flex: 0 0 auto; padding: 2px 5px; color: #8fd99a; border: 1px solid #245d30; white-space: nowrap; }
.state.succeeded { color: #5cff7a; }
.state.awaiting_confirmation { color: #ffbf66; border-color: #8a6426; }
.state.warning { color: #ffbf66; border-color: #8a6426; }
.state.denied, .state.failed, .state.conflict, .state.unknown { color: #ff8293; border-color: #71313c; }
.body { padding: 10px; }
.policy { margin: 0 0 8px; color: #6f9d78; }
pre { max-height: 190px; margin: 0; overflow: auto; color: #8fd99a; white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }
.result { margin-top: 9px; padding-top: 9px; border-top: 1px solid #123d1e; }
.result-metadata {
  display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 3px 9px;
  margin: 9px 0 0; padding-top: 9px; border-top: 1px solid #123d1e;
}
.result-metadata dt { color: #6f9d78; }
.result-metadata dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.result-metadata .warning { color: #ffbf66; font-weight: 700; }
.result-metadata .validated { color: #5cff7a; }
.error { margin: 8px 0 0; color: #ff8293; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 10px; }
button { min-height: 32px; padding: 5px 9px; cursor: pointer; color: #8fd99a; background: #050806; border: 1px solid #245d30; border-radius: 2px; }
button.primary { color: #020403; background: #5cff7a; border-color: #5cff7a; font-weight: 700; }
button:disabled { cursor: not-allowed; color: #52705a; background: #0a110c; border-color: #123d1e; }
label { display: flex; align-items: center; gap: 7px; color: #8fd99a; }
input { accent-color: #5cff7a; }
button:focus-visible, input:focus-visible { outline: 2px solid #5cff7a; outline-offset: 1px; }
`;
const MAX_RENDER_BLOCKS = 240;
const MAX_RESULT_MESSAGES = 120;

function boundedJson(value: unknown, maxCharacters = 5_000): string {
  const serialized = JSON.stringify(value, null, 2) ?? "null";
  return serialized.length <= maxCharacters
    ? serialized
    : `${serialized.slice(0, maxCharacters)}\n[display truncated by PLwC Chat Bridge]`;
}

function compactCallBadges(snapshot: ChatToolRunSnapshot): CompactBadge[] {
  const statusLabel = snapshot.state === "awaiting_confirmation"
    ? "! CONFIRM"
    : resultAwareRunStateLabel(snapshot.state, snapshot.call.name, snapshot.result);
  const badges: CompactBadge[] = [{
    className:
      snapshot.state === "awaiting_confirmation" || statusLabel === "Unvalidated artifact"
        ? "compact-alert"
        : `state ${snapshot.state}`,
    text: statusLabel,
    title: snapshot.state === "awaiting_confirmation"
      ? "Individual confirmation required before execution"
      : undefined,
  }];
  const trustBadge = artifactTrustBadge(
    snapshot.call.name,
    snapshot.state !== "succeeded",
    snapshot.result,
  );
  if (trustBadge && statusLabel !== "Unvalidated artifact") badges.push(trustBadge);
  if (snapshot.resultSubmitted) {
    badges.push({ className: "state succeeded", text: "RESULT SENT" });
  }
  return badges;
}

export function selectCallMaskTarget(raw: HTMLElement): HTMLElement {
  return raw;
}

export function isRenderableChatBlock(
  element: HTMLElement,
  documentValue: Document = document,
): boolean {
  const rect = element.getBoundingClientRect();
  const style = documentValue.defaultView?.getComputedStyle(element);
  return rect.width > 0 && rect.height > 0 && style?.display !== "none" &&
    style?.visibility !== "hidden" && Number(style?.opacity ?? 1) > 0;
}

export class PlwcChatRenderer {
  private readonly callBindings = new Map<string, Set<CardBinding>>();
  private readonly records = new Map<string, ChatToolRunSnapshot>();
  private readonly resultBindings = new Set<CardBinding>();
  private readonly boundRawBlocks = new WeakSet<HTMLElement>();
  private readonly maskedResultContainers = new WeakSet<HTMLElement>();
  private readonly observer: MutationObserver;
  private handlers: ChatRendererHandlers = {};
  private enabled = true;
  private rightReserve = 0;
  private scanTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly documentValue: Document = document) {
    this.observer = new MutationObserver(() => this.scheduleScan());
  }

  mount(): void {
    this.scan();
    this.observer.observe(this.documentValue.body ?? this.documentValue.documentElement, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  }

  setHandlers(handlers: ChatRendererHandlers): void {
    this.handlers = handlers;
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    for (const bindings of this.callBindings.values()) {
      for (const binding of bindings) this.applyBindingVisibility(binding);
    }
    for (const binding of this.resultBindings) this.applyBindingVisibility(binding);
    if (enabled) this.scheduleScan();
  }

  setRightReserve(pixels: number): void {
    this.rightReserve = Math.max(0, pixels);
    for (const bindings of this.callBindings.values()) {
      for (const binding of bindings) this.applyBindingWidth(binding);
    }
    for (const binding of this.resultBindings) this.applyBindingWidth(binding);
  }

  updateToolRun(snapshot: ChatToolRunSnapshot): void {
    this.records.set(snapshot.call.callKey, { ...snapshot });
    for (const binding of this.callBindings.get(snapshot.call.callKey) ?? []) {
      this.renderCallCard(binding, snapshot);
    }
  }

  private scheduleScan(): void {
    if (this.scanTimer) clearTimeout(this.scanTimer);
    this.scanTimer = setTimeout(() => this.scan(), 100);
  }

  private scan(): void {
    this.scanTimer = null;
    const blocks = new Set<HTMLElement>();
    const elements = [...this.documentValue.querySelectorAll<HTMLElement>("pre, code")].slice(
      -MAX_RENDER_BLOCKS,
    );
    for (const element of elements) {
      blocks.add(element.closest<HTMLElement>("pre") ?? element);
    }
    for (const raw of blocks) this.inspectRawBlock(raw);
    this.inspectUnfencedResultMessages();
  }

  private inspectRawBlock(raw: HTMLElement): void {
    if (this.boundRawBlocks.has(raw) || raw.closest("[data-plwc-chat-card]")) return;
    if (!isRenderableChatBlock(raw, this.documentValue)) return;
    const text = raw.textContent?.trim() ?? "";
    if (!text) return;

    const [call] = parseVisiblePlwcToolCalls([
      {
        conversationId: resolveConversationId(this.documentValue),
        sourceId: raw.id || undefined,
        sourceKind: "rendered",
        text,
        visible: true,
      },
    ]);
    if (call) {
      this.bindCall(selectCallMaskTarget(raw), call);
      return;
    }

    const result = parsePlwcToolResultMessage(text);
    if (result && this.hasResultMarker(raw)) {
      const contentRoot = this.findResultContentRoot(raw);
      if (!this.boundRawBlocks.has(contentRoot)) this.bindResult(contentRoot, result);
    }
  }

  private inspectUnfencedResultMessages(): void {
    const containers = collectChatTurnContainers(this.documentValue, "user").slice(-MAX_RESULT_MESSAGES);
    for (const container of containers) {
      if (this.maskedResultContainers.has(container)) continue;
      const result = parsePlwcToolResultFromText(container.textContent ?? "");
      if (!result) continue;
      const target = findSmallestResultContainer(container, result) ?? container;
      if (this.boundRawBlocks.has(target)) continue;
      this.maskedResultContainers.add(container);
      this.bindResult(target, result);
    }
  }

  private hasResultMarker(raw: HTMLElement): boolean {
    const renderedMarker = PLWC_TOOL_RESULT_MARKER.replace(/^#\s*/u, "");
    let current: HTMLElement | null = raw;
    for (let depth = 0; current && depth < 8; depth += 1, current = current.parentElement) {
      const text = current.textContent ?? "";
      if (text.includes(PLWC_TOOL_RESULT_MARKER) || text.includes(renderedMarker)) return true;
      if (current === this.documentValue.body) break;
    }
    return false;
  }

  private findResultContentRoot(raw: HTMLElement): HTMLElement {
    const renderedMarker = PLWC_TOOL_RESULT_MARKER.replace(/^#\s*/u, "");
    let candidate = raw;
    let current = raw.parentElement;
    while (current && !isChatTurnBoundary(current)) {
      const text = current.textContent ?? "";
      if (text.includes(PLWC_TOOL_RESULT_MARKER) || text.includes(renderedMarker)) candidate = current;
      current = current.parentElement;
    }
    return candidate;
  }

  private bindCall(raw: HTMLElement, call: ParsedPlwcToolCall): void {
    const binding = this.createBinding(raw);
    binding.host.dataset.plwcChatCardKind = "call";
    const bindings = this.callBindings.get(call.callKey) ?? new Set<CardBinding>();
    bindings.add(binding);
    this.callBindings.set(call.callKey, bindings);
    const snapshot = this.records.get(call.callKey) ?? this.historicalSnapshot(call);
    this.records.set(call.callKey, snapshot);
    this.renderCallCard(binding, snapshot);
  }

  private historicalSnapshot(call: ParsedPlwcToolCall): ChatToolRunSnapshot {
    const candidates = [
      ...this.documentValue.querySelectorAll<HTMLElement>("pre, code"),
      ...collectChatTurnContainers(this.documentValue, "user"),
    ]
      .slice(-300)
      .map((node) => node.textContent?.trim() ?? "")
      .filter(Boolean);
    const result = findPlwcToolResultForCall(candidates, call.callId);
    if (!result) return { call, state: "scheduled" };
    if (result.name !== call.name) {
      return {
        call,
        error: "A result with this call_id belongs to a different PLwC tool name.",
        result: result.result,
        resultSubmitted: true,
        state: "conflict",
      };
    }
    return {
      call,
      result: result.result,
      resultSubmitted: true,
      state: classifyToolResult(result.is_error, result.result),
    };
  }

  private bindResult(raw: HTMLElement, result: PlwcToolResultEnvelope): void {
    if (this.boundRawBlocks.has(raw)) return;
    const message = resolveChatTurnRole(raw) === "user" ? closestChatTurnContainer(raw) : null;
    if (message) this.maskedResultContainers.add(message);
    const binding = this.createBinding(raw);
    binding.host.dataset.plwcChatCardKind = "result";
    this.resultBindings.add(binding);
    this.renderResultCard(binding, result);
  }

  private createBinding(raw: HTMLElement): CardBinding {
    const host = this.documentValue.createElement("div");
    host.dataset.plwcChatCard = "true";
    const binding = {
      expanded: false,
      host,
      raw,
      rawDisplay: raw.style.getPropertyValue("display"),
      rawDisplayPriority: raw.style.getPropertyPriority("display"),
      rawVisible: false,
    };
    raw.before(host);
    raw.dataset.plwcMasked = "true";
    this.boundRawBlocks.add(raw);
    for (const child of raw.querySelectorAll<HTMLElement>("pre, code")) {
      child.dataset.plwcMasked = "true";
      this.boundRawBlocks.add(child);
    }
    this.applyBindingVisibility(binding);
    this.applyBindingWidth(binding);
    return binding;
  }

  private applyBindingVisibility(binding: CardBinding): void {
    binding.host.style.display = this.enabled ? "block" : "none";
    if (this.enabled && !binding.rawVisible) {
      binding.raw.style.setProperty("display", "none", "important");
    } else if (binding.rawDisplay) {
      binding.raw.style.setProperty("display", binding.rawDisplay, binding.rawDisplayPriority);
    } else {
      binding.raw.style.removeProperty("display");
    }
  }

  private applyBindingWidth(binding: CardBinding): void {
    if (this.rightReserve === 0) {
      binding.host.style.maxWidth = "";
      return;
    }
    const viewportWidth = this.documentValue.defaultView?.innerWidth ?? 0;
    const available = viewportWidth - this.rightReserve - binding.host.getBoundingClientRect().left;
    binding.host.style.maxWidth = `${Math.max(240, available)}px`;
  }

  private renderCallCard(binding: CardBinding, snapshot: ChatToolRunSnapshot): void {
    const shadow = binding.host.shadowRoot ?? binding.host.attachShadow({ mode: "open" });
    const policy = decidePolicy(snapshot.call.name, { ...snapshot.call.arguments });
    const card = this.element("article", `card${binding.expanded ? " expanded" : ""}`);
    const header = this.buildCompactHeader(
      "PLwC-Gateway-Call",
      binding,
      () => this.renderCallCard(binding, snapshot),
      compactCallBadges(snapshot),
    );
    const body = this.element("div", "body");
    const detailHeader = this.element("div", "detail-header");
    const identity = this.element("div", "identity");
    const statusLabel = resultAwareRunStateLabel(
      snapshot.state,
      snapshot.call.name,
      snapshot.result,
    );
    identity.append(
      this.element("div", "kind", "PLwC CALL"),
      this.element("div", "name", snapshot.call.name),
    );
    detailHeader.append(
      identity,
      this.element(
        "span",
        `state ${snapshot.state}${statusLabel === "Unvalidated artifact" ? " warning" : ""}`,
        statusLabel,
      ),
    );
    body.append(
      detailHeader,
      this.element("p", "policy", policy.readOnly ? "READ-ONLY / governed facade" : policy.reason),
      this.element("pre", "", boundedJson(snapshot.call.arguments, 4_000)),
    );

    if (snapshot.result !== undefined) {
      const metadata = this.buildResultMetadata(
        snapshot.call.name,
        snapshot.state !== "succeeded",
        snapshot.result,
      );
      if (metadata) body.append(metadata);
      body.append(this.element("pre", "result", boundedJson(snapshot.result)));
    }
    if (snapshot.error) body.append(this.element("p", "error", snapshot.error));

    const actions = this.element("div", "actions");
    const canRun = ["scheduled", "awaiting_confirmation"].includes(snapshot.state);
    if (canRun) {
      let confirmed = !policy.requiresConfirmation;
      const run = this.button(policy.requiresConfirmation ? "Confirm & Run" : "Run", "primary");
      run.disabled = policy.requiresConfirmation || !this.handlers.onRun;
      if (policy.requiresConfirmation) {
        const label = this.element("label");
        const checkbox = this.element("input") as HTMLInputElement;
        checkbox.type = "checkbox";
        checkbox.addEventListener("change", () => {
          confirmed = checkbox.checked;
          run.disabled = !confirmed || !this.handlers.onRun;
        });
        label.append(checkbox, this.element("span", "", "Confirm mutating call"));
        actions.append(label);
      }
      run.addEventListener("click", () => void this.handlers.onRun?.(snapshot.call, confirmed));
      actions.append(run);
    }

    const canInsertResult = ["succeeded", "denied", "failed"].includes(snapshot.state);
    if (snapshot.result !== undefined && !snapshot.resultSubmitted && canInsertResult) {
      const insert = this.button("Insert Result");
      insert.disabled = !this.handlers.onInsertResult;
      insert.addEventListener("click", () => void this.handlers.onInsertResult?.(snapshot.call));
      actions.append(insert);
    }
    if (snapshot.resultSubmitted) {
      actions.append(this.element("span", "state succeeded", "RESULT SENT"));
    }
    actions.append(this.rawToggle(binding));
    body.append(actions);
    card.append(header);
    if (binding.expanded) card.append(body);

    const style = this.element("style");
    style.textContent = CARD_THEME;
    shadow.replaceChildren(style, card);
  }

  private renderResultCard(binding: CardBinding, result: PlwcToolResultEnvelope): void {
    const shadow = binding.host.shadowRoot ?? binding.host.attachShadow({ mode: "open" });
    const state = classifyToolResult(result.is_error, result.result);
    const card = this.element("article", `card${binding.expanded ? " expanded" : ""}`);
    const body = this.element("div", "body");
    const detailHeader = this.element("div", "detail-header");
    const identity = this.element("div", "identity");
    const statusLabel = resultAwareRunStateLabel(state, result.name, result.result);
    identity.append(this.element("div", "kind", "PLwC RESULT"), this.element("div", "name", result.name));
    detailHeader.append(
      identity,
      this.element(
        "span",
        `state ${state}${statusLabel === "Unvalidated artifact" ? " warning" : ""}`,
        statusLabel,
      ),
    );
    body.append(detailHeader);
    const metadata = this.buildResultMetadata(result.name, result.is_error, result.result);
    if (metadata) body.append(metadata);
    body.append(this.element("pre", "", boundedJson(result.result)));
    const actions = this.element("div", "actions");
    actions.append(this.rawToggle(binding));
    body.append(actions);
    const trustBadge = artifactTrustBadge(result.name, result.is_error, result.result);
    card.append(this.buildCompactHeader(
      "PLwC-Gateway-Result",
      binding,
      () => this.renderResultCard(binding, result),
      [
        {
          className: statusLabel === "Unvalidated artifact" ? "compact-alert" : `state ${state}`,
          text: statusLabel,
        },
        ...(trustBadge === null || statusLabel === "Unvalidated artifact" ? [] : [trustBadge]),
        { className: "state succeeded", text: "RESULT SENT" },
      ],
    ));
    if (binding.expanded) card.append(body);
    const style = this.element("style");
    style.textContent = CARD_THEME;
    shadow.replaceChildren(style, card);
  }

  private buildResultMetadata(
    name: CanonicalToolName,
    isError: boolean,
    result: unknown,
  ): HTMLElement | null {
    const rows = toolResultMetadataRows(name, isError, result);
    if (rows.length === 0) return null;

    const metadata = this.element("dl", "result-metadata");
    for (const row of rows) {
      metadata.append(
        this.element("dt", "", row.label),
        this.element("dd", row.tone === "default" ? "" : row.tone, row.value),
      );
    }
    return metadata;
  }

  private buildCompactHeader(
    label: string,
    binding: CardBinding,
    rerender: () => void,
    badges: readonly CompactBadge[] = [],
  ): HTMLElement {
    const header = this.element("header", "header");
    const toggle = this.button(binding.expanded ? "−" : "+", "details-toggle");
    const action = binding.expanded ? "Hide details" : "Show details";
    toggle.title = action;
    toggle.setAttribute("aria-label", action);
    toggle.setAttribute("aria-expanded", String(binding.expanded));
    toggle.addEventListener("click", () => {
      binding.expanded = !binding.expanded;
      rerender();
    });
    header.append(this.element("div", "compact-title", label));
    for (const badge of badges) {
      const indicator = this.element("span", badge.className, badge.text);
      if (badge.title) {
        indicator.title = badge.title;
        indicator.setAttribute("aria-label", badge.title);
      }
      header.append(indicator);
    }
    header.append(toggle);
    return header;
  }

  private rawToggle(binding: CardBinding): HTMLButtonElement {
    const toggle = this.button(binding.rawVisible ? "Hide JSON" : "Show JSON");
    toggle.addEventListener("click", () => {
      binding.rawVisible = !binding.rawVisible;
      this.applyBindingVisibility(binding);
      toggle.textContent = binding.rawVisible ? "Hide JSON" : "Show JSON";
    });
    return toggle;
  }

  private button(label: string, className = ""): HTMLButtonElement {
    const node = this.element("button", className, label);
    node.type = "button";
    return node;
  }

  private element<K extends keyof HTMLElementTagNameMap>(
    tag: K,
    className = "",
    text = "",
  ): HTMLElementTagNameMap[K] {
    const node = this.documentValue.createElement(tag);
    node.className = className;
    node.textContent = text;
    return node;
  }
}

function artifactTrustBadge(
  name: CanonicalToolName,
  isError: boolean,
  result: unknown,
): CompactBadge | null {
  if (result === undefined) return null;
  const presentation = describeToolResultPresentation(name, isError, result);
  if (presentation.artifactTrust === "unvalidated") {
    return {
      className: "compact-alert",
      text: "UNVALIDATED",
      title: "Artifact is unvalidated and must not be treated as safe",
    };
  }
  if (presentation.artifactTrust === "validated") {
    return { className: "state succeeded", text: "VALIDATED" };
  }
  return null;
}

function findSmallestResultContainer(
  container: HTMLElement,
  result: PlwcToolResultEnvelope,
): HTMLElement | null {
  const descendants = [...container.querySelectorAll<HTMLElement>("div, p, pre, article")].reverse();
  return descendants.find((candidate) => {
    const parsed = parsePlwcToolResultFromText(candidate.textContent ?? "");
    return parsed?.call_id === result.call_id && parsed.name === result.name;
  }) ?? null;
}
