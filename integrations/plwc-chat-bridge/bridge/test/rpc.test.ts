import assert from "node:assert/strict";
import test from "node:test";

import { parseRequest, RpcFault } from "../src/rpc.js";

test("accepts JSON-RPC 2.0 requests with numeric IDs", () => {
  assert.deepEqual(parseRequest('{"jsonrpc":"2.0","id":7,"method":"ping"}'), {
    jsonrpc: "2.0",
    id: 7,
    method: "ping",
  });
});

test("rejects string IDs, notifications, batches and invalid JSON", () => {
  for (const source of [
    '{"jsonrpc":"2.0","id":"7","method":"ping"}',
    '{"jsonrpc":"2.0","method":"ping"}',
    '[{"jsonrpc":"2.0","id":1,"method":"ping"}]',
    "not-json",
  ]) {
    assert.throws(() => parseRequest(source), RpcFault);
  }
});
