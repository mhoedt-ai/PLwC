import assert from "node:assert/strict";
import test from "node:test";

import { buildPrimer } from "./build-primer";
import { CANONICAL_TOOL_NAMES } from "../shared/contracts";

const tools = CANONICAL_TOOL_NAMES.map((name) => {
  const properties = name === "plwc_status"
    ? { scope: { default: "", type: "string" } }
    : { operation: { type: "string" } };
  return {
    description: `${name} description`,
    inputSchema: { properties, type: "object" },
    name,
  };
});

test("builds the same primer and schema hash for equivalent tool sets", async () => {
  const first = await buildPrimer({ tools });
  const second = await buildPrimer({ tools: [...tools].reverse() });
  assert.equal(first.hash, second.hash);
  assert.equal(first.text, second.text);
  assert.match(first.text, /plwc_governor/);
  assert.match(first.text, /standing write confirmation/);
  assert.match(first.text, /Sandbox execution and unknown operations always require individual confirmation/);
  assert.match(first.text, /fenced jsonl code block/);
  assert.match(first.text, /summarize it naturally/);
  assert.match(first.text, /"type":"function_call_start"/);
  assert.match(first.text, /"key":"scope","type":"parameter","value":"runtime"/);
  assert.match(first.text, /"type":"function_call_end"/);
  assert.doesNotMatch(first.text, /"arguments":\{/);
});

test("fails closed when an extra tool is advertised", async () => {
  await assert.rejects(
    buildPrimer({ tools: [...tools, { inputSchema: { type: "object" }, name: "unsafe_extra" }] }),
    /contract mismatch/,
  );
});
