import { BridgeClient } from "../content/bridge-client";
import { buildPlwcChainRecoveryMessage } from "../content/chain-recovery";
import { copyCompleteToolResultMessage } from "../content/complete-result-copy";
import {
  type ChatGptComposerLock,
  findChatGptComposer,
  findChatGptComposerSurface,
  insertAndSubmitToChatGpt,
  insertIntoChatGptComposerVerified,
  lockChatGptComposerElement,
  unlockChatGptComposerElement,
} from "../content/composer";
import {
  resultAwareRunStateLabel,
  type ChatRunState,
  type PlwcChatRenderer,
} from "../content/chat-renderer";
import type { ParsedPlwcToolCall } from "../content/tool-call-parser";
import {
  buildOnboardingContinuation,
  type PlwcOnboardingContinuation,
} from "../content/onboarding-continuation";
import {
  buildOnboardingEntryCorrection,
  type PlwcToolCallCorrection,
} from "../content/onboarding-correction";
import type { ToolCallConflict } from "../content/tool-call-observer";
import {
  findPlwcToolResultForCall,
  formatPlwcToolResultMessage,
} from "../content/tool-result-message";
import { buildPrimer, type BridgePrimer } from "../primer/build-primer";
import { AutomaticRunQueue, shouldAutoRun, shouldAutoSubmitResult } from "../shared/automation";
import type { CanonicalToolName, McpTool } from "../shared/contracts";
import {
  localizeBuildIdentityMatch,
  localizeBridgeError,
  localizeConnectionState,
  localizeLauncherStatus,
  resolveUiLanguage,
  text,
} from "../shared/i18n";
import { EXTENSION_BUILD_IDENTITY } from "../shared/build-identity";
import type {
  BridgeSettings,
  BridgeStatus,
  GatewaySettingsSnapshot,
  GatewaySettingsUpdate,
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";
import { decidePolicy, POLICY_ROWS } from "../shared/policy";
import {
  chunkTransportFailureResult,
  classifyToolResult,
  prepareToolResultForChat,
  presentToolResult,
  toolResultMetadataRows,
  type ToolResultTransportFailure,
} from "../shared/tool-result";
import {
  calculateComposerBusyOverlayPosition,
  calculateComposerLauncherPosition,
  calculatePanelLayout,
  findLeftNavigationRight,
  PANEL_GAP,
} from "./layout";
import {
  normalizeBridgeStatus,
  shouldOfferSetupDownload,
  shouldRequestNativeAutoStart,
} from "./status";
import { TERMINAL_THEME } from "./theme";
import { ComposerBusyGate } from "./composer-busy-gate";

const TAB_NAMES = ["PLwC Tools", "Primer", "Policy", "Status", "Settings"] as const;
const PLWC_OFFICIAL_RELEASES_URL = "https://github.com/mhoedt-ai/PLwC/releases";
type TabName = (typeof TAB_NAMES)[number];
type RunState = ChatRunState;

interface ToolRunRecord {
  call: ParsedPlwcToolCall;
  state: RunState;
  chatResult?: unknown;
  result?: unknown;
  resultSubmitted?: boolean;
  isError?: boolean;
  error?: string;
  identityConflict?: string;
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = "",
  text = "",
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function button(label: string, className = "command-button secondary"): HTMLButtonElement {
  const node = element("button", className, label);
  node.type = "button";
  return node;
}

function boundedJson(value: unknown, maxCharacters = 12_000): string {
  const serialized = JSON.stringify(value, null, 2) ?? "null";
  return serialized.length <= maxCharacters
    ? serialized
    : `${serialized.slice(0, maxCharacters)}\n[output truncated by PLwC Chat Bridge]`;
}

function toolResultMetadata(
  name: CanonicalToolName,
  isError: boolean,
  result: unknown,
): HTMLElement | null {
  const rows = toolResultMetadataRows(name, isError, result);
  if (rows.length === 0) return null;

  const metadata = element("dl", "run-result-metadata");
  for (const row of rows) {
    metadata.append(
      element("dt", "", row.label),
      element("dd", row.tone === "default" ? "" : row.tone, row.value),
    );
  }
  return metadata;
}

function waitSeconds(seconds: number): Promise<void> {
  return seconds <= 0
    ? Promise.resolve()
    : new Promise((resolve) => setTimeout(resolve, seconds * 1_000));
}

export class PlwcPanel {
  private readonly root = element("div", "bridge-root");
  private readonly panel = element("section", "bridge-panel");
  private readonly launcher = button("", "bridge-launcher");
  private readonly composerLauncher = button("", "composer-launcher is-hidden");
  private readonly composerBusyOverlay = element("div", "composer-busy-overlay is-hidden");
  private readonly composerBusyDots = element("span", "composer-busy-dots", ".");
  private readonly composerBusyUnlock = button("Unlock input", "composer-busy-unlock");
  private readonly statusDot = element("span", "status-dot");
  private readonly views = new Map<TabName, HTMLElement>();
  private readonly language = resolveUiLanguage(chrome.i18n?.getUILanguage?.() ?? globalThis.navigator?.language);
  private activeTab: TabName = "PLwC Tools";
  private userCollapsed: boolean | undefined;
  private tools: McpTool[] = [];
  private primer: BridgePrimer | null = null;
  private statusValue: BridgeStatus | null = null;
  private settings: BridgeSettings = {
    autoConfirmSandbox: false,
    autoConfirmWrites: false,
    autoExecuteDelay: 2,
    autoInsertDelay: 2,
    autoSubmitDelay: 2,
    autoSubmitResults: true,
    composerBusyTimeout: 60,
    readOnlyAutoRun: true,
    renderChatCards: true,
  };
  private gatewaySettings: GatewaySettingsSnapshot | null = null;
  private readonly toolRuns = new Map<string, ToolRunRecord>();
  private readonly automaticRunQueue = new AutomaticRunQueue();
  private readonly composerBusyGate = new ComposerBusyGate(() => this.syncComposerBusyState());
  private composerLock: ChatGptComposerLock | null = null;
  private composerBusyTimer: ReturnType<typeof setInterval> | null = null;
  private composerBusyDotCount = 1;
  private chainRecoveryInProgress = false;
  private chainRecoveriesSinceToolCall = 0;
  private resizeTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly hostObserver = new MutationObserver(() => this.scheduleLayout());
  private readonly onResize = () => {
    this.scheduleLayout();
  };

  constructor(
    private readonly shadowRoot: ShadowRoot,
    private readonly client: BridgeClient,
    private readonly chatRenderer?: PlwcChatRenderer,
  ) {
    this.chatRenderer?.setHandlers({
      onInsertResult: (call) => this.insertToolResultForCall(call),
      onRun: (call, confirmed) => this.runToolCallFromChat(call, confirmed),
    });
  }

  mount(): void {
    const style = element("style");
    style.textContent = TERMINAL_THEME;
    this.buildLauncher();
    this.buildComposerLauncher();
    this.buildComposerBusyOverlay();
    this.buildPanel();
    this.shadowRoot.append(style, this.root);
    this.applyLayout();

    window.addEventListener("resize", this.onResize, { passive: true });
    this.hostObserver.observe(document.body ?? document.documentElement, { childList: true, subtree: true });
    setInterval(() => void this.refreshConnectionStatus(), 15_000);
    this.client.onStatus((status) => {
      this.statusValue = status;
      this.renderStatus();
    });

    void this.initialize();
  }

  offerToolCall(call: ParsedPlwcToolCall): void {
    const existing = this.toolRuns.get(call.callKey);
    if (existing) {
      if (existing.call.callSignatureKey !== call.callSignatureKey) {
        this.offerToolCallConflict({
          conflictingCall: call,
          existingCall: existing.call,
          message:
            `Conflicting PLwC tool call rejected: conversation_id ${JSON.stringify(call.conversationId)} ` +
            `and call_id ${JSON.stringify(call.callId)} were already assigned different tool arguments or a different tool name.`,
        });
      }
      return;
    }
    this.chainRecoveriesSinceToolCall = 0;
    const policy = decidePolicy(call.name, { ...call.arguments });
    const automatic = shouldAutoRun(this.settings, policy);
    const record: ToolRunRecord = {
      call,
      state: policy.requiresConfirmation && !automatic ? "awaiting_confirmation" : "scheduled",
    };
    this.toolRuns.set(call.callKey, record);
    this.syncChatCard(record);
    this.renderStatus();
    if (automatic) this.queueAutomaticRun(record, policy);
  }

  offerToolCallConflict(conflict: ToolCallConflict): void {
    const record = this.toolRuns.get(conflict.existingCall.callKey) ?? {
      call: conflict.existingCall,
      state: "conflict" as const,
    };
    record.identityConflict = conflict.message;
    record.error = conflict.message;
    record.state = "conflict";
    this.toolRuns.set(record.call.callKey, record);
    this.syncChatCard(record);
    this.renderStatus();
  }

  async recoverStalledChain(): Promise<void> {
    if (
      this.chainRecoveryInProgress ||
      this.chainRecoveriesSinceToolCall >= 1 ||
      this.composerBusyGate.activeCount > 0
    ) return;
    this.chainRecoveryInProgress = true;
    try {
      const outcome = await insertAndSubmitToChatGpt(
        buildPlwcChainRecoveryMessage(this.latestToolCallGuidance()),
        document,
        {
          autoSubmitDelayMs: this.settings.autoSubmitDelay * 1_000,
          readinessWaitAttempts: 20,
        },
      );
      if (outcome === "submitted") {
        this.chainRecoveriesSinceToolCall += 1;
      } else {
        this.showError("Status", new Error(`Automatic chain recovery paused: ${outcome}.`));
      }
    } finally {
      this.chainRecoveryInProgress = false;
    }
  }

  private queueAutomaticRun(
    record: ToolRunRecord,
    policy = decidePolicy(record.call.name, { ...record.call.arguments }),
  ): void {
    const delay = this.settings.autoExecuteDelay;
    void this.automaticRunQueue.enqueue(
      record.call.sourceId,
      async () => {
        await waitSeconds(delay);
        if (!shouldAutoRun(this.settings, policy)) {
          record.state = policy.requiresConfirmation ? "awaiting_confirmation" : "scheduled";
          this.syncChatCard(record);
          this.renderStatus();
          return false;
        }
        const confirmed = policy.requiresConfirmation;
        await this.executeToolCall(record.call.callKey, confirmed);
        const resultExpectedInChat = shouldAutoSubmitResult(this.settings, policy, confirmed);
        return record.state === "succeeded" && (!resultExpectedInChat || record.resultSubmitted === true);
      },
      () => {
        record.error = "Automatic execution paused because an earlier call in the same response did not complete successfully.";
        this.syncChatCard(record);
        this.renderStatus();
      },
    );
  }

  private resumeEligibleAutomaticCalls(): void {
    for (const record of this.toolRuns.values()) {
      if (record.state !== "awaiting_confirmation") continue;
      const policy = decidePolicy(record.call.name, { ...record.call.arguments });
      if (!shouldAutoRun(this.settings, policy)) continue;
      record.state = "scheduled";
      record.error = undefined;
      this.syncChatCard(record);
      this.queueAutomaticRun(record, policy);
    }
    this.renderStatus();
  }

  private buildLauncher(): void {
    this.launcher.title = "Open PLwC Chat Bridge";
    this.launcher.setAttribute("aria-label", "Open PLwC Chat Bridge");
    const image = element("img");
    image.src = chrome.runtime.getURL("icons/plwc-icon-512.png");
    image.alt = "";
    this.launcher.append(image);
    this.launcher.addEventListener("click", () => {
      this.userCollapsed = false;
      this.applyLayout();
    });
    this.root.append(this.launcher);
  }

  private buildComposerLauncher(): void {
    this.composerLauncher.title = "Toggle PLwC Chat Bridge";
    this.composerLauncher.setAttribute("aria-label", "Toggle PLwC Chat Bridge");
    this.composerLauncher.setAttribute("aria-pressed", "false");
    const image = element("img");
    image.src = chrome.runtime.getURL("icons/plwc-icon-512.png");
    image.alt = "";
    this.composerLauncher.append(image);
    this.composerLauncher.addEventListener("click", () => {
      this.userCollapsed = !this.root.classList.contains("is-collapsed");
      this.applyLayout();
    });
    this.root.append(this.composerLauncher);
  }

  private buildComposerBusyOverlay(): void {
    this.composerBusyOverlay.setAttribute("role", "status");
    this.composerBusyOverlay.setAttribute("aria-live", "off");
    this.composerBusyOverlay.setAttribute("aria-label", "PLwC tool is running. Chat input is locked.");
    this.composerBusyUnlock.title = "Release the ChatGPT input without cancelling the PLwC operation.";
    this.composerBusyUnlock.setAttribute("aria-label", "Unlock ChatGPT input");
    this.composerBusyUnlock.addEventListener("click", () => this.composerBusyGate.release());
    this.composerBusyOverlay.append(
      element("span", "composer-busy-label", "PLwC working"),
      this.composerBusyDots,
      this.composerBusyUnlock,
    );
    this.root.append(this.composerBusyOverlay);
  }

  private buildPanel(): void {
    this.panel.setAttribute("aria-label", "PLwC Chat Bridge");
    this.panel.append(this.buildHeader(), this.buildTabs(), this.buildViews());
    this.root.append(this.panel);
  }

  private buildHeader(): HTMLElement {
    const header = element("header", "bridge-header");
    const image = element("img");
    image.src = chrome.runtime.getURL("icons/plwc-icon-512.png");
    image.alt = "PLwC Gateway";
    const title = element("div", "bridge-title", "PLwC Chat Bridge");
    const collapse = button("<", "icon-button");
    collapse.title = "Collapse bridge";
    collapse.setAttribute("aria-label", "Collapse bridge");
    collapse.addEventListener("click", () => {
      this.userCollapsed = true;
      this.applyLayout();
    });
    header.append(image, title, this.statusDot, collapse);
    return header;
  }

  private buildTabs(): HTMLElement {
    const tabs = element("div", "tabs");
    tabs.setAttribute("role", "tablist");
    for (const name of TAB_NAMES) {
      const tab = button(name, "tab");
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(name === this.activeTab));
      tab.addEventListener("click", () => this.selectTab(name));
      tabs.append(tab);
    }
    return tabs;
  }

  private buildViews(): HTMLElement {
    const container = element("main", "views");
    for (const name of TAB_NAMES) {
      const view = element("section", `view${name === this.activeTab ? " active" : ""}`);
      view.dataset.tab = name;
      this.views.set(name, view);
      container.append(view);
    }
    this.renderTools();
    this.renderPrimer();
    this.renderPolicy();
    this.renderStatus();
    this.renderSettings();
    return container;
  }

  private selectTab(name: TabName): void {
    this.activeTab = name;
    for (const tab of this.panel.querySelectorAll<HTMLButtonElement>(".tab")) {
      tab.setAttribute("aria-selected", String(tab.textContent === name));
    }
    for (const [tabName, view] of this.views) view.classList.toggle("active", tabName === name);
  }

  private async initialize(): Promise<void> {
    try {
      this.settings = await this.client.getSettings();
      this.chatRenderer?.setEnabled(this.settings.renderChatCards);
      await this.refreshTools();
      await this.refreshGatewaySettings();
    } catch (error) {
      this.showError("Status", error);
    } finally {
      this.renderSettings();
      this.renderStatus();
    }
  }

  private async refreshTools(autoStart?: boolean): Promise<void> {
    try {
      this.statusValue = await this.client.connect(autoStart ?? shouldRequestNativeAutoStart(this.statusValue));
      const response = await this.client.listTools();
      this.acceptToolList(response);
    } catch (error) {
      await this.refreshStatusAfterError();
      throw error;
    }
  }

  private async refreshGatewaySettings(): Promise<void> {
    try {
      this.statusValue = await this.client.connect(shouldRequestNativeAutoStart(this.statusValue));
      this.gatewaySettings = await this.client.getGatewaySettings();
      this.renderSettings();
    } catch (error) {
      await this.refreshStatusAfterError();
      throw error;
    }
  }

  private async refreshConnectionStatus(): Promise<void> {
    try {
      this.statusValue = await this.client.connect(shouldRequestNativeAutoStart(this.statusValue));
      if (!this.statusValue.toolSet?.valid) {
        this.acceptToolList(await this.client.listTools());
        this.statusValue = await this.client.status();
      }
    } catch {
      try {
        this.statusValue = await this.client.status();
      } catch {
        return;
      }
    }
    this.renderStatus();
  }

  private async refreshStatusAfterError(): Promise<void> {
    try {
      this.statusValue = await this.client.status();
      this.renderStatus();
    } catch {
      return;
    }
  }

  private acceptToolList(response: ToolListResponse): void {
    this.tools = response.validation.valid ? response.tools : [];
    this.primer = null;
    this.renderTools(response);
    this.renderPrimer();
    this.renderStatus();
  }

  private renderTools(response?: ToolListResponse): void {
    const view = this.views.get("PLwC Tools");
    if (!view) return;
    view.replaceChildren();
    const toolbar = element("div", "toolbar");
    toolbar.append(element("span", "label", "PUBLIC FACADE"), element("span", "spacer"));
    const refresh = button("Refresh");
    refresh.addEventListener("click", () => void this.runAction(refresh, () => this.refreshTools()));
    toolbar.append(refresh);
    view.append(toolbar);

    const valid = response?.validation.valid ?? this.tools.length === 8;
    const contract = element("div", "contract-state");
    contract.append(
      element("div", valid ? "label" : "error-text", valid ? "8 / 8 tools verified" : "Tool contract locked"),
      element(
        "div",
        "muted",
        valid
          ? "Schemas loaded live from the local PLwC Gateway."
          : "Primer and execution stay disabled until exactly eight canonical tools are present.",
      ),
    );
    view.append(contract);

    if (response && !response.validation.valid) {
      view.append(
        element(
          "pre",
          "error-text",
          boundedJson({
            duplicates: response.validation.duplicates,
            extra: response.validation.extra,
            invalidSchemas: response.validation.invalidSchemas,
            missing: response.validation.missing,
          }),
        ),
      );
    }

    for (const tool of this.tools) {
      const item = element("article", "tool");
      item.append(
        element("div", "tool-name", tool.name),
        element("div", "tool-description", tool.description ?? "No gateway description."),
      );
      const details = element("details");
      details.append(element("summary", "", "Schema"), element("pre", "", boundedJson(tool.inputSchema)));
      item.append(details);
      view.append(item);
    }
  }

  private renderPrimer(): void {
    const view = this.views.get("Primer");
    if (!view) return;
    view.replaceChildren();
    const toolbar = element("div", "toolbar");
    toolbar.append(element("span", "label", "BRIDGE PRIMER"), element("span", "spacer"));
    const generate = button("Generate");
    generate.disabled = this.tools.length !== 8;
    toolbar.append(generate);
    view.append(toolbar);

    const preview = element("textarea", "primer-preview") as HTMLTextAreaElement;
    preview.readOnly = true;
    preview.placeholder = "Connect to the PLwC Gateway to generate the versioned primer.";
    const hash = element("code", "hash", "schema_sha256: pending");
    const insert = button("Insert Bridge Primer");
    insert.disabled = true;
    view.append(preview, hash, insert);

    const update = async () => {
      this.primer = await buildPrimer({ tools: this.tools });
      preview.value = this.primer.text;
      hash.textContent = `schema_sha256: ${this.primer.hash}`;
      insert.disabled = false;
    };
    generate.addEventListener("click", () => void this.runAction(generate, update));
    insert.addEventListener("click", async () => {
      if (!this.primer) return;
      const outcome = await insertIntoChatGptComposerVerified(this.primer.text);
      if (outcome !== "inserted") {
        const message = outcome === "composer-not-found"
          ? "ChatGPT composer was not found."
          : "ChatGPT rejected the inserted primer.";
        this.showError("Primer", new Error(message));
        return;
      }
      insert.textContent = "Inserted";
      setTimeout(() => (insert.textContent = "Insert Bridge Primer"), 1_500);
    });
  }

  private renderPolicy(): void {
    const view = this.views.get("Policy");
    if (!view) return;
    view.replaceChildren(element("div", "label", "EXECUTION POLICY"));
    const table = element("table", "policy-table");
    const head = element("thead");
    const headRow = element("tr");
    headRow.append(element("th", "", "Capability"), element("th", "", "Rule"));
    head.append(headRow);
    const body = element("tbody");
    for (const [capability, rule] of POLICY_ROWS) {
      const row = element("tr");
      row.append(element("td", "", capability), element("td", "", rule));
      body.append(row);
    }
    table.append(head, body);
    view.append(table, element("p", "muted", "The PLwC Gateway remains the final allow or deny boundary."));
  }

  private renderStatus(): void {
    const view = this.views.get("Status");
    if (!view) return;
    view.replaceChildren();
    const toolbar = element("div", "toolbar");
    toolbar.append(element("span", "label", text("local_status", this.language)), element("span", "spacer"));
    const reconnect = button(text("reconnect", this.language));
    toolbar.append(reconnect);
    view.append(toolbar);
    const values = normalizeBridgeStatus(this.statusValue);
    this.statusDot.className = `status-dot ${values.connection}`;
    const grid = element("dl", "status-grid");
    const rows: string[][] = [
      [text("label_bridge", this.language), localizeConnectionState(values.connection, this.language)],
      [text("label_endpoint", this.language), values.endpoint],
      [text("label_build_id", this.language), EXTENSION_BUILD_IDENTITY.buildId],
      [
        text("label_build_match", this.language),
        localizeBuildIdentityMatch(
          values.buildIdentityValidation === null ? null : values.buildIdentityValidation.valid,
          this.language,
        ),
      ],
      [
        text("label_bridge_version", this.language),
        EXTENSION_BUILD_IDENTITY.components.nodeBridge,
      ],
      [
        text("label_extension_version", this.language),
        EXTENSION_BUILD_IDENTITY.components.browserExtension,
      ],
      [
        text("label_launcher_version", this.language),
        EXTENSION_BUILD_IDENTITY.components.nativeLauncher,
      ],
      [text("label_tools", this.language), `${this.tools.length} / 8`],
      [
        text("label_launcher", this.language),
        localizeLauncherStatus(values.launcher, this.language),
      ],
      [text("label_pending", this.language), String(values.pendingRequests)],
      [text("label_error", this.language), localizeBridgeError(values.lastError, this.language)],
    ];
    if (values.launcher.logPath) {
      rows.push([text("label_log", this.language), values.launcher.logPath]);
    }
    for (const [label, value] of rows) {
      grid.append(element("dt", "", label), element("dd", "", value));
    }
    view.append(grid);
    if (shouldOfferSetupDownload(values)) {
      const setupHelp = element("p", "muted launcher-setup-help");
      setupHelp.append(`${text("launcher_store_boundary", this.language)} `);
      const setupLink = element("a", "", text("setup_download", this.language)) as HTMLAnchorElement;
      setupLink.href = PLWC_OFFICIAL_RELEASES_URL;
      setupLink.target = "_blank";
      setupLink.rel = "noopener noreferrer";
      setupHelp.append(setupLink);
      view.append(setupHelp);
    }
    const runtime = button(text("runtime_status", this.language), "command-button");
    runtime.disabled = this.tools.length !== 8;
    const result = element("pre", "", text("no_runtime_status", this.language));
    reconnect.addEventListener("click", () => void this.runAction(reconnect, () => this.refreshTools(true)));
    runtime.addEventListener("click", () =>
      void this.runAction(runtime, async () => {
        const response = await this.client.callTool("plwc_status", { scope: "runtime" });
        this.statusValue = await this.client.status();
        result.textContent = boundedJson(presentToolResult("plwc_status", response.result), 5_000);
      }),
    );
    view.append(runtime, result);
    view.append(this.renderToolRuns());
  }

  private renderToolRuns(): HTMLElement {
    const section = element("section", "run-queue");
    section.append(element("div", "label", "DETECTED TOOL CALLS"));
    if (this.toolRuns.size === 0) {
      section.append(element("p", "muted", "No visible PLwC tool call detected in this chat."));
      return section;
    }

    for (const record of [...this.toolRuns.values()].reverse()) {
      const policy = decidePolicy(record.call.name, { ...record.call.arguments });
      const displayedResult = record.chatResult ??
        (record.result === undefined ? undefined : presentToolResult(record.call.name, record.result));
      const statusLabel = resultAwareRunStateLabel(
        record.state,
        record.call.name,
        displayedResult,
      );
      const card = element("article", "run-card");
      const header = element("div", "run-header");
      header.append(
        element("code", "tool-name", record.call.name),
        element(
          "span",
          `run-state ${record.state}${statusLabel === "Unvalidated artifact" ? " warning" : ""}`,
          statusLabel,
        ),
      );
      card.append(
        header,
        element("div", "run-call-id", `call_id: ${record.call.callId}`),
        element("pre", "run-arguments", boundedJson(record.call.arguments, 4_000)),
      );

      const actions = element("div", "toolbar");
      const run = button(policy.requiresConfirmation ? "Confirm & Run" : "Run", "command-button");
      const terminalState = !["scheduled", "awaiting_confirmation"].includes(record.state);
      run.disabled = terminalState || policy.requiresConfirmation;
      if (policy.requiresConfirmation && ["scheduled", "awaiting_confirmation"].includes(record.state)) {
        const confirmation = element("label", "setting-row run-confirmation");
        const checkbox = element("input") as HTMLInputElement;
        checkbox.type = "checkbox";
        checkbox.addEventListener("change", () => (run.disabled = !checkbox.checked));
        confirmation.append(checkbox, element("span", "", "I confirm this mutating PLwC call."));
        card.append(confirmation);
      }
      run.addEventListener("click", () => void this.executeToolCall(record.call.callKey, policy.requiresConfirmation));
      actions.append(run);

      const canInsertResult = ["succeeded", "denied", "failed"].includes(record.state);
      const resultReturned = this.markResultReturnedIfPresent(record);
      if (record.result !== undefined && canInsertResult) {
        const copy = button("Copy Complete Result");
        copy.addEventListener("click", () => void this.copyToolResult(record, copy));
        actions.append(copy);
      }
      if (record.result !== undefined && canInsertResult && !resultReturned) {
        const insert = button("Insert Result");
        insert.addEventListener("click", () => void this.insertToolResult(record, insert));
        actions.append(insert);
      }
      if (resultReturned) actions.append(element("span", "run-state succeeded", "RESULT SENT"));
      card.append(actions);
      if (record.error) card.append(element("p", "error-text", record.error));
      if (record.result !== undefined) {
        const metadata = toolResultMetadata(
          record.call.name,
          record.isError === true || record.state !== "succeeded",
          displayedResult,
        );
        if (metadata) card.append(metadata);
        card.append(
          element(
            "pre",
            "run-result",
            boundedJson(displayedResult, 5_000),
          ),
        );
      }
      section.append(card);
    }
    return section;
  }

  private async runToolCallFromChat(call: ParsedPlwcToolCall, confirmed: boolean): Promise<void> {
    const existing = this.toolRuns.get(call.callKey);
    if (existing && existing.call.callSignatureKey !== call.callSignatureKey) {
      this.offerToolCallConflict({
        conflictingCall: call,
        existingCall: existing.call,
        message:
          `Conflicting PLwC tool call rejected: conversation_id ${JSON.stringify(call.conversationId)} ` +
          `and call_id ${JSON.stringify(call.callId)} were already assigned different tool arguments or a different tool name.`,
      });
      return;
    }
    if (!existing) {
      const policy = decidePolicy(call.name, { ...call.arguments });
      const record: ToolRunRecord = {
        call,
        state: policy.requiresConfirmation ? "awaiting_confirmation" : "scheduled",
      };
      this.toolRuns.set(call.callKey, record);
      this.syncChatCard(record);
    }
    const record = this.toolRuns.get(call.callKey);
    if (record && this.markResultReturnedIfPresent(record)) {
      this.renderStatus();
      return;
    }
    await this.executeToolCall(call.callKey, confirmed);
  }

  private async executeToolCall(callKey: string, confirmed: boolean): Promise<void> {
    const record = this.toolRuns.get(callKey);
    if (!record || !["scheduled", "awaiting_confirmation"].includes(record.state)) return;
    if (this.markResultReturnedIfPresent(record)) {
      this.renderStatus();
      return;
    }
    const policy = decidePolicy(record.call.name, { ...record.call.arguments });
    if (policy.requiresConfirmation && !confirmed) return;
    record.state = "running";
    record.error = undefined;
    record.chatResult = undefined;
    record.result = undefined;
    record.isError = undefined;
    record.resultSubmitted = undefined;
    this.syncChatCard(record);
    this.renderStatus();
    this.beginToolCall(record.call.callKey);
    try {
      try {
        const response: ToolCallResponse = await this.client.callTool(
          record.call.name,
          { ...record.call.arguments },
          confirmed,
          {
            callId: record.call.callId,
            conversationId: record.call.conversationId,
          },
        );
        record.result = response.result;
        const prepared = prepareToolResultForChat(record.call.name, response.result);
        if (!prepared.ok) {
          this.applyChunkTransportFailure(record, prepared);
        } else {
          record.chatResult = prepared.result;
          record.state = classifyToolResult(response.isError, response.result);
          record.isError = record.state !== "succeeded";
          if (record.state === "failed") record.error = "PLwC returned an unsuccessful result.";
        }
        this.statusValue = await this.client.status();
        if (shouldAutoSubmitResult(this.settings, policy, confirmed)) {
          await this.submitToolResult(record);
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Tool call failed.";
        record.error = message;
        record.state = /timed out|connection closed/i.test(message) ? "unknown" : "failed";
      }
      if (record.identityConflict) {
        record.error = record.identityConflict;
        record.state = "conflict";
      }
      this.syncChatCard(record);
      this.renderStatus();
    } finally {
      this.endToolCall(record.call.callKey);
    }
  }

  private async copyToolResult(
    record: ToolRunRecord,
    control?: HTMLButtonElement,
  ): Promise<void> {
    const originalLabel = control?.textContent ?? "Copy Complete Result";
    try {
      await copyCompleteToolResultMessage(this.buildToolResultMessage(record));
      if (control) control.textContent = "Complete Result Copied";
    } catch (error) {
      this.showError("Status", error);
      if (control) control.textContent = "Copy Failed";
    } finally {
      if (control) {
        setTimeout(() => {
          control.textContent = originalLabel;
        }, 2_000);
      }
    }
  }

  private async insertToolResultForCall(call: ParsedPlwcToolCall): Promise<void> {
    const record = this.toolRuns.get(call.callKey);
    if (record) await this.insertToolResult(record);
  }

  private async insertToolResult(
    record: ToolRunRecord,
    control?: HTMLButtonElement,
  ): Promise<boolean> {
    if (this.markResultReturnedIfPresent(record)) return false;
    const message = this.buildToolResultMessage(record);
    const outcome = await insertIntoChatGptComposerVerified(message);
    if (outcome === "inserted") {
      if (control) {
        control.textContent = "Inserted";
        control.disabled = true;
      }
      return true;
    }
    const reason = outcome === "composer-not-found"
      ? "ChatGPT composer was not found."
      : "ChatGPT rejected the inserted result. Use Copy Complete Result and paste it manually.";
    this.showError("Status", new Error(reason));
    return false;
  }

  private async submitToolResult(record: ToolRunRecord): Promise<void> {
    if (this.markResultReturnedIfPresent(record)) return;
    await waitSeconds(this.settings.autoInsertDelay);
    if (this.markResultReturnedIfPresent(record)) return;
    const outcome = await this.withComposerAutomation(() =>
      insertAndSubmitToChatGpt(
        this.buildToolResultMessage(record),
        document,
        { autoSubmitDelayMs: this.settings.autoSubmitDelay * 1_000 },
      ),
    );
    if (outcome === "submitted") {
      record.resultSubmitted = true;
      return;
    }
    const reasons: Record<Exclude<typeof outcome, "submitted">, string> = {
      "chat-not-ready": "Automatic result return paused because ChatGPT is still responding. Use Insert Result after the response finishes.",
      "composer-not-empty": "Automatic result return paused because the composer contains a draft.",
      "composer-not-found": "Automatic result return paused because the ChatGPT composer was not found.",
      "composer-rejected-insertion": "ChatGPT rejected the inserted result. Use Copy Complete Result and paste it manually.",
      "send-button-not-found": "Result inserted, but the ChatGPT send button did not become available.",
      "submission-not-accepted": "Result inserted, but ChatGPT did not accept the automatic submission.",
    };
    record.error = reasons[outcome];
  }

  private markResultReturnedIfPresent(record: ToolRunRecord): boolean {
    if (record.resultSubmitted === true) return true;
    const candidates = [...document.querySelectorAll<HTMLElement>("pre, code, [data-message-author-role='user']")]
      .slice(-300)
      .map((node) => node.textContent?.trim() ?? "")
      .filter(Boolean);
    const result = findPlwcToolResultForCall(candidates, record.call.callId);
    if (!result) return false;
    if (result.name !== record.call.name) {
      const message = "A result with this call_id belongs to a different PLwC tool name.";
      record.identityConflict = message;
      record.error = message;
      record.state = "conflict";
      record.resultSubmitted = true;
      this.syncChatCard(record);
      return true;
    }
    record.resultSubmitted = true;
    if (record.result === undefined) {
      record.result = result.result;
      record.chatResult = result.result;
      record.isError = result.is_error;
    }
    if (["scheduled", "awaiting_confirmation"].includes(record.state)) {
      record.state = classifyToolResult(result.is_error, result.result);
    }
    this.syncChatCard(record);
    return true;
  }

  private buildToolResultMessage(record: ToolRunRecord): string {
    if (record.chatResult === undefined) {
      const prepared = prepareToolResultForChat(record.call.name, record.result);
      if (!prepared.ok) this.applyChunkTransportFailure(record, prepared);
      else record.chatResult = prepared.result;
    }
    const continuation = buildOnboardingContinuation(record.call, record.result);
    const correction = buildOnboardingEntryCorrection(record.call, record.result);
    return formatPlwcToolResultMessage({
      call_id: record.call.callId,
      ...(continuation === null ? {} : { continuation }),
      ...(correction === null ? {} : { correction }),
      is_error: record.isError === true,
      name: record.call.name,
      result: record.chatResult,
    });
  }

  private latestToolCallGuidance(): PlwcOnboardingContinuation | PlwcToolCallCorrection | null {
    for (const record of [...this.toolRuns.values()].reverse()) {
      if (record.resultSubmitted !== true) continue;
      const continuation = buildOnboardingContinuation(record.call, record.result);
      if (continuation) return continuation;
      const correction = buildOnboardingEntryCorrection(record.call, record.result);
      if (correction) return correction;
    }
    return null;
  }

  private applyChunkTransportFailure(
    record: ToolRunRecord,
    failure: ToolResultTransportFailure,
  ): void {
    record.chatResult = chunkTransportFailureResult(failure);
    record.error = `Chunk transport validation failed (${failure.code}): ${failure.message}`;
    record.isError = true;
    record.state = "failed";
    this.syncChatCard(record);
    this.renderStatus();
  }

  private syncChatCard(record: ToolRunRecord): void {
    this.chatRenderer?.updateToolRun({
      call: record.call,
      ...(record.error === undefined ? {} : { error: record.error }),
      ...(record.result === undefined
        ? {}
        : { result: record.chatResult ?? presentToolResult(record.call.name, record.result) }),
      ...(record.resultSubmitted === undefined ? {} : { resultSubmitted: record.resultSubmitted }),
      state: record.state,
    });
  }

  private renderSettings(): void {
    const view = this.views.get("Settings");
    if (!view) return;
    view.replaceChildren();
    const toolbar = element("div", "toolbar");
    toolbar.append(element("span", "label", "PLwC CONFIGURATION"), element("span", "spacer"));
    const refresh = button("Refresh");
    refresh.addEventListener("click", () =>
      void this.runAction(refresh, () => this.refreshGatewaySettings()),
    );
    toolbar.append(refresh);
    view.append(toolbar);

    const configuration = element("div", "settings-block");
    configuration.append(
      element(
        "p",
        "settings-source",
        `Source: ${this.gatewaySettings?.source ?? "Connect to load PLwC settings"}`,
      ),
    );
    const form = element("form", "configuration-form");
    const fields = new Map<keyof GatewaySettingsUpdate, HTMLInputElement | HTMLSelectElement>();
    const addInput = (
      key: keyof GatewaySettingsUpdate,
      label: string,
      type: "text" | "number",
    ) => {
      const field = element("label", "configuration-field");
      const input = element("input") as HTMLInputElement;
      input.type = type;
      input.value = this.gatewaySettings?.[key] ?? "";
      input.placeholder = "PLwC default";
      input.autocomplete = "off";
      input.spellcheck = false;
      if (type === "number") {
        input.min = "0";
        input.max = "1000000";
        input.step = "1";
      }
      field.append(element("span", "", label), input);
      fields.set(key, input);
      form.append(field);
    };
    const addBoolean = (key: keyof GatewaySettingsUpdate, label: string) => {
      const field = element("label", "configuration-field");
      const select = element("select") as HTMLSelectElement;
      const options: Array<[string, string]> = [["", "PLwC default"], ["true", "true"], ["false", "false"]];
      for (const [value, text] of options) {
        const option = element("option", "", text) as HTMLOptionElement;
        option.value = value;
        select.append(option);
      }
      select.value = this.gatewaySettings?.[key] ?? "";
      field.append(element("span", "", label), select);
      fields.set(key, select);
      form.append(field);
    };

    addInput("workspacePath", "Workspace path", "text");
    addInput("profilesPath", "Profiles path", "text");
    addInput("activeProfileName", "Bootstrap profile fallback", "text");
    addInput("securityConfig", "Security config", "text");
    addInput("memoryWriteThreshold", "Memory write threshold", "number");
    addInput("personaWriteThreshold", "Persona write threshold", "number");
    addInput("temperamentWriteThreshold", "Temperament threshold", "number");
    addBoolean("qdrantEnabled", "Qdrant enabled");
    addBoolean("personaLayerDisabled", "Persona layer disabled");

    const actions = element("div", "toolbar configuration-actions");
    const save = button("Save & Restart", "command-button");
    save.type = "submit";
    const reset = button("Use Imported Settings");
    actions.append(save, reset);
    form.append(actions);

    const fieldValue = (key: keyof GatewaySettingsUpdate): string | null => {
      const value = fields.get(key)?.value.trim() ?? "";
      return value === "" ? null : value;
    };
    const readUpdate = (): GatewaySettingsUpdate => {
      const update: GatewaySettingsUpdate = {
        activeProfileName: fieldValue("activeProfileName"),
        memoryWriteThreshold: fieldValue("memoryWriteThreshold"),
        personaLayerDisabled: fieldValue("personaLayerDisabled"),
        personaWriteThreshold: fieldValue("personaWriteThreshold"),
        profilesPath: fieldValue("profilesPath"),
        qdrantEnabled: fieldValue("qdrantEnabled"),
        securityConfig: fieldValue("securityConfig"),
        temperamentWriteThreshold: fieldValue("temperamentWriteThreshold"),
        workspacePath: fieldValue("workspacePath"),
      };
      for (const key of ["workspacePath", "profilesPath", "securityConfig"] as const) {
        const value = update[key];
        if (value !== null && !/^(?:[A-Za-z]:[\\/]|\\\\|\/)/u.test(value)) {
          throw new Error(`${key} must be an absolute path.`);
        }
      }
      for (const key of ["memoryWriteThreshold", "personaWriteThreshold", "temperamentWriteThreshold"] as const) {
        const value = update[key];
        if (value !== null && (!/^(?:0|[1-9][0-9]*)$/u.test(value) || Number(value) > 1_000_000)) {
          throw new Error(`${key} must be a nonnegative integer.`);
        }
      }
      return update;
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const originalLabel = save.textContent;
      save.disabled = true;
      reset.disabled = true;
      save.textContent = "Restarting...";
      void (async () => {
        try {
          this.gatewaySettings = await this.client.updateGatewaySettings(readUpdate());
          await this.refreshTools();
          this.statusValue = await this.client.status();
          this.renderSettings();
          this.renderStatus();
        } catch (error) {
          this.showError("Settings", error);
          save.disabled = false;
          reset.disabled = false;
          save.textContent = originalLabel;
        }
      })();
    });
    reset.addEventListener("click", () =>
      void this.runAction(reset, async () => {
        save.disabled = true;
        this.gatewaySettings = await this.client.resetGatewaySettings();
        await this.refreshTools();
        this.statusValue = await this.client.status();
        this.renderSettings();
        this.renderStatus();
      }),
    );
    configuration.append(form);
    view.append(configuration, element("div", "label settings-section-label", "BRIDGE BEHAVIOR"));

    const block = element("div", "settings-block behavior-settings");
    type BooleanBridgeSetting =
      | "renderChatCards"
      | "readOnlyAutoRun"
      | "autoConfirmWrites"
      | "autoConfirmSandbox"
      | "autoSubmitResults";
    const behaviors: Array<[BooleanBridgeSetting, string]> = [
      ["renderChatCards", "Render PLwC calls and results as terminal cards in the chat."],
      ["readOnlyAutoRun", "Automatically execute only operations classified as read-only."],
      ["autoConfirmWrites", "Automatically confirm and execute recognized PLwC write operations."],
      ["autoConfirmSandbox", "Automatically confirm and execute PLwC sandbox operations."],
      ["autoSubmitResults", "Automatically submit results after read-only or explicitly confirmed calls."],
    ];
    for (const [key, label] of behaviors) {
      const row = element("label", "setting-row");
      const checkbox = element("input") as HTMLInputElement;
      checkbox.type = "checkbox";
      checkbox.checked = this.settings[key];
      checkbox.addEventListener("change", async () => {
        checkbox.disabled = true;
        try {
          this.settings = await this.client.updateSettings({ [key]: checkbox.checked });
          this.chatRenderer?.setEnabled(this.settings.renderChatCards);
          if (checkbox.checked && (key === "autoConfirmWrites" || key === "autoConfirmSandbox")) {
            this.resumeEligibleAutomaticCalls();
          }
        } catch (error) {
          checkbox.checked = this.settings[key];
          this.showError("Settings", error);
        } finally {
          checkbox.disabled = false;
        }
      });
      row.append(checkbox, element("span", "", label));
      block.append(row);
      if (key === "autoConfirmWrites") {
        block.append(
          element(
            "p",
            "danger-text setting-warning",
            "WARNING: Recognized writes run without an individual click and may change workspace files, documents, profiles, or persistent PLwC data. Sandbox operations require their own setting; unknown operations still require confirmation.",
          ),
        );
      }
      if (key === "autoConfirmSandbox") {
        block.append(
          element(
            "p",
            "danger-text setting-warning",
            "WARNING: Sandbox code runs automatically without individual review and can execute programs or change data allowed by the local PLwC sandbox policy. Unknown operations still require confirmation.",
          ),
        );
      }
    }
    block.append(element("div", "label timing-label", "AUTOMATION TIMING (SECONDS)"));
    type TimingBridgeSetting =
      | "autoExecuteDelay"
      | "autoInsertDelay"
      | "autoSubmitDelay"
      | "composerBusyTimeout";
    const timings: Array<[TimingBridgeSetting, string]> = [
      ["autoExecuteDelay", "Auto-execute delay"],
      ["autoInsertDelay", "Auto-insert delay"],
      ["autoSubmitDelay", "Auto-submit delay"],
      ["composerBusyTimeout", "Maximum input lock (0 disables lock)"],
    ];
    const timingGrid = element("div", "timing-grid");
    for (const [key, label] of timings) {
      const field = element("label", "configuration-field timing-field");
      const input = element("input") as HTMLInputElement;
      input.type = "number";
      input.min = "0";
      input.max = "60";
      input.step = "0.5";
      input.value = String(this.settings[key]);
      input.addEventListener("change", async () => {
        const value = Number(input.value);
        if (!Number.isFinite(value) || value < 0 || value > 60) {
          input.value = String(this.settings[key]);
          this.showError("Settings", new Error(`${label} must be between 0 and 60 seconds.`));
          return;
        }
        input.disabled = true;
        try {
          this.settings = await this.client.updateSettings({ [key]: Math.round(value * 10) / 10 });
          input.value = String(this.settings[key]);
          if (key === "composerBusyTimeout") {
            this.composerBusyGate.updateTimeout(this.settings.composerBusyTimeout);
          }
        } catch (error) {
          input.value = String(this.settings[key]);
          this.showError("Settings", error);
        } finally {
          input.disabled = false;
        }
      });
      field.append(element("span", "", label), input);
      timingGrid.append(field);
    }
    block.append(timingGrid);
    block.append(
      element(
        "p",
        "muted",
        "The input unlocks when the complete PLwC result pipeline finishes. The maximum timeout and Unlock input release only the input; they do not cancel the running operation.",
      ),
    );
    block.append(element("p", "muted", "Endpoint remains fixed to IPv4 loopback."));
    view.append(block);
  }

  private applyLayout(): void {
    this.resizeTimer = null;
    const leftNavigationRight = findLeftNavigationRight();
    const layout = calculatePanelLayout({
      leftNavigationRight,
      userCollapsed: this.userCollapsed,
      viewportWidth: window.innerWidth,
    });
    this.root.style.setProperty("--plwc-panel-width", `${layout.width}px`);
    this.root.classList.toggle("is-collapsed", layout.collapsed);
    this.chatRenderer?.setRightReserve(layout.collapsed ? 0 : layout.width + PANEL_GAP * 2);
    this.launcher.disabled = !layout.canOpen;
    this.launcher.title = layout.canOpen
      ? "Open PLwC Chat Bridge"
      : "PLwC Chat Bridge is collapsed to keep the chat navigation reachable";
    this.positionComposerLauncher(leftNavigationRight, layout.canOpen, layout.collapsed);
  }

  private scheduleLayout(): void {
    if (this.resizeTimer) clearTimeout(this.resizeTimer);
    this.resizeTimer = setTimeout(() => this.applyLayout(), 120);
  }

  private positionComposerLauncher(leftNavigationRight: number, canOpen: boolean, collapsed: boolean): void {
    const detectedComposer = findChatGptComposer();
    const composer = detectedComposer ?? (
      this.composerBusyGate.blocking && this.composerLock?.composer.isConnected
        ? this.composerLock.composer
        : null
    );
    if (!composer) {
      this.composerLauncher.classList.add("is-hidden");
      this.root.classList.remove("has-composer-launcher");
      this.syncComposerBusyOverlay(null, null);
      return;
    }
    const composerRect = composer.getBoundingClientRect();
    const surfaceRect = findChatGptComposerSurface(composer).getBoundingClientRect();
    const position = calculateComposerLauncherPosition({
      composer: {
        bottom: surfaceRect.bottom,
        left: composerRect.left,
        right: composerRect.right,
        top: surfaceRect.top,
      },
      leftNavigationRight,
      viewportHeight: window.innerHeight,
      viewportWidth: window.innerWidth,
    });
    this.composerLauncher.style.left = `${position.left}px`;
    this.composerLauncher.style.top = `${position.top}px`;
    this.composerLauncher.disabled = !canOpen;
    this.composerLauncher.setAttribute("aria-pressed", String(!collapsed));
    this.composerLauncher.classList.toggle("is-hidden", !position.visible);
    this.root.classList.toggle("has-composer-launcher", position.visible);
    this.syncComposerBusyOverlay(composer, surfaceRect);
  }

  private beginToolCall(callKey: string): void {
    this.composerBusyGate.begin(callKey, this.settings.composerBusyTimeout);
  }

  private endToolCall(callKey: string): void {
    this.composerBusyGate.end(callKey);
  }

  private syncComposerBusyState(): void {
    if (this.composerBusyGate.blocking && this.composerBusyTimer === null) {
      this.composerBusyDotCount = 1;
      this.composerBusyDots.textContent = ".";
      this.composerBusyTimer = setInterval(() => {
        this.composerBusyDotCount = this.composerBusyDotCount % 3 + 1;
        this.composerBusyDots.textContent = ".".repeat(this.composerBusyDotCount);
      }, 500);
    }
    if (!this.composerBusyGate.blocking && this.composerBusyTimer !== null) {
      clearInterval(this.composerBusyTimer);
      this.composerBusyTimer = null;
    }
    this.applyLayout();
  }

  private syncComposerBusyOverlay(composer: HTMLElement | null, surfaceRect: DOMRect | null): void {
    if (!this.composerBusyGate.blocking || composer === null || surfaceRect === null) {
      this.composerBusyOverlay.classList.add("is-hidden");
      this.releaseComposerDomLock();
      return;
    }

    const overlay = calculateComposerBusyOverlayPosition(surfaceRect);
    this.composerBusyOverlay.style.left = `${overlay.left}px`;
    this.composerBusyOverlay.style.top = `${overlay.top}px`;
    this.composerBusyOverlay.style.width = `${overlay.width}px`;
    this.composerBusyOverlay.style.height = `${overlay.height}px`;
    this.composerBusyOverlay.classList.remove("is-hidden");
    if (!this.composerBusyGate.locksComposerDom) {
      this.releaseComposerDomLock();
      return;
    }
    if (this.composerLock?.composer !== composer) {
      this.releaseComposerDomLock();
      this.composerLock = lockChatGptComposerElement(composer);
    }
  }

  private releaseComposerDomLock(): void {
    if (this.composerLock === null) return;
    unlockChatGptComposerElement(this.composerLock);
    this.composerLock = null;
  }

  private async withComposerAutomation<T>(action: () => Promise<T>): Promise<T> {
    this.composerBusyGate.beginAutomation();
    try {
      return await action();
    } finally {
      this.composerBusyGate.endAutomation();
    }
  }

  private async runAction(control: HTMLButtonElement, action: () => Promise<void>): Promise<void> {
    const label = control.textContent ?? "Action";
    control.disabled = true;
    control.textContent = text("working", this.language);
    try {
      await action();
    } catch (error) {
      this.showError(this.activeTab, error);
    } finally {
      control.textContent = label;
      control.disabled = false;
    }
  }

  private showError(tab: TabName, error: unknown): void {
    const view = this.views.get(tab);
    if (!view) return;
    const rawMessage = error instanceof Error ? error.message : text("unexpected_error", this.language);
    const message = tab === "Status"
      ? localizeBridgeError(rawMessage, this.language)
      : rawMessage;
    const notice = element("p", "error-text", message);
    view.prepend(notice);
  }
}
