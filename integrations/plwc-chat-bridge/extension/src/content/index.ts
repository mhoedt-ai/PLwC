import { BridgeClient } from "./bridge-client";
import { PlwcChatRenderer } from "./chat-renderer";
import { observePlwcChainStalls } from "./chain-recovery";
import { observePlwcToolCalls } from "./tool-call-observer";
import { PlwcPanel } from "../panel/plwc-panel";
import { shouldClaimPlwcHost, type PlwcHostOwner } from "./host-ownership";

const HOST_ID = "plwc-chat-bridge-host";
const ALLOWED_HOSTS = new Set(["chatgpt.com", "chat.openai.com"]);

const currentOwner: PlwcHostOwner = {
  extensionId: chrome.runtime.id,
  packageVersion: chrome.runtime.getManifest().version,
};
const existingHost = document.getElementById(HOST_ID);
const existingOwner = existingHost?.dataset.plwcExtensionId
  ? {
      extensionId: existingHost.dataset.plwcExtensionId,
      packageVersion: existingHost.dataset.plwcExtensionVersion ?? "unknown",
    }
  : null;

if (ALLOWED_HOSTS.has(location.hostname) && shouldClaimPlwcHost(currentOwner, existingOwner)) {
  existingHost?.remove();
  const host = document.createElement("div");
  host.id = HOST_ID;
  host.dataset.plwcExtensionId = currentOwner.extensionId;
  host.dataset.plwcExtensionVersion = currentOwner.packageVersion;
  const shadowRoot = host.attachShadow({ mode: "open" });
  document.documentElement.append(host);
  const chatRenderer = new PlwcChatRenderer();
  const panel = new PlwcPanel(shadowRoot, new BridgeClient(), chatRenderer);
  panel.mount();
  chatRenderer.mount();
  observePlwcToolCalls({
    onCall: (call) => panel.offerToolCall(call),
    onConflict: (conflict) => panel.offerToolCallConflict(conflict),
  });
  observePlwcChainStalls(() => panel.recoverStalledChain());
}
