import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";

import { CANONICAL_TOOL_NAMES } from "./contracts";
import {
  assertValidToolResultTransport,
  chunkTransportFailureResult,
  classifyToolResult,
  describeToolResultPresentation,
  normalizeToolResult,
  prepareToolResultForChat,
  presentToolResult,
  toolResultMetadataRows,
  validateToolResultTransport,
} from "./tool-result";

function reconstructedCompileLayer(result: Record<string, unknown>): string {
  const data = result.data as Record<string, unknown>;
  const transport = data.compiled_layer_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  return chunks.map((chunk) => String(chunk.text)).join("");
}

function reconstructGeneralResult(result: Record<string, unknown>): {
  json: string;
  value: unknown;
} {
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const json = chunks.map((chunk) => String(chunk.text)).join("");
  return {
    json,
    value: JSON.parse(json) as unknown,
  };
}

function largeUnicodeResult(toolName: string): Record<string, unknown> {
  return {
    ok: true,
    tool_name: toolName,
    payload: "Größe, Grüße, Prüfung und Kontinuität 🙂 — vollständig.\n".repeat(1_500),
  };
}

function clonedGeneralTransport(): Record<string, unknown> {
  return structuredClone(
    presentToolResult("plwc_status", largeUnicodeResult("plwc_status")),
  ) as Record<string, unknown>;
}

test("prefers structured MCP content and keeps the error flag", () => {
  assert.deepEqual(
    normalizeToolResult({
      content: [{ type: "text", text: "{\"ok\":false}" }],
      structuredContent: { ok: true, value: 42 },
      isError: true,
    }),
    { isError: true, result: { ok: true, value: 42 } },
  );
});

test("parses a single JSON text result when structured content is unavailable", () => {
  assert.deepEqual(
    normalizeToolResult({ content: [{ type: "text", text: "{\"ok\":true}" }], isError: false }),
    { isError: false, result: { ok: true } },
  );
});

test("classifies structured domain failures instead of trusting only the MCP error flag", () => {
  assert.equal(classifyToolResult(false, { ok: true, policy_decision: "ALLOW" }), "succeeded");
  assert.equal(
    classifyToolResult(false, {
      error: "Path is outside the allowed roots.",
      ok: false,
      policy_decision: "DENY",
    }),
    "denied",
  );
  assert.equal(
    classifyToolResult(false, { error: "Source file does not exist.", ok: false, policy_decision: "ALLOW" }),
    "failed",
  );
  assert.equal(
    classifyToolResult(false, {
      error_category: "UNAVAILABLE",
      ok: false,
      policy_decision: "DENY",
    }),
    "failed",
  );
  assert.equal(classifyToolResult(true, { error: "Transport failed." }), "failed");
});

test("maps public gateway results to distinct visible failure labels", () => {
  const cases = [
    [{ error_category: "POLICY_DENY", ok: false }, "policy_denied", "Policy denied"],
    [{ error_category: "INVALID_REQUEST", ok: false }, "validation_failed", "Validation failed"],
    [{ error_category: "NOT_FOUND", ok: false }, "not_found", "Not found"],
    [
      { error_category: "UNAVAILABLE", ok: false, policy_decision: "DENY" },
      "unavailable",
      "Unavailable",
    ],
    [{ error_category: "CONFLICT", ok: false }, "gateway_failed", "Gateway failed"],
  ] as const;

  for (const [result, failureKind, failureLabel] of cases) {
    const presentation = describeToolResultPresentation(
      "plwc_workspace_operation",
      false,
      result,
    );
    assert.equal(presentation.failureKind, failureKind);
    assert.equal(presentation.failureLabel, failureLabel);
  }
  assert.equal(
    describeToolResultPresentation("plwc_status", true, { error: "RPC failed." }).failureLabel,
    "Gateway failed",
  );
});

test("distinguishes transport and artifact validation failures from unavailability", () => {
  const transport = describeToolResultPresentation(
    "plwc_status",
    true,
    {
      error_category: "UNAVAILABLE",
      error_detail_category: "chunk_transport_invalid",
      ok: false,
      transport_error_code: "chunk_hash_mismatch",
      validation_status: "validation_failed",
    },
  );
  const artifactValidation = describeToolResultPresentation(
    "plwc_document_operation",
    true,
    {
      error_category: "UNAVAILABLE",
      error_detail_category: "document_validation_failed",
      ok: false,
      validation_status: "validation_failed",
    },
  );

  assert.equal(transport.failureLabel, "Transport failed");
  assert.equal(artifactValidation.failureLabel, "Validation failed");
});

test("exposes validated and unvalidated artifact provenance without upgrading trust", () => {
  const validated = describeToolResultPresentation(
    "plwc_document_operation",
    false,
    {
      artifact_origin: "document_worker",
      artifact_origin_detail: "document_worker_create_pdf",
      ok: true,
      validation_detail_status: "technically_validated",
      validation_status: "validated",
    },
  );
  const unvalidated = describeToolResultPresentation(
    "plwc_workspace_operation",
    false,
    {
      artifact_origin: "workspace_binary_write",
      ok: true,
      validation_status: "unvalidated",
    },
  );

  assert.equal(validated.artifactOrigin, "document_worker");
  assert.equal(validated.artifactOriginDetail, "document_worker_create_pdf");
  assert.equal(validated.validationStatus, "validated");
  assert.equal(validated.validationLabel, "Validated");
  assert.equal(validated.artifactTrust, "validated");
  assert.equal(unvalidated.artifactOrigin, "workspace_binary_write");
  assert.equal(unvalidated.validationLabel, "Unvalidated");
  assert.equal(unvalidated.artifactTrust, "unvalidated");
  assert.deepEqual(
    toolResultMetadataRows(
      "plwc_workspace_operation",
      false,
      {
        artifact_origin: "workspace_binary_write",
        ok: true,
        validation_status: "unvalidated",
      },
    ),
    [
      { label: "Artifact origin", tone: "default", value: "workspace_binary_write" },
      { label: "Validation", tone: "warning", value: "Unvalidated" },
      {
        label: "Artifact trust",
        tone: "warning",
        value: "UNVALIDATED - do not treat as safe",
      },
    ],
  );
});

test("reads provenance from a validated large-result transport", () => {
  const result = presentToolResult("plwc_document_operation", {
    artifact_origin: "document_worker",
    ok: true,
    payload: "Large validated document evidence.\n".repeat(2_000),
    validation_status: "validated",
  });
  const presentation = describeToolResultPresentation(
    "plwc_document_operation",
    false,
    result,
  );

  assert.equal(presentation.artifactOrigin, "document_worker");
  assert.equal(presentation.artifactTrust, "validated");
});

test("preserves complete runtime status data", () => {
  const original = {
    ok: true,
    scope: "runtime",
    workspace_root: "C:\\workspace",
    active_profile_name: "WasIstDas",
    expected_public_tool_count: 8,
    registered_public_tool_count: 8,
    available_profiles: [{ name: "large repeated payload" }],
    governance_thresholds: { memory_write_threshold: 2 },
    profile_compile: { persona_layer_enabled: false },
  };
  const result = presentToolResult("plwc_status", original);

  assert.equal(result, original);
  assert.deepEqual(result, original);
});

test("chunks oversized workspace listings without omitting entries", () => {
  const entries = Array.from({ length: 500 }, (_, index) => ({
    kind: "file",
    path: `C:\\workspace\\export\\file-${String(index).padStart(4, "0")}-${"x".repeat(80)}.dat`,
    size: index,
  }));

  const original = {
    ok: true,
    operation: "list",
    path: "C:\\workspace\\export",
    policy_decision: "ALLOW",
    entries,
  };
  const result = presentToolResult("plwc_workspace_operation", original) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const reconstructed = reconstructGeneralResult(result);

  assert.equal(transport.chunked, true);
  assert.equal(transport.protocol, "plwc_result_chunks.v1");
  assert.equal(transport.complete, true);
  assert.equal(transport.no_omitted_content, true);
  assert.equal(transport.received_chunks, transport.total_chunks);
  assert.equal(transport.sha256, transport.reconstructed_sha256);
  assert.equal(
    transport.sha256,
    createHash("sha256").update(reconstructed.json, "utf8").digest("hex"),
  );
  assert.deepEqual(reconstructed.value, original);
});

test("chunks oversized workspace read content without truncating text", () => {
  const source = "Line with useful context.\n".repeat(800);
  const original = {
    ok: true,
    operation: "read",
    path: "C:\\workspace\\large.md",
    policy_decision: "ALLOW",
    content: source,
  };
  const result = presentToolResult("plwc_workspace_operation", original) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const reconstructed = reconstructGeneralResult(result);

  assert.equal(transport.chunked, true);
  assert.equal(transport.protocol, "plwc_result_chunks.v1");
  assert.equal(transport.complete, true);
  assert.equal(transport.no_omitted_content, true);
  assert.deepEqual(reconstructed.value, original);
  assert.equal((reconstructed.value as Record<string, unknown>).content, source);
});

test("keeps Unicode intact across general result chunk boundaries", () => {
  const content = "Größe, Grüße und Profilstatus 🙂\n".repeat(600);
  const original = {
    ok: true,
    operation: "read",
    content,
  };
  const result = presentToolResult("plwc_workspace_operation", original) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const reconstructed = reconstructGeneralResult(result);

  assert.ok(chunks.length > 1);
  for (const chunk of chunks) {
    const text = String(chunk.text);
    assert.equal(chunk.chars, Array.from(text).length);
    assert.equal(chunk.sha256, createHash("sha256").update(text, "utf8").digest("hex"));
  }
  assert.deepEqual(reconstructed.value, original);
  assert.equal((reconstructed.value as Record<string, unknown>).content, content);
});

test("preserves denial classification hints on chunked results", () => {
  const result = presentToolResult("plwc_workspace_operation", {
    ok: false,
    policy_decision: "DENY",
    error: "Protected path denied. ".repeat(800),
  });

  assert.equal(classifyToolResult(false, result), "denied");
});

test("chunks oversized governor results without omitting plan steps", () => {
  const planSteps = Array.from({ length: 80 }, (_, index) => ({
    directive_id: `directive-${String(index).padStart(3, "0")}`,
    evidence: "Long evidence block that must remain available to ChatGPT for review.".repeat(3),
    operation: "retire",
  }));
  const original = {
    ok: true,
    operation: "plan",
    policy_decision: "ALLOW",
    profile: "Sororitas",
    data: {
      plan_type: "memory_retirement",
      steps: planSteps,
    },
    requirement_ids: ["FR-008", "SR-004"],
  };
  const result = presentToolResult("plwc_governor", original) as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const reconstructed = reconstructGeneralResult(result);

  assert.equal(transport.chunked, true);
  assert.equal(transport.protocol, "plwc_result_chunks.v1");
  assert.equal(transport.no_omitted_content, true);
  assert.equal(transport.complete, true);
  assert.deepEqual(reconstructed.value, original);
  assert.equal(
    (((reconstructed.value as Record<string, unknown>).data as Record<string, unknown>).steps as unknown[])
      .length,
    80,
  );
});

test("chunks oversized full profile compiled layers without omitting content", () => {
  const compiledLayer = "Mirco korrigierte explizit: Meta-Kommentare bleiben erhalten.\n".repeat(500);
  const result = presentToolResult("plwc_profile", {
    data: {
      compile_mode: "full",
      compiled_layer: compiledLayer,
    },
    ok: true,
    policy_decision: "ALLOW",
  }) as Record<string, unknown>;
  const data = result.data as Record<string, unknown>;
  const transport = result.result_transport as Record<string, unknown>;
  const layerTransport = data.compiled_layer_transport as Record<string, unknown>;
  const chunks = layerTransport.chunks as Array<Record<string, unknown>>;

  assert.equal(transport.profile_compile_layer_chunked, true);
  assert.equal(transport.profile_compile_layer_protocol, "plwc_profile_compile_layer_chunks.v1");
  assert.equal(transport.compile_mode, "full");
  assert.equal(transport.full_requested, true);
  assert.equal(transport.full_transport_complete, true);
  assert.equal(transport.full_transport_incomplete, false);
  assert.equal(transport.must_continue_until_full_received, false);
  assert.equal(transport.no_omitted_content, true);
  assert.equal(transport.received_chunks, transport.total_chunks);
  assert.equal(transport.sha256, transport.reconstructed_sha256);
  assert.match(String(transport.next_action), /do not request a sandbox artifact/u);
  assert.equal(layerTransport.complete, true);
  assert.equal(layerTransport.received_chunks, layerTransport.total_chunks);
  assert.equal(layerTransport.sha256, layerTransport.reconstructed_sha256);
  assert.ok(chunks.length > 1);
  assert.deepEqual(
    chunks.map((chunk) => chunk.chunk_index),
    Array.from({ length: chunks.length }, (_, index) => index + 1),
  );
  assert.ok(String(data.compiled_layer).length < compiledLayer.length);
  assert.doesNotMatch(String(data.compiled_layer), /content compacted by PLwC Chat Bridge/u);
  assert.equal(reconstructedCompileLayer(result), compiledLayer);
});

test("chunks oversized boot and working profile compiled layers", () => {
  for (const compileMode of ["boot", "working"] as const) {
    const compiledLayer = `${compileMode} layer line with enough context.\n`.repeat(260);
    const result = presentToolResult("plwc_profile", {
      data: {
        compile_mode: compileMode,
        compiled_layer: compiledLayer,
      },
      ok: true,
      policy_decision: "ALLOW",
    }) as Record<string, unknown>;
    const data = result.data as Record<string, unknown>;
    const layerTransport = data.compiled_layer_transport as Record<string, unknown>;
    const transport = result.result_transport as Record<string, unknown>;

    assert.equal(transport.profile_compile_layer_chunked, true);
    assert.equal(transport.compile_mode, compileMode);
    assert.equal(transport.full_requested, false);
    assert.equal(transport.no_omitted_content, true);
    assert.equal(layerTransport.complete, true);
    assert.equal(layerTransport.received_chunks, layerTransport.total_chunks);
    assert.equal(layerTransport.sha256, layerTransport.reconstructed_sha256);
    assert.equal(reconstructedCompileLayer(result), compiledLayer);
  }
});

test("keeps ordinary workspace listings unchanged", () => {
  const result = {
    ok: true,
    operation: "list",
    entries: [{ kind: "file", path: "C:\\workspace\\chat.html", size: 42 }],
  };

  assert.equal(presentToolResult("plwc_workspace_operation", result), result);
});

test("preserves complete sandbox results", () => {
  const original = {
    ok: true,
    mode: "docker",
    policy_decision: "ALLOW",
    facade: "plwc_sandbox_run",
    lang: "python",
    stdout: "FORTSETZEN: Quelle 17/30\n",
    stderr: "",
    exit_code: 0,
    error: null,
    requested_timeout_seconds: 20,
    effective_timeout_seconds: 120,
    timeout_clamped: false,
    docker_args: ["docker", "run", "--rm", "large repeated payload"],
    docker_version: "Docker version repeated for every call",
    requirement_ids: ["FR-008", "SR-003"],
  };
  const result = presentToolResult("plwc_sandbox_run", original);

  assert.equal(result, original);
  assert.deepEqual(result, original);
});

test("validates 50 to 100 KB Unicode results for all eight public tools", () => {
  for (const name of CANONICAL_TOOL_NAMES) {
    const original = largeUnicodeResult(name);
    const originalBytes = Buffer.byteLength(JSON.stringify(original, null, 2), "utf8");
    assert.ok(originalBytes >= 50 * 1_024, `${name} payload is below 50 KB`);
    assert.ok(originalBytes <= 100 * 1_024, `${name} payload is above 100 KB`);

    const prepared = prepareToolResultForChat(name, original);
    assert.equal(prepared.ok, true);
    if (!prepared.ok) continue;
    assert.equal(prepared.validation.chunked, true);
    assert.equal(prepared.validation.protocol, "plwc_result_chunks.v1");
    assert.deepEqual(prepared.validation.reconstructed, original);
    assert.deepEqual(
      validateToolResultTransport(name, prepared.result),
      prepared.validation,
    );
  }
});

test("rejects missing chunks", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  chunks.pop();

  const validation = validateToolResultTransport("plwc_status", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "chunk_count_mismatch");
});

test("rejects duplicate chunk indices", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  assert.ok(chunks[0] && chunks[1]);
  chunks[1].chunk_index = chunks[0].chunk_index;

  const validation = validateToolResultTransport("plwc_status", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "chunk_index_duplicate");
});

test("rejects reordered chunks even when their individual hashes remain valid", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  assert.ok(chunks[0] && chunks[1]);
  [chunks[0], chunks[1]] = [chunks[1], chunks[0]];

  const validation = validateToolResultTransport("plwc_status", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "chunk_order_invalid");
});

test("rejects corrupted chunk text", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const first = chunks[0];
  assert.ok(first);
  first.text = `corrupted${String(first.text)}`;
  first.chars = Array.from(String(first.text)).length;

  const validation = validateToolResultTransport("plwc_status", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "chunk_hash_mismatch");
});

test("rejects an invalid reconstructed JSON payload even with recomputed hashes", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const first = chunks[0];
  assert.ok(first);
  first.text = `!${String(first.text).slice(1)}`;
  first.sha256 = createHash("sha256").update(String(first.text), "utf8").digest("hex");
  const reconstructed = chunks.map((chunk) => String(chunk.text)).join("");
  const completeHash = createHash("sha256").update(reconstructed, "utf8").digest("hex");
  transport.sha256 = completeHash;
  transport.reconstructed_sha256 = completeHash;

  const validation = validateToolResultTransport("plwc_status", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "result_json_invalid");
});

test("rejects corrupted profile compile layer chunks", () => {
  const result = presentToolResult("plwc_profile", {
    data: {
      compile_mode: "full",
      compiled_layer: "Profile context with Unicode 🙂 and continuity.\n".repeat(2_000),
    },
    ok: true,
  }) as Record<string, unknown>;
  const data = result.data as Record<string, unknown>;
  const transport = data.compiled_layer_transport as Record<string, unknown>;
  const chunks = transport.chunks as Array<Record<string, unknown>>;
  const first = chunks[0];
  assert.ok(first);
  first.sha256 = "0".repeat(64);

  const validation = validateToolResultTransport("plwc_profile", result);

  assert.equal(validation.ok, false);
  if (!validation.ok) assert.equal(validation.code, "chunk_hash_mismatch");
  assert.throws(
    () => assertValidToolResultTransport("plwc_profile", result),
    /failed SHA-256 validation/,
  );
});

test("does not rewrap an invalid incoming chunk transport as a seemingly complete result", () => {
  const result = clonedGeneralTransport();
  const transport = result.result_transport as Record<string, unknown>;
  transport.complete = false;

  const prepared = prepareToolResultForChat("plwc_status", result);

  assert.equal(prepared.ok, false);
  if (!prepared.ok) {
    assert.equal(prepared.code, "transport_completeness_invalid");
    const safeFailure = chunkTransportFailureResult(prepared);
    assert.deepEqual(validateToolResultTransport("plwc_status", safeFailure), {
      chunked: false,
      ok: true,
    });
    assert.equal(safeFailure.error_category, "UNAVAILABLE");
    assert.equal(safeFailure.error_detail_category, "chunk_transport_invalid");
    assert.equal(JSON.stringify(safeFailure).includes("payload"), false);
    assert.equal(JSON.stringify(safeFailure).includes("chunks"), false);
  }
});
