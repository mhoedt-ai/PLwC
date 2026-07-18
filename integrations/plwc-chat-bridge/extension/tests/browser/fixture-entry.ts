import { PlwcPanel } from "../../src/panel/plwc-panel";
import { BridgeClient } from "../../src/content/bridge-client";
import { PlwcChatRenderer } from "../../src/content/chat-renderer";
import { CANONICAL_TOOL_NAMES } from "../../src/shared/contracts";
import type { BridgeSettings, GatewaySettingsSnapshot, GatewaySettingsUpdate } from "../../src/shared/messages";

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

const importedGatewaySettings: GatewaySettingsSnapshot = {
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
};
let gatewaySettings: GatewaySettingsSnapshot = { ...importedGatewaySettings };
let bridgeSettings: BridgeSettings = {
  autoConfirmWrites: false,
  autoSubmitResults: true,
  readOnlyAutoRun: true,
  renderChatCards: true,
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
    sendMessage: (
      request: { type: string; settings?: GatewaySettingsUpdate | Partial<BridgeSettings> },
      callback?: (response: unknown) => void,
    ) => {
      if (request.type === "bridge.gateway.settings.update" && request.settings) {
        gatewaySettings = { ...(request.settings as GatewaySettingsUpdate), source: "PLwC Chat Bridge saved settings" };
      }
      if (request.type === "bridge.gateway.settings.reset") {
        gatewaySettings = { ...importedGatewaySettings };
      }
      if (request.type === "bridge.settings.update" && request.settings) {
        bridgeSettings = { ...bridgeSettings, ...(request.settings as Partial<BridgeSettings>) };
      }
      const values: Record<string, unknown> = {
        "bridge.connect": status,
        "bridge.status": status,
        "bridge.tools.list": { tools, validation },
        "bridge.tools.call": { isError: false, policy: { readOnly: true }, result: { ok: true } },
        "bridge.gateway.settings.get": gatewaySettings,
        "bridge.gateway.settings.update": gatewaySettings,
        "bridge.gateway.settings.reset": gatewaySettings,
        "bridge.settings.get": bridgeSettings,
        "bridge.settings.update": bridgeSettings,
      };
      callback?.({ ok: true, value: values[request.type] });
      return Promise.resolve();
    },
  },
};

Object.assign(globalThis.chrome, fakeChrome);

document.querySelector<HTMLButtonElement>(".composer-submit-button-color")?.addEventListener("click", () => {
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
