import type { JsonObject } from "../shared/contracts";
import type {
  BridgeRequest,
  BridgeResponse,
  BridgeSettings,
  BridgeStatus,
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";

export class BridgeClient {
  connect(): Promise<BridgeStatus> {
    return this.send<BridgeStatus>({ type: "bridge.connect" });
  }

  status(): Promise<BridgeStatus> {
    return this.send<BridgeStatus>({ type: "bridge.status" });
  }

  listTools(): Promise<ToolListResponse> {
    return this.send<ToolListResponse>({ type: "bridge.tools.list" });
  }

  callTool(name: string, argumentsValue: JsonObject, confirmed = false): Promise<ToolCallResponse> {
    return this.send<ToolCallResponse>({
      arguments: argumentsValue,
      confirmed,
      name,
      type: "bridge.tools.call",
    });
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
      chrome.runtime.sendMessage(request, (response: BridgeResponse<T> | undefined) => {
        const runtimeError = chrome.runtime.lastError;
        if (runtimeError) {
          reject(new Error(runtimeError.message));
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
    });
  }
}
