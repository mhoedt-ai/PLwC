import type { CanonicalToolName } from "./contracts";

export interface NormalizedToolResult {
  isError: boolean;
  result: unknown;
}

export type ToolResultState = "denied" | "failed" | "succeeded";
export type ToolResultFailureKind =
  | "gateway_failed"
  | "not_found"
  | "policy_denied"
  | "transport_failed"
  | "unavailable"
  | "validation_failed";

export interface ToolResultPresentation {
  artifactOrigin?: string;
  artifactOriginDetail?: string;
  artifactTrust?: "unvalidated" | "validated";
  failureKind: ToolResultFailureKind | null;
  failureLabel: string | null;
  validationDetailStatus?: string;
  validationLabel?: string;
  validationStatus?: string;
}

export interface ToolResultMetadataRow {
  label: string;
  tone: "default" | "validated" | "warning";
  value: string;
}

export type ToolResultTransportErrorCode =
  | "mixed_chunk_protocols"
  | "chunk_protocol_invalid"
  | "chunk_list_missing"
  | "chunk_count_mismatch"
  | "chunk_index_invalid"
  | "chunk_index_duplicate"
  | "chunk_order_invalid"
  | "chunk_total_mismatch"
  | "chunk_character_count_mismatch"
  | "chunk_hash_mismatch"
  | "result_character_count_mismatch"
  | "result_hash_mismatch"
  | "result_json_invalid"
  | "transport_completeness_invalid"
  | "profile_transport_metadata_mismatch";

export interface ToolResultTransportSuccess {
  chunked: boolean;
  ok: true;
  protocol?: string;
  reconstructed?: unknown;
}

export interface ToolResultTransportFailure {
  code: ToolResultTransportErrorCode;
  message: string;
  ok: false;
}

export type ToolResultTransportValidation =
  | ToolResultTransportSuccess
  | ToolResultTransportFailure;

export type PreparedToolResult =
  | {
      ok: true;
      result: unknown;
      validation: ToolResultTransportSuccess;
    }
  | ToolResultTransportFailure;

export class ToolResultTransportError extends Error {
  constructor(
    readonly code: ToolResultTransportErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "ToolResultTransportError";
  }
}

export function chunkTransportFailureResult(
  failure: ToolResultTransportFailure,
): Record<string, unknown> {
  return {
    error: `PLwC result chunk transport validation failed: ${failure.message}`,
    error_category: "UNAVAILABLE",
    error_detail_category: "chunk_transport_invalid",
    ok: false,
    transport_error_code: failure.code,
    validation_status: "validation_failed",
  };
}

const CHAT_RESULT_TRANSPORT_BUDGET = 8_000;
const MAX_INLINE_RESULT_STRING_CHARS = 1_800;
const GENERAL_RESULT_CHUNK_CHARS = 1_500;
const PROFILE_COMPILE_LAYER_CHUNK_CHARS = 1_500;
const PROFILE_COMPILE_LAYER_PROTOCOL = "plwc_profile_compile_layer_chunks.v1";
const GENERAL_RESULT_CHUNK_PROTOCOL = "plwc_result_chunks.v1";
const PROFILE_COMPILE_MODES = new Set(["boot", "working", "full"]);

const SHA256_INITIAL_HASH = [
  0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

const SHA256_K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

function formattedJsonLength(value: unknown): number {
  return (JSON.stringify(value, null, 2) ?? "").length;
}

function add32(...values: number[]): number {
  return values.reduce((sum, value) => (sum + value) >>> 0, 0);
}

function rightRotate(value: number, bits: number): number {
  return ((value >>> bits) | (value << (32 - bits))) >>> 0;
}

function sha256Hex(text: string): string {
  const bytes = new TextEncoder().encode(text);
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  let bitLength = BigInt(bytes.length) * 8n;
  for (let index = paddedLength - 1; index >= paddedLength - 8; index -= 1) {
    padded[index] = Number(bitLength & 0xffn);
    bitLength >>= 8n;
  }

  const hash = [...SHA256_INITIAL_HASH];
  const words = new Array<number>(64).fill(0);
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let index = 0; index < 16; index += 1) {
      const base = offset + index * 4;
      words[index] = (
        ((padded[base] ?? 0) << 24) |
        ((padded[base + 1] ?? 0) << 16) |
        ((padded[base + 2] ?? 0) << 8) |
        (padded[base + 3] ?? 0)
      ) >>> 0;
    }
    for (let index = 16; index < 64; index += 1) {
      const word15 = words[index - 15]!;
      const word2 = words[index - 2]!;
      const sigma0 = (rightRotate(word15, 7) ^ rightRotate(word15, 18) ^ (word15 >>> 3)) >>> 0;
      const sigma1 = (rightRotate(word2, 17) ^ rightRotate(word2, 19) ^ (word2 >>> 10)) >>> 0;
      words[index] = add32(words[index - 16]!, sigma0, words[index - 7]!, sigma1);
    }

    let a = hash[0]!;
    let b = hash[1]!;
    let c = hash[2]!;
    let d = hash[3]!;
    let e = hash[4]!;
    let f = hash[5]!;
    let g = hash[6]!;
    let h = hash[7]!;

    for (let index = 0; index < 64; index += 1) {
      const sigma1 = (rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25)) >>> 0;
      const choice = ((e & f) ^ (~e & g)) >>> 0;
      const temp1 = add32(h, sigma1, choice, SHA256_K[index]!, words[index]!);
      const sigma0 = (rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22)) >>> 0;
      const majority = ((a & b) ^ (a & c) ^ (b & c)) >>> 0;
      const temp2 = add32(sigma0, majority);

      h = g;
      g = f;
      f = e;
      e = add32(d, temp1);
      d = c;
      c = b;
      b = a;
      a = add32(temp1, temp2);
    }

    hash[0] = add32(hash[0]!, a);
    hash[1] = add32(hash[1]!, b);
    hash[2] = add32(hash[2]!, c);
    hash[3] = add32(hash[3]!, d);
    hash[4] = add32(hash[4]!, e);
    hash[5] = add32(hash[5]!, f);
    hash[6] = add32(hash[6]!, g);
    hash[7] = add32(hash[7]!, h);
  }

  return hash.map((value) => value.toString(16).padStart(8, "0")).join("");
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function withResultTransport(
  result: Record<string, unknown>,
  transport: Record<string, unknown>,
): Record<string, unknown> {
  const existing = record(result.result_transport);
  return {
    ...result,
    result_transport: {
      ...(existing ?? {}),
      ...transport,
    },
  };
}

function chunkText(text: string, chunkSize: number): Array<Record<string, unknown>> {
  const characters = Array.from(text);
  const totalChunks = Math.max(1, Math.ceil(characters.length / chunkSize));
  return Array.from({ length: totalChunks }, (_, index) => {
    const chunkTextValue = characters.slice(index * chunkSize, (index + 1) * chunkSize).join("");
    return {
      chunk_index: index + 1,
      total_chunks: totalChunks,
      chars: Array.from(chunkTextValue).length,
      sha256: sha256Hex(chunkTextValue),
      text: chunkTextValue,
    };
  });
}

interface ValidatedChunkCollection {
  ok: true;
  text: string;
  totalChunks: number;
}

function transportFailure(
  code: ToolResultTransportErrorCode,
  message: string,
): ToolResultTransportFailure {
  return { code, message, ok: false };
}

function isPositiveInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function validateChunkCollection(
  transport: Record<string, unknown>,
): ValidatedChunkCollection | ToolResultTransportFailure {
  const chunks = transport.chunks;
  if (!Array.isArray(chunks) || chunks.length === 0) {
    return transportFailure("chunk_list_missing", "Chunk transport does not contain a non-empty chunks array.");
  }
  const totalChunks = transport.total_chunks;
  const receivedChunks = transport.received_chunks;
  if (!isPositiveInteger(totalChunks) || !isPositiveInteger(receivedChunks)) {
    return transportFailure("chunk_count_mismatch", "Chunk transport has invalid total or received chunk counts.");
  }
  if (chunks.length !== totalChunks || receivedChunks !== totalChunks) {
    return transportFailure(
      "chunk_count_mismatch",
      `Chunk transport expected ${totalChunks} chunks, received ${receivedChunks}, and contains ${chunks.length}.`,
    );
  }

  const indices = new Set<number>();
  const texts: string[] = [];
  for (const [position, value] of chunks.entries()) {
    const chunk = record(value);
    if (!chunk || !isPositiveInteger(chunk.chunk_index) || chunk.chunk_index > totalChunks) {
      return transportFailure("chunk_index_invalid", `Chunk at array position ${position + 1} has an invalid index.`);
    }
    if (indices.has(chunk.chunk_index)) {
      return transportFailure("chunk_index_duplicate", `Chunk index ${chunk.chunk_index} occurs more than once.`);
    }
    indices.add(chunk.chunk_index);
    if (chunk.total_chunks !== totalChunks) {
      return transportFailure(
        "chunk_total_mismatch",
        `Chunk ${chunk.chunk_index} reports a different total chunk count.`,
      );
    }
    if (typeof chunk.text !== "string") {
      return transportFailure("chunk_list_missing", `Chunk ${chunk.chunk_index} does not contain text.`);
    }
    const characterCount = Array.from(chunk.text).length;
    if (chunk.chars !== characterCount) {
      return transportFailure(
        "chunk_character_count_mismatch",
        `Chunk ${chunk.chunk_index} character count does not match its text.`,
      );
    }
    if (chunk.sha256 !== sha256Hex(chunk.text)) {
      return transportFailure("chunk_hash_mismatch", `Chunk ${chunk.chunk_index} failed SHA-256 validation.`);
    }
    texts.push(chunk.text);
  }

  for (let position = 0; position < chunks.length; position += 1) {
    const chunk = record(chunks[position]);
    if (chunk?.chunk_index !== position + 1) {
      return transportFailure(
        "chunk_order_invalid",
        `Chunk array order is invalid at position ${position + 1}.`,
      );
    }
  }

  return { ok: true, text: texts.join(""), totalChunks };
}

function validateGeneralResultTransport(
  result: Record<string, unknown>,
  transport: Record<string, unknown> | null,
): ToolResultTransportValidation {
  if (
    !transport ||
    transport.chunked !== true ||
    transport.protocol !== GENERAL_RESULT_CHUNK_PROTOCOL ||
    transport.serialization !== "json" ||
    transport.content_type !== "application/json"
  ) {
    return transportFailure("chunk_protocol_invalid", "General result chunk protocol metadata is invalid.");
  }
  const collection = validateChunkCollection(transport);
  if (!collection.ok) return collection;
  if (
    transport.complete !== true ||
    transport.no_omitted_content !== true
  ) {
    return transportFailure(
      "transport_completeness_invalid",
      "General result chunk transport is not explicitly complete and lossless.",
    );
  }
  if (transport.total_chars !== Array.from(collection.text).length) {
    return transportFailure(
      "result_character_count_mismatch",
      "General result total character count does not match the reconstructed JSON.",
    );
  }
  if (transport.original_json_chars !== collection.text.length) {
    return transportFailure(
      "result_character_count_mismatch",
      "General result JSON character count does not match the reconstructed JSON.",
    );
  }
  const reconstructedHash = sha256Hex(collection.text);
  if (
    transport.sha256 !== reconstructedHash ||
    transport.reconstructed_sha256 !== reconstructedHash
  ) {
    return transportFailure("result_hash_mismatch", "General result failed complete SHA-256 validation.");
  }

  let reconstructed: unknown;
  try {
    reconstructed = JSON.parse(collection.text) as unknown;
  } catch {
    return transportFailure("result_json_invalid", "Reconstructed general result is not valid JSON.");
  }
  const expectedHints = resultClassificationHints(reconstructed);
  for (const [key, value] of Object.entries(expectedHints)) {
    if (Object.hasOwn(result, key) && result[key] !== value) {
      return transportFailure(
        "profile_transport_metadata_mismatch",
        `General result classification hint ${key} does not match the reconstructed result.`,
      );
    }
  }
  return {
    chunked: true,
    ok: true,
    protocol: GENERAL_RESULT_CHUNK_PROTOCOL,
    reconstructed,
  };
}

function validateProfileResultTransport(
  name: CanonicalToolName,
  result: Record<string, unknown>,
  outerTransport: Record<string, unknown> | null,
  data: Record<string, unknown> | null,
  layerTransport: Record<string, unknown> | null,
): ToolResultTransportValidation {
  if (
    name !== "plwc_profile" ||
    !outerTransport ||
    !data ||
    !layerTransport ||
    outerTransport.profile_compile_layer_chunked !== true ||
    outerTransport.profile_compile_layer_protocol !== PROFILE_COMPILE_LAYER_PROTOCOL ||
    layerTransport.protocol !== PROFILE_COMPILE_LAYER_PROTOCOL
  ) {
    return transportFailure(
      "profile_transport_metadata_mismatch",
      "Profile compile chunk protocol metadata is invalid.",
    );
  }
  const collection = validateChunkCollection(layerTransport);
  if (!collection.ok) return collection;
  const compileMode = data.compile_mode;
  if (
    !isProfileCompileMode(compileMode) ||
    outerTransport.compile_mode !== compileMode ||
    layerTransport.compile_mode !== compileMode ||
    layerTransport.field_path !== "$.data.compiled_layer"
  ) {
    return transportFailure(
      "profile_transport_metadata_mismatch",
      "Profile compile mode or field metadata is inconsistent.",
    );
  }
  const totalCharacters = Array.from(collection.text).length;
  if (
    layerTransport.total_chars !== totalCharacters ||
    outerTransport.compiled_layer_chars !== totalCharacters
  ) {
    return transportFailure(
      "result_character_count_mismatch",
      "Profile compile layer character count does not match the reconstructed layer.",
    );
  }
  const reconstructedHash = sha256Hex(collection.text);
  if (
    layerTransport.sha256 !== reconstructedHash ||
    layerTransport.reconstructed_sha256 !== reconstructedHash ||
    outerTransport.sha256 !== reconstructedHash ||
    outerTransport.reconstructed_sha256 !== reconstructedHash
  ) {
    return transportFailure("result_hash_mismatch", "Profile compile layer failed complete SHA-256 validation.");
  }
  if (
    layerTransport.complete !== true ||
    outerTransport.complete !== true ||
    outerTransport.no_omitted_content !== true ||
    outerTransport.total_chunks !== collection.totalChunks ||
    outerTransport.received_chunks !== collection.totalChunks
  ) {
    return transportFailure(
      "transport_completeness_invalid",
      "Profile compile chunk transport is not explicitly complete and lossless.",
    );
  }
  if (
    compileMode === "full" &&
    (
      outerTransport.full_requested !== true ||
      outerTransport.full_transport_complete !== true ||
      outerTransport.full_transport_incomplete !== false ||
      outerTransport.must_continue_until_full_received !== false
    )
  ) {
    return transportFailure(
      "profile_transport_metadata_mismatch",
      "Full profile compile completeness metadata is inconsistent.",
    );
  }
  return {
    chunked: true,
    ok: true,
    protocol: PROFILE_COMPILE_LAYER_PROTOCOL,
    reconstructed: collection.text,
  };
}

export function validateToolResultTransport(
  name: CanonicalToolName,
  result: unknown,
): ToolResultTransportValidation {
  const resultRecord = record(result);
  if (!resultRecord) return { chunked: false, ok: true };
  const outerTransport = record(resultRecord.result_transport);
  const data = record(resultRecord.data);
  const layerTransport = record(data?.compiled_layer_transport);
  const outerProtocol = outerTransport?.protocol;
  const generalIndicated =
    outerTransport?.chunked === true ||
    (typeof outerProtocol === "string" && outerProtocol.startsWith("plwc_result_chunks."));
  const profileIndicated =
    outerTransport?.profile_compile_layer_chunked === true ||
    (typeof outerTransport?.profile_compile_layer_protocol === "string" &&
      outerTransport.profile_compile_layer_protocol.startsWith("plwc_profile_compile_layer_chunks.")) ||
    layerTransport !== null;

  if (generalIndicated && profileIndicated) {
    return transportFailure("mixed_chunk_protocols", "Result claims multiple chunk transport protocols.");
  }
  if (generalIndicated) return validateGeneralResultTransport(resultRecord, outerTransport);
  if (profileIndicated) {
    return validateProfileResultTransport(name, resultRecord, outerTransport, data, layerTransport);
  }
  return { chunked: false, ok: true };
}

export function assertValidToolResultTransport(
  name: CanonicalToolName,
  result: unknown,
): ToolResultTransportSuccess {
  const validation = validateToolResultTransport(name, result);
  if (!validation.ok) throw new ToolResultTransportError(validation.code, validation.message);
  return validation;
}

export function prepareToolResultForChat(
  name: CanonicalToolName,
  result: unknown,
): PreparedToolResult {
  const incomingValidation = validateToolResultTransport(name, result);
  if (!incomingValidation.ok) return incomingValidation;
  if (incomingValidation.chunked) {
    return { ok: true, result, validation: incomingValidation };
  }

  const presented = presentToolResult(name, result);
  const presentedValidation = validateToolResultTransport(name, presented);
  if (!presentedValidation.ok) return presentedValidation;
  return { ok: true, result: presented, validation: presentedValidation };
}

function resultSummary(value: unknown): unknown {
  if (typeof value === "string") {
    return {
      type: "string",
      chars: Array.from(value).length,
    };
  }
  if (value === null || ["boolean", "number"].includes(typeof value)) return value;
  if (Array.isArray(value)) {
    return {
      array_items: value.length,
    };
  }
  const valueRecord = record(value);
  if (!valueRecord) return typeof value;
  return {
    object_keys: Object.keys(valueRecord).sort(),
  };
}

function resultClassificationHints(value: unknown): Record<string, unknown> {
  const valueRecord = record(value);
  if (!valueRecord) return {};
  const hints: Record<string, unknown> = {};
  for (const key of ["ok", "policy_decision", "decision", "operation", "scope"]) {
    const hint = valueRecord[key];
    if (hint === null || ["boolean", "number", "string"].includes(typeof hint)) {
      hints[key] = hint;
    }
  }
  return hints;
}

function isProfileCompileLayerChunked(result: unknown): boolean {
  const resultRecord = record(result);
  const transport = record(resultRecord?.result_transport);
  return transport?.profile_compile_layer_chunked === true;
}

function isProfileCompileMode(value: unknown): value is string {
  return typeof value === "string" && PROFILE_COMPILE_MODES.has(value);
}

function profileLayerChunks(text: string): Array<Record<string, unknown>> {
  return chunkText(text, PROFILE_COMPILE_LAYER_CHUNK_CHARS);
}

function presentProfileCompileResult(name: CanonicalToolName, result: unknown): unknown {
  if (name !== "plwc_profile") return result;
  const resultRecord = record(result);
  const data = record(resultRecord?.data);
  if (!resultRecord || !data) return result;
  const compileMode = data.compile_mode;
  const compiledLayer = data.compiled_layer;
  if (!isProfileCompileMode(compileMode) || typeof compiledLayer !== "string") return result;
  if (compiledLayer.length <= MAX_INLINE_RESULT_STRING_CHARS) return result;

  const chunks = profileLayerChunks(compiledLayer);
  const reconstructed = chunks.map((chunk) => String(chunk.text ?? "")).join("");
  const sha256 = sha256Hex(compiledLayer);
  const reconstructedSha256 = sha256Hex(reconstructed);
  const totalChars = Array.from(compiledLayer).length;
  const complete = reconstructed === compiledLayer && sha256 === reconstructedSha256;
  const layerTransport = {
    protocol: PROFILE_COMPILE_LAYER_PROTOCOL,
    field_path: "$.data.compiled_layer",
    compile_mode: compileMode,
    chunk_size_chars: PROFILE_COMPILE_LAYER_CHUNK_CHARS,
    total_chars: totalChars,
    total_chunks: chunks.length,
    received_chunks: chunks.length,
    sha256,
    reconstructed_sha256: reconstructedSha256,
    complete,
    reconstruction: "Concatenate chunks[].text in chunk_index order.",
    chunks,
  };
  return withResultTransport(
    {
      ...resultRecord,
      data: {
        ...data,
        compiled_layer: `[complete compiled_layer transported via data.compiled_layer_transport.chunks; ${totalChars} chars, ${chunks.length} chunks]`,
        compiled_layer_transport: layerTransport,
      },
    },
    {
      profile_compile_layer_chunked: true,
      profile_compile_layer_protocol: PROFILE_COMPILE_LAYER_PROTOCOL,
      compile_mode: compileMode,
      compiled_layer_chars: totalChars,
      total_chunks: chunks.length,
      received_chunks: chunks.length,
      sha256,
      reconstructed_sha256: reconstructedSha256,
      complete,
      no_omitted_content: complete,
      full_requested: compileMode === "full",
      full_transport_complete: compileMode === "full" ? complete : undefined,
      full_transport_incomplete: compileMode === "full" ? !complete : undefined,
      must_continue_until_full_received: compileMode === "full" ? !complete : undefined,
      chunk_completion_rule:
        "Treat the profile compile layer as complete only when received_chunks == total_chunks and sha256 == reconstructed_sha256.",
      next_action:
        "Use data.compiled_layer_transport.chunks in chunk_index order; do not request a sandbox artifact for this profile compile layer.",
    },
  );
}

function chunkResultForChatTransport(result: unknown): unknown {
  if (isProfileCompileLayerChunked(result)) return result;
  if (formattedJsonLength(result) <= CHAT_RESULT_TRANSPORT_BUDGET) return result;

  const originalJson = JSON.stringify(result, null, 2) ?? "null";
  const chunks = chunkText(originalJson, GENERAL_RESULT_CHUNK_CHARS);
  const reconstructed = chunks.map((chunk) => String(chunk.text ?? "")).join("");
  const sha256 = sha256Hex(originalJson);
  const reconstructedSha256 = sha256Hex(reconstructed);
  const complete = reconstructed === originalJson && sha256 === reconstructedSha256;
  return {
    ...resultClassificationHints(result),
    result_summary: resultSummary(result),
    result_transport: {
      chunked: true,
      protocol: GENERAL_RESULT_CHUNK_PROTOCOL,
      reason: "chat_message_size_limit",
      serialization: "json",
      content_type: "application/json",
      original_json_chars: originalJson.length,
      total_chars: Array.from(originalJson).length,
      chunk_size_chars: GENERAL_RESULT_CHUNK_CHARS,
      total_chunks: chunks.length,
      received_chunks: chunks.length,
      sha256,
      reconstructed_sha256: reconstructedSha256,
      complete,
      no_omitted_content: complete,
      reconstruction:
        "Concatenate chunks[].text in chunk_index order, verify the SHA-256 metadata, then parse the reconstructed JSON.",
      chunks,
      next_action:
        "Use the complete reconstructed JSON result. Do not request a narrower call merely because this result was chunked.",
    },
  };
}

export function normalizeToolResult(value: unknown): NormalizedToolResult {
  const envelope = record(value);
  if (!envelope) return { isError: false, result: value };

  const isError = envelope.isError === true;
  if (envelope.structuredContent !== undefined) {
    return { isError, result: envelope.structuredContent };
  }

  if (Array.isArray(envelope.content) && envelope.content.length === 1) {
    const item = record(envelope.content[0]);
    if (item?.type === "text" && typeof item.text === "string") {
      try {
        return { isError, result: JSON.parse(item.text) as unknown };
      } catch {
        return { isError, result: item.text };
      }
    }
  }

  return { isError, result: value };
}

const NON_POLICY_PUBLIC_ERROR_CATEGORIES = new Set([
  "CONFLICT",
  "INVALID_REQUEST",
  "NOT_FOUND",
  "UNAVAILABLE",
]);

export function classifyToolResult(isError: boolean, result: unknown): ToolResultState {
  const resultRecord = record(result);
  const publicErrorCategory = String(resultRecord?.error_category ?? "").toUpperCase();
  const explicitNonPolicyFailure = NON_POLICY_PUBLIC_ERROR_CATEGORIES.has(publicErrorCategory);
  const denied =
    publicErrorCategory === "POLICY_DENY" ||
    (
      !explicitNonPolicyFailure &&
      (
        String(resultRecord?.policy_decision ?? "").toUpperCase() === "DENY" ||
        String(resultRecord?.decision ?? "").toLowerCase() === "denied"
      )
    );
  if (denied) return "denied";
  if (isError || resultRecord?.ok === false) return "failed";
  return "succeeded";
}

const TOOL_RESULT_FAILURE_LABELS: Record<ToolResultFailureKind, string> = {
  gateway_failed: "Gateway failed",
  not_found: "Not found",
  policy_denied: "Policy denied",
  transport_failed: "Transport failed",
  unavailable: "Unavailable",
  validation_failed: "Validation failed",
};

export function describeToolResultPresentation(
  name: CanonicalToolName,
  isError: boolean,
  result: unknown,
): ToolResultPresentation {
  const resultRecord = presentationResultRecord(name, result);
  const errorCategory = stringField(resultRecord, "error_category")?.toUpperCase();
  const errorDetailCategory = stringField(resultRecord, "error_detail_category")?.toLowerCase();
  const validationStatus = stringField(resultRecord, "validation_status")?.toLowerCase();
  const policyDenied =
    String(resultRecord?.policy_decision ?? "").toUpperCase() === "DENY" ||
    String(resultRecord?.decision ?? "").toLowerCase() === "denied";

  let failureKind: ToolResultFailureKind | null = null;
  if (
    errorDetailCategory === "chunk_transport_invalid" ||
    typeof resultRecord?.transport_error_code === "string"
  ) {
    failureKind = "transport_failed";
  } else if (errorCategory === "POLICY_DENY") {
    failureKind = "policy_denied";
  } else if (errorCategory === "INVALID_REQUEST") {
    failureKind = "validation_failed";
  } else if (errorCategory === "NOT_FOUND") {
    failureKind = "not_found";
  } else if (validationStatus === "validation_failed") {
    failureKind = "validation_failed";
  } else if (errorCategory === "UNAVAILABLE") {
    failureKind = "unavailable";
  } else if (policyDenied) {
    failureKind = "policy_denied";
  } else if (isError || resultRecord?.ok === false) {
    failureKind = "gateway_failed";
  }

  const artifactOrigin = stringField(resultRecord, "artifact_origin");
  const artifactOriginDetail = stringField(resultRecord, "artifact_origin_detail");
  const validationDetailStatus = stringField(resultRecord, "validation_detail_status");
  const artifactTrust = validationStatus === "validated"
    ? "validated"
    : validationStatus === "unvalidated" || validationStatus === "validation_failed"
      ? "unvalidated"
      : undefined;

  return {
    ...(artifactOrigin === undefined ? {} : { artifactOrigin }),
    ...(artifactOriginDetail === undefined ? {} : { artifactOriginDetail }),
    ...(artifactTrust === undefined ? {} : { artifactTrust }),
    failureKind,
    failureLabel: failureKind === null ? null : TOOL_RESULT_FAILURE_LABELS[failureKind],
    ...(validationDetailStatus === undefined ? {} : { validationDetailStatus }),
    ...(validationStatus === undefined
      ? {}
      : {
          validationLabel: validationStatusLabel(validationStatus),
          validationStatus,
        }),
  };
}

export function toolResultMetadataRows(
  name: CanonicalToolName,
  isError: boolean,
  result: unknown,
): ToolResultMetadataRow[] {
  const presentation = describeToolResultPresentation(name, isError, result);
  const rows: ToolResultMetadataRow[] = [];
  if (presentation.artifactOrigin) {
    rows.push({ label: "Artifact origin", tone: "default", value: presentation.artifactOrigin });
  }
  if (presentation.artifactOriginDetail) {
    rows.push({ label: "Origin detail", tone: "default", value: presentation.artifactOriginDetail });
  }
  if (presentation.validationLabel) {
    rows.push({
      label: "Validation",
      tone: presentation.artifactTrust === "unvalidated"
        ? "warning"
        : presentation.artifactTrust === "validated"
          ? "validated"
          : "default",
      value: presentation.validationLabel,
    });
  }
  if (presentation.validationDetailStatus) {
    rows.push({
      label: "Validation detail",
      tone: "default",
      value: presentation.validationDetailStatus,
    });
  }
  if (presentation.artifactTrust) {
    rows.push({
      label: "Artifact trust",
      tone: presentation.artifactTrust === "unvalidated" ? "warning" : "validated",
      value: presentation.artifactTrust === "unvalidated"
        ? "UNVALIDATED - do not treat as safe"
        : "VALIDATED",
    });
  }
  return rows;
}

function presentationResultRecord(
  name: CanonicalToolName,
  result: unknown,
): Record<string, unknown> | null {
  const validation = validateToolResultTransport(name, result);
  if (
    validation.ok &&
    validation.protocol === GENERAL_RESULT_CHUNK_PROTOCOL
  ) {
    return record(validation.reconstructed);
  }
  return record(result);
}

function stringField(
  value: Record<string, unknown> | null,
  field: string,
): string | undefined {
  const candidate = value?.[field];
  return typeof candidate === "string" && candidate.trim() !== ""
    ? candidate.trim()
    : undefined;
}

function validationStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    unvalidated: "Unvalidated",
    validated: "Validated",
    validation_failed: "Validation failed",
  };
  return labels[status] ?? status.replaceAll("_", " ");
}

export function presentToolResult(name: CanonicalToolName, result: unknown): unknown {
  const presented = presentProfileCompileResult(name, result);
  return chunkResultForChatTransport(presented);
}
