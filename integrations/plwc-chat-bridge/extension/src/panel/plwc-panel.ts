import { BridgeClient } from "../content/bridge-client";
import {
  findChatGptComposer,
  insertAndSubmitToChatGpt,
  insertIntoChatGptComposer,
} from "../content/composer";
import type { ChatRunState, PlwcChatRenderer } from "../content/chat-renderer";
import type { ParsedPlwcToolCall } from "../content/tool-call-parser";
import { formatPlwcToolResultMessage } from "../content/tool-result-message";
import { buildPrimer, type BridgePrimer } from "../primer/build-primer";
import { shouldAutoRun, shouldAutoSubmitResult } from "../shared/automation";
import type { McpTool } from "../shared/contracts";
import type {
  BridgeSettings,
  BridgeStatus,
  GatewaySettingsSnapshot,
  ToolListResponse,
} from "../shared/messages";
import { decidePolicy, POLICY_ROWS } from "../shared/policy";
import { presentToolResult } from "../shared/tool-result";
import {
  calculateComposerLauncherPosition,
  calculatePanelLayout,
  findLeftNavigationRight,
  PANEL_GAP,
} from "./layout";
import { TERMINAL_THEME } from "./theme";

const TAB_NAMES = ["PLwC Tools", "Primer", "Policy", "Status", "Settings"] as const;
type TabName = (typeof TAB_NAMES)[number];
type RunState = ChatRunState;

interface ToolRunRecord {
  call: ParsedPlwcToolCall;
  state: RunState;
  result?: unknown;
  resultSubmitted?: boolean;
  isError?: boolean;
  error?: string;
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

export class PlwcPanel {
  private readonly root = element("div", "bridge-root");
  private readonly panel = element("section", "bridge-panel");
  private readonly launcher = button("", "bridge-launcher");
  private readonly composerLauncher = button("", "composer-launcher is-hidden");
  private readonly statusDot = element("span", "status-dot");
  private readonly views = new Map<TabName, HTMLElement>();
  private activeTab: TabName = "PLwC Tools";
  private userCollapsed: boolean | undefined;
  private tools: McpTool[] = [];
  private primer: BridgePrimer | null = null;
  private statusValue: BridgeStatus | null = null;
  private settings: BridgeSettings = {
    autoSubmitResults: true,
    readOnlyAutoRun: true,
    renderChatCards: true,
  };
  private gatewaySettings: GatewaySettingsSnapshot | null = null;
  private readonly toolRuns = new Map<string, ToolRunRecord>();
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
    if (this.toolRuns.has(call.callKey)) return;
    const record: ToolRunRecord = { call, state: "scheduled" };
    this.toolRuns.set(call.callKey, record);
    this.syncChatCard(record);
    this.renderStatus();
    const policy = decidePolicy(call.name, { ...call.arguments });
    if (shouldAutoRun(this.settings, policy)) {
      void this.executeToolCall(call.callKey, false);
    }
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

  private async refreshTools(): Promise<void> {
    this.statusValue = await this.client.connect();
    const response = await this.client.listTools();
    this.acceptToolList(response);
  }

  private async refreshGatewaySettings(): Promise<void> {
    this.statusValue = await this.client.connect();
    this.gatewaySettings = await this.client.getGatewaySettings();
    this.renderSettings();
  }

  private async refreshConnectionStatus(): Promise<void> {
    try {
      this.statusValue = await this.client.connect();
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
    insert.addEventListener("click", () => {
      if (!this.primer || !insertIntoChatGptComposer(this.primer.text)) {
        this.showError("Primer", new Error("ChatGPT composer was not found."));
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
    toolbar.append(element("span", "label", "LOCAL STATUS"), element("span", "spacer"));
    const reconnect = button("Reconnect");
    toolbar.append(reconnect);
    view.append(toolbar);
    const values = this.statusValue ?? {
      connection: "disconnected",
      endpoint: "ws://127.0.0.1:3007/message",
      lastError: "",
      pendingRequests: 0,
      toolSet: null,
    };
    this.statusDot.className = `status-dot ${values.connection}`;
    const grid = element("dl", "status-grid");
    for (const [label, value] of [
      ["Bridge", values.connection],
      ["Endpoint", values.endpoint],
      ["Tools", `${this.tools.length} / 8`],
      ["Pending", String(values.pendingRequests)],
      ["Error", values.lastError || "none"],
    ]) {
      grid.append(element("dt", "", label), element("dd", "", value));
    }
    const runtime = button("Run Runtime Status", "command-button");
    runtime.disabled = this.tools.length !== 8;
    const result = element("pre", "", "No status call run in this panel session.");
    reconnect.addEventListener("click", () => void this.runAction(reconnect, () => this.refreshTools()));
    runtime.addEventListener("click", () =>
      void this.runAction(runtime, async () => {
        const response = await this.client.callTool("plwc_status", { scope: "runtime" });
        this.statusValue = await this.client.status();
        result.textContent = boundedJson(presentToolResult("plwc_status", response.result), 5_000);
      }),
    );
    view.append(grid, runtime, result);
    view.append(this.renderToolRuns());
  }

  private renderToolRuns(): HTMLElement {
    const section = element("section", "run-queue");
    section.append(element("div", "label", "DETECTED TOOL CALLS"));
    if (this.toolRuns.size === 0) {
      section.append(element("p", "muted", "No visible PLwC JSONL call detected in this chat."));
      return section;
    }

    for (const record of this.toolRuns.values()) {
      const policy = decidePolicy(record.call.name, { ...record.call.arguments });
      const card = element("article", "run-card");
      const header = element("div", "run-header");
      header.append(
        element("code", "tool-name", record.call.name),
        element("span", `run-state ${record.state}`, record.state.toUpperCase()),
      );
      card.append(header, element("pre", "run-arguments", boundedJson(record.call.arguments, 4_000)));

      const actions = element("div", "toolbar");
      const run = button(policy.requiresConfirmation ? "Confirm & Run" : "Run", "command-button");
      const terminalState = ["running", "succeeded", "denied", "unknown"].includes(record.state);
      run.disabled = terminalState || policy.requiresConfirmation;
      if (policy.requiresConfirmation && record.state === "scheduled") {
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
      if (record.result !== undefined && canInsertResult) {
        const insert = button("Insert Result");
        insert.addEventListener("click", () => {
          if (!this.insertToolResult(record)) return;
          insert.textContent = "Inserted";
          insert.disabled = true;
        });
        actions.append(insert);
      }
      card.append(actions);
      if (record.error) card.append(element("p", "error-text", record.error));
      if (record.result !== undefined) {
        card.append(
          element("pre", "run-result", boundedJson(presentToolResult(record.call.name, record.result), 5_000)),
        );
      }
      section.append(card);
    }
    return section;
  }

  private async runToolCallFromChat(call: ParsedPlwcToolCall, confirmed: boolean): Promise<void> {
    if (!this.toolRuns.has(call.callKey)) {
      const record: ToolRunRecord = { call, state: "scheduled" };
      this.toolRuns.set(call.callKey, record);
      this.syncChatCard(record);
    }
    await this.executeToolCall(call.callKey, confirmed);
  }

  private async executeToolCall(callKey: string, confirmed: boolean): Promise<void> {
    const record = this.toolRuns.get(callKey);
    if (!record || record.state !== "scheduled" && record.state !== "failed") return;
    const policy = decidePolicy(record.call.name, { ...record.call.arguments });
    if (policy.requiresConfirmation && !confirmed) return;
    record.state = "running";
    record.error = undefined;
    record.result = undefined;
    record.isError = undefined;
    record.resultSubmitted = undefined;
    this.syncChatCard(record);
    this.renderStatus();
    try {
      const response = await this.client.callTool(record.call.name, { ...record.call.arguments }, confirmed);
      record.result = response.result;
      record.isError = response.isError;
      const serialized = boundedJson(response.result).toLowerCase();
      if (response.isError) {
        record.state = /denied|policy/.test(serialized) ? "denied" : "failed";
        if (record.state === "failed") record.error = "PLwC returned an error result.";
      } else {
        record.state = "succeeded";
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
    this.syncChatCard(record);
    this.renderStatus();
  }

  private insertToolResultForCall(call: ParsedPlwcToolCall): void {
    const record = this.toolRuns.get(call.callKey);
    if (record) this.insertToolResult(record);
  }

  private insertToolResult(record: ToolRunRecord): boolean {
    const message = this.buildToolResultMessage(record);
    if (insertIntoChatGptComposer(message)) return true;
    this.showError("Status", new Error("ChatGPT composer was not found."));
    return false;
  }

  private async submitToolResult(record: ToolRunRecord): Promise<void> {
    const outcome = await insertAndSubmitToChatGpt(this.buildToolResultMessage(record));
    if (outcome === "submitted") {
      record.resultSubmitted = true;
      return;
    }
    const reasons: Record<Exclude<typeof outcome, "submitted">, string> = {
      "composer-not-empty": "Automatic result return paused because the composer contains a draft.",
      "composer-not-found": "Automatic result return paused because the ChatGPT composer was not found.",
      "send-button-not-found": "Result inserted, but the ChatGPT send button did not become available.",
      "submission-not-accepted": "Result inserted, but ChatGPT did not accept the automatic submission.",
    };
    record.error = reasons[outcome];
  }

  private buildToolResultMessage(record: ToolRunRecord): string {
    return formatPlwcToolResultMessage({
      call_id: record.call.callId,
      is_error: record.isError === true,
      name: record.call.name,
      result: presentToolResult(record.call.name, record.result),
    });
  }

  private syncChatCard(record: ToolRunRecord): void {
    this.chatRenderer?.updateToolRun({
      call: record.call,
      ...(record.error === undefined ? {} : { error: record.error }),
      ...(record.result === undefined ? {} : { result: presentToolResult(record.call.name, record.result) }),
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
    const values: Array<[string, string | null | undefined]> = [
      ["Workspace path", this.gatewaySettings?.workspacePath],
      ["Profiles path", this.gatewaySettings?.profilesPath],
      ["Active profile", this.gatewaySettings?.activeProfileName],
      ["Security config", this.gatewaySettings?.securityConfig],
      ["Memory write threshold", this.gatewaySettings?.memoryWriteThreshold],
      ["Persona write threshold", this.gatewaySettings?.personaWriteThreshold],
      ["Temperament threshold", this.gatewaySettings?.temperamentWriteThreshold],
      ["Qdrant enabled", this.gatewaySettings?.qdrantEnabled],
      ["Persona layer disabled", this.gatewaySettings?.personaLayerDisabled],
    ];
    const grid = element("dl", "configuration-grid");
    const emptyValue = this.gatewaySettings ? "PLwC default" : "not loaded";
    for (const [label, value] of values) {
      grid.append(
        element("dt", "", label),
        element("dd", value ? "" : "muted", value ?? emptyValue),
      );
    }
    configuration.append(grid);
    view.append(configuration, element("div", "label settings-section-label", "BRIDGE BEHAVIOR"));

    const block = element("div", "settings-block behavior-settings");
    const behaviors: Array<[keyof BridgeSettings, string]> = [
      ["renderChatCards", "Render PLwC calls and results as terminal cards in the chat."],
      ["readOnlyAutoRun", "Automatically execute only operations classified as read-only."],
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
        } catch (error) {
          checkbox.checked = this.settings[key];
          this.showError("Settings", error);
        } finally {
          checkbox.disabled = false;
        }
      });
      row.append(checkbox, element("span", "", label));
      block.append(row);
    }
    block.append(element("p", "muted", "Endpoint is fixed to IPv4 loopback in rc19.dev4."));
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
    const composer = findChatGptComposer();
    if (!composer) {
      this.composerLauncher.classList.add("is-hidden");
      this.root.classList.remove("has-composer-launcher");
      return;
    }
    const position = calculateComposerLauncherPosition({
      composer: composer.getBoundingClientRect(),
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
  }

  private async runAction(control: HTMLButtonElement, action: () => Promise<void>): Promise<void> {
    const label = control.textContent ?? "Action";
    control.disabled = true;
    control.textContent = "Working...";
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
    const message = error instanceof Error ? error.message : "Unexpected PLwC Chat Bridge error.";
    const notice = element("p", "error-text", message);
    view.prepend(notice);
  }
}
