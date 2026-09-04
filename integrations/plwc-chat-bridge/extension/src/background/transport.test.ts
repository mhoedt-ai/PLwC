import assert from "node:assert/strict";
import test from "node:test";

import { JsonRpcWebSocketClient, RpcRequestError, type WebSocketLike } from "./transport";

class FakeWebSocket implements WebSocketLike {
  readyState = 0;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;
  readonly sent: string[] = [];

  open(): void {
    this.readyState = 1;
    this.onopen?.({} as Event);
  }

  receive(value: unknown): void {
    this.onmessage?.({ data: JSON.stringify(value) } as MessageEvent);
  }

  close(): void {
    this.readyState = 3;
    this.onclose?.({} as CloseEvent);
  }

  send(data: string): void {
    this.sent.push(data);
  }
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

test("keeps a long request alive when request-scoped heartbeats arrive", async () => {
  const socket = new FakeWebSocket();
  const client = new JsonRpcWebSocketClient("ws://127.0.0.1:3007/message", 60, () => socket);
  const request = client.request("tools/call", { name: "plwc_sandbox_run" });
  socket.open();
  await wait(0);

  const sent = JSON.parse(socket.sent[0] ?? "null") as { id: number };
  await wait(35);
  socket.receive({
    jsonrpc: "2.0",
    method: "bridge/heartbeat",
    params: { elapsed_ms: 35, request_id: sent.id },
  });
  await wait(45);
  socket.receive({
    jsonrpc: "2.0",
    method: "bridge/heartbeat",
    params: { elapsed_ms: 80, request_id: sent.id },
  });
  await wait(45);
  socket.receive({ jsonrpc: "2.0", id: sent.id, result: { ok: true } });

  assert.deepEqual(await request, { ok: true });
  assert.equal(client.pendingCount, 0);
});

test("does not resend a request whose response times out after dispatch", async () => {
  const socket = new FakeWebSocket();
  const client = new JsonRpcWebSocketClient("ws://127.0.0.1:3007/message", 20, () => socket);
  const request = client.request("tools/call", { name: "plwc_workspace_operation" });
  socket.open();

  await assert.rejects(request, (error: unknown) => {
    assert.ok(error instanceof RpcRequestError);
    assert.equal(error.code, "timeout");
    assert.equal(error.deliveryState, "outcome_unknown");
    return true;
  });
  assert.equal(socket.sent.length, 1);
  assert.equal(client.pendingCount, 0);
});

test("marks a closed connection after dispatch as outcome unknown without resending", async () => {
  const socket = new FakeWebSocket();
  const client = new JsonRpcWebSocketClient("ws://127.0.0.1:3007/message", 1_000, () => socket);
  const request = client.request("tools/call", { name: "plwc_governor" });
  socket.open();
  await wait(0);
  socket.close();

  await assert.rejects(request, (error: unknown) => {
    assert.ok(error instanceof RpcRequestError);
    assert.equal(error.code, "connection_closed");
    assert.equal(error.deliveryState, "outcome_unknown");
    return true;
  });
  assert.equal(socket.sent.length, 1);
  assert.equal(client.pendingCount, 0);
});
