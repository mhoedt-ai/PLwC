import type { JsonObject } from "../shared/contracts";
import type {
  BridgeRequest,
  BridgeResponse,
  BridgeSettings,
  BridgeStatus,
  GatewaySettingsSnapshot,
  GatewaySettingsUpdate,
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";

export function normalizeRuntimeErrorMessage(message: string | undefined): string {
  const value = message?.trim() || "Chrome runtime unavailable.";
  if (/extension context invalidated/i.test(value)) {
    return "PLwC Chat Bridge was reloaded while this ChatGPT tab was open. Reload the ChatGPT tab, then run the PLwC call again.";
  }
  return value;
}

export class BridgeClient {
  connect(autoStart = false): Promise<BridgeStatus> {
    return this.send<BridgeStatus>({ autoStart, type: "bridge.connect" });
  }

  status(): Promise<BridgeStatus> {
    return this.send<BridgeStatus>({ type: "bridge.status" });
  }

  listTools(): Promise<ToolListResponse> {
    return this.send<ToolListResponse>({ type: "bridge.tools.list" });
  }

  callTool(
    name: string,
    argumentsValue: JsonObject,
    confirmed = false,
    identity?: { callId: string; conversationId: string },
  ): Promise<ToolCallResponse> {
    return this.send<ToolCallResponse>({
      arguments: argumentsValue,
      confirmed,
      ...(identity === undefined ? {} : identity),
      name,
      type: "bridge.tools.call",
    });
  }

  getGatewaySettings(): Promise<GatewaySettingsSnapshot> {
    return this.send<GatewaySettingsSnapshot>({ type: "bridge.gateway.settings.get" });
  }

  updateGatewaySettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot> {
    return this.send<GatewaySettingsSnapshot>({ settings, type: "bridge.gateway.settings.update" });
  }

  resetGatewaySettings(): Promise<GatewaySettingsSnapshot> {
    return this.send<GatewaySettingsSnapshot>({ type: "bridge.gateway.settings.reset" });
  }

  getSettings(): Promise<BridgeSettings> {
    return this.send<BridgeSettings>({ type: "bridge.settings.get" });
  }

  updateSettings(settings: Partial<BridgeSettings>): Promise<BridgeSettings> {
    return this.send<BridgeSettings>({ settings, type: "bridge.settings.update" });
  }

  onStatus(listener: (status: BridgeStatus) => void): () => void {
    const handler = (message: unknown) => {
      if (
        typeof message === "object" &&
        message !== null &&
        "type" in message &&
        message.type === "bridge.status.changed" &&
        "value" in message
      ) {
        listener(message.value as BridgeStatus);
      }
    };
    chrome.runtime.onMessage.addListener(handler);
    return () => chrome.runtime.onMessage.removeListener(handler);
  }

  private send<T>(request: BridgeRequest): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      try {
        chrome.runtime.sendMessage(request, (response: BridgeResponse<T> | undefined) => {
          const runtimeError = chrome.runtime.lastError;
          if (runtimeError) {
            reject(new Error(normalizeRuntimeErrorMessage(runtimeError.message)));
            return;
          }
          if (!response) {
            reject(new Error("PLwC Chat Bridge returned no response."));
            return;
          }
          if (!response.ok) {
            reject(new Error(response.error));
            return;
          }
          resolve(response.value);
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : undefined;
        reject(new Error(normalizeRuntimeErrorMessage(message)));
      }
    });
  }
}
