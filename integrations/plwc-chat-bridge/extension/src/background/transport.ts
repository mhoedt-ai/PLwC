import type { ConnectionState } from "../shared/messages";

interface JsonRpcResponse {
  id: number;
  jsonrpc: "2.0";
  result?: unknown;
  error?: { code?: number; message?: string; data?: unknown };
}

export interface WebSocketLike {
  readyState: number;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onopen: ((event: Event) => void) | null;
  close(): void;
  send(data: string): void;
}

export type WebSocketFactory = (endpoint: string) => WebSocketLike;

interface PendingRequest {
  reject: (error: Error) => void;
  resolve: (value: unknown) => void;
  timeout: ReturnType<typeof setTimeout>;
}

export class RpcRequestError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "RpcRequestError";
  }
}

export class JsonRpcWebSocketClient {
  private socket: WebSocketLike | null = null;
  private connectionPromise: Promise<void> | null = null;
  private nextRequestId = 1;
  private readonly pending = new Map<number, PendingRequest>();
  private stateValue: ConnectionState = "disconnected";
  private lastErrorValue = "";
  private readonly listeners = new Set<(state: ConnectionState, error: string) => void>();

  constructor(
    readonly endpoint: string,
    private readonly requestTimeoutMs = 15_000,
    private readonly socketFactory: WebSocketFactory = (url) => new WebSocket(url),
  ) {}

  get state(): ConnectionState {
    return this.stateValue;
  }

  get lastError(): string {
    return this.lastErrorValue;
  }

  get pendingCount(): number {
    return this.pending.size;
  }

  onStateChange(listener: (state: ConnectionState, error: string) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async connect(): Promise<void> {
    if (this.socket?.readyState === 1) return;
    if (this.connectionPromise) return this.connectionPromise;

    this.setState("connecting", "");
    this.connectionPromise = new Promise<void>((resolve, reject) => {
      const socket = this.socketFactory(this.endpoint);
      this.socket = socket;

      socket.onopen = () => {
        this.connectionPromise = null;
        this.setState("connected", "");
        resolve();
      };
      socket.onmessage = (event) => this.handleMessage(event.data);
      socket.onerror = () => {
        this.setState("error", "WebSocket connection failed.");
      };
      socket.onclose = () => {
        const wasConnecting = this.connectionPromise !== null;
        this.connectionPromise = null;
        this.socket = null;
        const error = new RpcRequestError("WebSocket connection closed.", "connection_closed");
        this.rejectAll(error);
        this.setState("disconnected", error.message);
        if (wasConnecting) reject(error);
      };
    });

    return this.connectionPromise;
  }

  async request(method: string, params: unknown): Promise<unknown> {
    await this.connect();
    const socket = this.socket;
    if (!socket || socket.readyState !== 1) {
      throw new RpcRequestError("WebSocket is not connected.", "not_connected");
    }

    const id = this.nextRequestId++;
    return new Promise<unknown>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new RpcRequestError(`JSON-RPC request timed out after ${this.requestTimeoutMs} ms.`, "timeout"));
      }, this.requestTimeoutMs);
      this.pending.set(id, { reject, resolve, timeout });
      socket.send(JSON.stringify({ id, jsonrpc: "2.0", method, params }));
    });
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
    this.connectionPromise = null;
  }

  private handleMessage(raw: unknown): void {
    if (typeof raw !== "string") return;
    let response: JsonRpcResponse;
    try {
      response = JSON.parse(raw) as JsonRpcResponse;
    } catch {
      this.setState("error", "Bridge returned invalid JSON.");
      return;
    }
    if (typeof response.id !== "number") return;

    const request = this.pending.get(response.id);
    if (!request) return;
    this.pending.delete(response.id);
    clearTimeout(request.timeout);

    if (response.error) {
      request.reject(
        new RpcRequestError(response.error.message || "JSON-RPC request failed.", `rpc_${response.error.code ?? "error"}`),
      );
      return;
    }
    request.resolve(response.result);
  }

  private rejectAll(error: Error): void {
    for (const request of this.pending.values()) {
      clearTimeout(request.timeout);
      request.reject(error);
    }
    this.pending.clear();
  }

  private setState(state: ConnectionState, error: string): void {
    this.stateValue = state;
    this.lastErrorValue = error;
    for (const listener of this.listeners) listener(state, error);
  }
}
