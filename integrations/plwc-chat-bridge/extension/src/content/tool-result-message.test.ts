import assert from "node:assert/strict";
import test from "node:test";

import {
  formatPlwcToolResultMessage,
  hasPlwcToolResultForCall,
  parsePlwcToolResultFromText,
  parsePlwcToolResultMessage,
} from "./tool-result-message";
import { buildOnboardingContinuation } from "./onboarding-continuation";
import { buildOnboardingEntryCorrection } from "./onboarding-correction";
import {
  chunkTransportFailureResult,
  prepareToolResultForChat,
  presentToolResult,
} from "../shared/tool-result";

test("formats and parses a marked PLwC tool result", () => {
  const message = formatPlwcToolResultMessage({
    call_id: "status-17",
    is_error: false,
    name: "plwc_status",
    result: { ok: true, scope: "runtime" },
  });

  assert.match(message, /^# PLwC Tool Result\n\n```json/u);
  assert.deepEqual(parsePlwcToolResultMessage(message), {
    call_id: "status-17",
    is_error: false,
    name: "plwc_status",
    result: { ok: true, scope: "runtime" },
  });
});

test("round-trips an exact onboarding continuation inside the marked result", () => {
  const continuation = buildOnboardingContinuation(
    {
      arguments: {
        onboarding_answers: { profile_name: "Worker", preferred_name: "Mirco" },
        operation: "plan",
        plan_type: "profile_creation",
        profile: "Worker",
      },
      callId: "profile-plan-001",
      name: "plwc_governor",
    },
    {
      data: { approved_for_apply: true, plan_type: "profile_creation" },
      ok: true,
      operation: "plan",
    },
  );
  assert.ok(continuation);
  const envelope = {
    call_id: "profile-plan-001",
    continuation,
    is_error: false,
    name: "plwc_governor" as const,
    result: { ok: true, operation: "plan" },
  };

  const message = formatPlwcToolResultMessage(envelope);

  assert.deepEqual(parsePlwcToolResultMessage(message), envelope);
});

test("round-trips an exact onboarding entry correction inside the marked result", () => {
  const correction = buildOnboardingEntryCorrection(
    {
      arguments: { operation: "onboarding", scope: "status" },
      callId: "onboarding-describe-001",
      name: "plwc_describe",
    },
    {
      error: "operation filtering is supported only for workspace_operation and document_operation scopes",
      ok: false,
      operation_filter: "onboarding",
    },
  );
  assert.ok(correction);
  const envelope = {
    call_id: "onboarding-describe-001",
    correction,
    is_error: true,
    name: "plwc_describe" as const,
    result: { ok: false, operation_filter: "onboarding" },
  };

  const message = formatPlwcToolResultMessage(envelope);

  assert.deepEqual(parsePlwcToolResultMessage(message), envelope);
});

test("parses the JSON payload rendered inside a chat code block", () => {
  const payload = JSON.stringify({
    call_id: "describe-3",
    name: "plwc_describe",
    result: { tools: 8 },
  });

  assert.deepEqual(parsePlwcToolResultMessage(payload), {
    call_id: "describe-3",
    is_error: false,
    name: "plwc_describe",
    result: { tools: 8 },
  });
});

test("parses the current ChatGPT language label joined directly to result JSON", () => {
  const payload = JSON.stringify({
    call_id: "live-result-1",
    is_error: false,
    name: "plwc_status",
    result: { ok: true, scope: "runtime" },
  });

  for (const text of [`JSON${payload}`, `json ${payload}`]) {
    assert.equal(parsePlwcToolResultMessage(text)?.call_id, "live-result-1");
  }
  assert.equal(parsePlwcToolResultMessage(`javascript${payload}`), null);
});

test("normalizes ChatGPT non-breaking indentation without changing string content", () => {
  const payload = [
    "{",
    '\u00a0\u00a0"call_id": "live-result-nbsp-1",',
    '\u00a0\u00a0"is_error": false,',
    '\u00a0\u00a0"name": "plwc_status",',
    '\u00a0\u00a0"result": {"scope": "run\u00a0time"}',
    "}",
  ].join("\n");

  const parsed = parsePlwcToolResultMessage(`json\n${payload}`);
  assert.equal(parsed?.call_id, "live-result-nbsp-1");
  assert.deepEqual(parsed?.result, { scope: "run\u00a0time" });
});

test("rejects generic and malformed JSON objects", () => {
  assert.equal(parsePlwcToolResultMessage('{"name":"plwc_status","result":{}}'), null);
  assert.equal(
    parsePlwcToolResultMessage('{"call_id":"1","name":"unknown","result":{}}'),
    null,
  );
  assert.equal(
    parsePlwcToolResultMessage('{"call_id":"1","name":"plwc_status","result":{},"run":true}'),
    null,
  );
  assert.equal(
    parsePlwcToolResultMessage(
      '{"call_id":"1","continuation":{},"name":"plwc_status","result":{}}',
    ),
    null,
  );
});

test("detects an existing result for the same call id without matching the tool call", () => {
  const result = formatPlwcToolResultMessage({
    call_id: "sandbox-17",
    is_error: false,
    name: "plwc_sandbox_run",
    result: { ok: true },
  });
  const call = [
    '{"plwc_tool_call":{"name":"plwc_sandbox_run","call_id":"sandbox-17","arguments":{}}}',
  ].join("\n");

  assert.equal(hasPlwcToolResultForCall([call], "sandbox-17"), false);
  assert.equal(hasPlwcToolResultForCall([call, result], "sandbox-17"), true);
  assert.equal(hasPlwcToolResultForCall([result], "sandbox-18"), false);
});

test("detects a result rendered as plain chat message text", () => {
  const result = {
    call_id: "write-17",
    is_error: false,
    name: "plwc_workspace_operation" as const,
    result: { ok: true, operation: "write", path: "PLwC_Entstehung\\09.md" },
  };
  const renderedText = `PLwC Tool Result json ${JSON.stringify(result)} Mehr anzeigen`;

  assert.deepEqual(parsePlwcToolResultFromText(renderedText), result);
  assert.equal(hasPlwcToolResultForCall([renderedText], "write-17"), true);
});

test("formats an oversized compiled layer as complete profile chunks", () => {
  const compiledLayer = "Mirco korrigierte explizit: Meta-Kommentare bleiben erhalten.\n".repeat(500);
  const result = presentToolResult("plwc_profile", {
    data: {
      compile_mode: "full",
      compiled_layer: compiledLayer,
    },
    ok: true,
    policy_decision: "ALLOW",
  });
  const envelope = {
    call_id: "large-1",
    is_error: false,
    name: "plwc_profile" as const,
    result,
  };
  const message = formatPlwcToolResultMessage(envelope);
  const parsed = parsePlwcToolResultMessage(message);
  const parsedResult = parsed?.result as Record<string, unknown>;
  const data = parsedResult.data as Record<string, unknown>;
  const layerTransport = data.compiled_layer_transport as Record<string, unknown>;
  const chunks = layerTransport.chunks as Array<Record<string, unknown>>;
  const reconstructed = chunks.map((chunk) => String(chunk.text)).join("");

  assert.match(message, /plwc_profile_compile_layer_chunks\.v1/u);
  assert.doesNotMatch(message, /content compacted by PLwC Chat Bridge/u);
  assert.deepEqual(parsed, envelope);
  assert.equal(layerTransport.complete, true);
  assert.equal(layerTransport.received_chunks, layerTransport.total_chunks);
  assert.equal(layerTransport.sha256, layerTransport.reconstructed_sha256);
  assert.equal(reconstructed, compiledLayer);
});

test("formats an oversized workspace listing as complete result chunks", () => {
  const entries = Array.from({ length: 500 }, (_, index) => ({
    kind: "file",
    path: `C:\\workspace\\large-export\\file-${index}-${"x".repeat(80)}.dat`,
    size: index,
  }));
  const original = {
    ok: true,
    operation: "list",
    path: "C:\\workspace\\large-export",
    entries,
  };
  const result = presentToolResult("plwc_workspace_operation", original);
  const message = formatPlwcToolResultMessage({
    call_id: "list-500",
    is_error: false,
    name: "plwc_workspace_operation",
    result,
  });
  const parsed = parsePlwcToolResultMessage(message);
  const parsedResult = parsed?.result as Record<string, unknown>;
  const transport = parsedResult.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const reconstructed = chunks.map((chunk) => String(chunk.text)).join("");

  assert.match(message, /plwc_result_chunks\.v1/u);
  assert.deepEqual(parsed?.result, result);
  assert.equal(transport.chunked, true);
  assert.equal(transport.complete, true);
  assert.equal(transport.no_omitted_content, true);
  assert.equal(transport.received_chunks, transport.total_chunks);
  assert.deepEqual(JSON.parse(reconstructed), original);
  assert.equal(message.includes("\n  \"call_id\""), false);
});

test("keeps a large workspace read result complete for ChatGPT submission", () => {
  const content = "AP Grundregeltext mit Kontext.\n".repeat(1_800);
  const original = {
    ok: true,
    operation: "read",
    path: "Wandorra/Spielerhandbuch.txt",
    policy_decision: "ALLOW",
    start_line: 12835,
    end_line: 12985,
    max_bytes: 50_000,
    content,
  };
  const result = presentToolResult("plwc_workspace_operation", original);
  const message = formatPlwcToolResultMessage({
    call_id: "read-50k",
    is_error: false,
    name: "plwc_workspace_operation",
    result,
  });
  const parsed = parsePlwcToolResultMessage(message);
  const parsedResult = parsed?.result as Record<string, unknown>;
  const transport = parsedResult.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const reconstructed = chunks.map((chunk) => String(chunk.text)).join("");

  assert.equal(transport.protocol, "plwc_result_chunks.v1");
  assert.equal(transport.no_omitted_content, true);
  assert.equal(transport.complete, true);
  assert.deepEqual(JSON.parse(reconstructed), original);
  assert.ok(message.length > content.length);
});

test("F-08 preserves a large result call_id through formatting and parsing", () => {
  const original = {
    ok: true,
    payload: "F-08 Korrelation, Größe und Unicode 🙂.\n".repeat(1_800),
  };
  const result = presentToolResult("plwc_reflection", original);
  const message = formatPlwcToolResultMessage({
    call_id: "f-08-large-result-17",
    is_error: false,
    name: "plwc_reflection",
    result,
  });
  const parsed = parsePlwcToolResultMessage(message);

  assert.equal(parsed?.call_id, "f-08-large-result-17");
  assert.equal(parsed?.name, "plwc_reflection");
  assert.deepEqual(parsed?.result, result);
});

test("refuses to format or parse a result with missing chunks", () => {
  const result = structuredClone(
    presentToolResult("plwc_document_operation", {
      ok: true,
      payload: "Document result with integrity evidence.\n".repeat(2_000),
    }),
  ) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  chunks.pop();
  const envelope = {
    call_id: "document-corrupt-1",
    is_error: false,
    name: "plwc_document_operation" as const,
    result,
  };

  assert.throws(
    () => formatPlwcToolResultMessage(envelope),
    /expected .* chunks/u,
  );
  const rawMessage = `# PLwC Tool Result\n\n\`\`\`json\n${JSON.stringify(envelope)}\n\`\`\``;
  assert.equal(parsePlwcToolResultMessage(rawMessage), null);
});

test("F-08 preserves call_id when invalid chunks become a visible error result", () => {
  const result = structuredClone(
    presentToolResult("plwc_status", {
      ok: true,
      payload: "Large status result with transport evidence.\n".repeat(2_000),
    }),
  ) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  transport.complete = false;
  const prepared = prepareToolResultForChat("plwc_status", result);
  assert.equal(prepared.ok, false);
  if (prepared.ok) return;

  const message = formatPlwcToolResultMessage({
    call_id: "f-08-invalid-transport-23",
    is_error: true,
    name: "plwc_status",
    result: chunkTransportFailureResult(prepared),
  });
  const parsed = parsePlwcToolResultMessage(message);

  assert.equal(parsed?.call_id, "f-08-invalid-transport-23");
  assert.equal(parsed?.is_error, true);
  assert.equal(parsed?.name, "plwc_status");
  assert.equal(
    (parsed?.result as Record<string, unknown>).error_detail_category,
    "chunk_transport_invalid",
  );
});
