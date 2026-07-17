import assert from "node:assert/strict";
import test from "node:test";

import { buildPrimer } from "./build-primer";
import { CANONICAL_TOOL_NAMES } from "../shared/contracts";

const tools = CANONICAL_TOOL_NAMES.map((name) => ({
  description: `${name} description`,
  inputSchema: { properties: { operation: { type: "string" } }, type: "object" },
  name,
}));

test("builds the same primer and schema hash for equivalent tool sets", async () => {
  const first = await buildPrimer({ tools });
  const second = await buildPrimer({ tools: [...tools].reverse() });
  assert.equal(first.hash, second.hash);
  assert.equal(first.text, second.text);
  assert.match(first.text, /plwc_governor/);
  assert.match(first.text, /always requires explicit confirmation/);
});

test("fails closed when an extra tool is advertised", async () => {
  await assert.rejects(
    buildPrimer({ tools: [...tools, { inputSchema: { type: "object" }, name: "unsafe_extra" }] }),
    /contract mismatch/,
  );
});
