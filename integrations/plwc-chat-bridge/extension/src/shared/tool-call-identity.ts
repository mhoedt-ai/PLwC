import { stableStringify, type JsonObject } from "./contracts";

export interface ToolCallIdentity {
  callId: string;
  conversationId: string;
  identityKey: string;
  signatureKey: string;
}

const MAX_IDENTITY_COMPONENT_LENGTH = 512;

export function createToolCallIdentity(
  conversationId: string,
  callId: string,
  name: string,
  argumentsValue: JsonObject,
): ToolCallIdentity {
  validateIdentityComponent(conversationId, "conversation_id");
  validateIdentityComponent(callId, "call_id");
  return {
    callId,
    conversationId,
    identityKey: stableStringify([conversationId, callId]),
    signatureKey: stableStringify({ arguments: argumentsValue, name }),
  };
}

function validateIdentityComponent(value: string, field: string): void {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    value.length > MAX_IDENTITY_COMPONENT_LENGTH ||
    value.trim() !== value ||
    /[\u0000-\u001f\u007f]/u.test(value)
  ) {
    throw new Error(`Invalid PLwC ${field}.`);
  }
}
