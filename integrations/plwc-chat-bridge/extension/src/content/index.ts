import { BridgeClient } from "./bridge-client";
import { observePlwcToolCalls } from "./tool-call-observer";
import { PlwcPanel } from "../panel/plwc-panel";

const HOST_ID = "plwc-chat-bridge-host";
const ALLOWED_HOSTS = new Set(["chatgpt.com", "chat.openai.com"]);

if (ALLOWED_HOSTS.has(location.hostname) && !document.getElementById(HOST_ID)) {
  const host = document.createElement("div");
  host.id = HOST_ID;
  const shadowRoot = host.attachShadow({ mode: "open" });
  document.documentElement.append(host);
  const panel = new PlwcPanel(shadowRoot, new BridgeClient());
  panel.mount();
  observePlwcToolCalls((call) => panel.offerToolCall(call));
}
