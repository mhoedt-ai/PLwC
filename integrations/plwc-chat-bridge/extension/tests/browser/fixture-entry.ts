import { PlwcPanel } from "../../src/panel/plwc-panel";
import { BridgeClient } from "../../src/content/bridge-client";
import { PlwcChatRenderer } from "../../src/content/chat-renderer";
import { CANONICAL_TOOL_NAMES } from "../../src/shared/contracts";

const tools = CANONICAL_TOOL_NAMES.map((name) => ({
  name,
  description: `${name} is available through the governed PLwC facade.`,
  inputSchema: {
    type: "object",
    properties: name === "plwc_status" ? { scope: { type: "string", default: "runtime" } } : {},
  },
}));

const validation = {
  valid: true,
  tools,
  missing: [],
  extra: [],
  duplicates: [],
  invalidSchemas: [],
};

const status = {
  connection: "connected",
  endpoint: "ws://127.0.0.1:3007/message",
  lastError: "",
  pendingRequests: 0,
  toolSet: validation,
};

const listeners = new Set<(message: unknown) => void>();
const fakeChrome = {
  runtime: {
    getURL: (path: string) => `./${path}`,
    lastError: undefined,
    onMessage: {
      addListener: (listener: (message: unknown) => void) => listeners.add(listener),
      removeListener: (listener: (message: unknown) => void) => listeners.delete(listener),
    },
    sendMessage: (request: { type: string }, callback?: (response: unknown) => void) => {
      const values: Record<string, unknown> = {
        "bridge.connect": status,
        "bridge.status": status,
        "bridge.tools.list": { tools, validation },
        "bridge.tools.call": { isError: false, policy: { readOnly: true }, result: { ok: true } },
        "bridge.gateway.settings.get": {
          source: "Claude PLwC configuration",
          workspacePath: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
          profilesPath: null,
          activeProfileName: "WasIstDas",
          securityConfig: null,
          memoryWriteThreshold: "2",
          personaWriteThreshold: "3",
          temperamentWriteThreshold: "6",
          qdrantEnabled: "true",
          personaLayerDisabled: "true",
        },
        "bridge.settings.get": {
          autoSubmitResults: true,
          readOnlyAutoRun: true,
          renderChatCards: true,
        },
        "bridge.settings.update": {
          autoSubmitResults: true,
          readOnlyAutoRun: true,
          renderChatCards: true,
        },
      };
      callback?.({ ok: true, value: values[request.type] });
      return Promise.resolve();
    },
  },
};

Object.assign(globalThis.chrome, fakeChrome);

document.querySelector<HTMLButtonElement>("[data-testid='send-button']")?.addEventListener("click", () => {
  const composer = document.querySelector<HTMLElement>("#prompt-textarea");
  if (composer) {
    document.documentElement.dataset.plwcLastSubmittedText = composer.textContent ?? "";
    composer.textContent = "";
  }
});

const navigation = document.querySelector<HTMLElement>("[data-testid='sidebar']");
if (navigation) {
  const rect = navigation.getBoundingClientRect();
  Object.assign(globalThis, { __plwcHostNavigationBefore: { left: rect.left, right: rect.right, width: rect.width } });
}

const host = document.createElement("div");
host.id = "plwc-chat-bridge-host";
const shadowRoot = host.attachShadow({ mode: "open" });
document.documentElement.append(host);
const chatRenderer = new PlwcChatRenderer();
new PlwcPanel(shadowRoot, new BridgeClient(), chatRenderer).mount();
chatRenderer.mount();
