import assert from 'node:assert/strict';
import test from 'node:test';

import {
  PLWC_TOOL_NAMES,
  parseVisiblePlwcToolCalls,
  type JsonValue,
  type PlwcToolName,
  type ToolCallTextCandidate,
} from './tool-call-parser.js';

function wrappedCall(
  name: PlwcToolName | string,
  callId: number | string,
  parameters: ReadonlyArray<readonly [string, JsonValue]> = [],
): string {
  return JSON.stringify({
    plwc_tool_call: {
      arguments: Object.fromEntries(parameters),
      call_id: callId,
      name,
    },
  });
}

function wrappedCallWithEnvelope(
  envelope: Record<string, unknown>,
): string {
  return JSON.stringify({ plwc_tool_call: envelope });
}

function visible(text: string, overrides: Partial<ToolCallTextCandidate> = {}): ToolCallTextCandidate {
  return {
    conversationId: '/c/parser-test',
    text,
    visible: true,
    sourceKind: 'rendered',
    ...overrides,
  };
}

test('accepts exactly the eight canonical PLwC tool names', () => {
  const calls = parseVisiblePlwcToolCalls(
    PLWC_TOOL_NAMES.map((name, index) => visible(wrappedCall(name, index + 1))),
  );

  assert.deepEqual(calls.map(call => call.name), PLWC_TOOL_NAMES);
  assert.equal(calls.length, 8);
});

test('parses fenced wrapper JSON and preserves nested JSON argument values', () => {
  const text = [
    '```json',
    wrappedCall('plwc_governor', 'plan-17', [
      ['operation', 'plan'],
      ['confirmed', false],
      ['onboarding_answers', { goals: ['clarity', 'continuity'], score: 0.75 }],
      ['optional', null],
    ]),
    '```',
  ].join('\n');

  const [call] = parseVisiblePlwcToolCalls([visible(text)]);

  assert.ok(call);
  assert.equal(call.name, 'plwc_governor');
  assert.equal(call.callId, 'plan-17');
  assert.deepEqual(call.arguments, {
    operation: 'plan',
    confirmed: false,
    onboarding_answers: { goals: ['clarity', 'continuity'], score: 0.75 },
    optional: null,
  });
});

test('parses the current ChatGPT language label joined directly to wrapper JSON', () => {
  const payload = wrappedCall('plwc_status', 'live-dom-1', [['scope', 'runtime']]);

  for (const text of [`JSON${payload}`, `json ${payload}`]) {
    const [call] = parseVisiblePlwcToolCalls([visible(text)]);
    assert.equal(call?.callId, 'live-dom-1');
    assert.equal(call?.name, 'plwc_status');
    assert.deepEqual(call?.arguments, { scope: 'runtime' });
  }

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(`javascript${payload}`)]), []);
});

test('normalizes ChatGPT non-breaking indentation without changing string content', () => {
  const payload = [
    '{',
    '\u00a0\u00a0"plwc_tool_call": {',
    '\u00a0\u00a0\u00a0\u00a0"name": "plwc_status",',
    '\u00a0\u00a0\u00a0\u00a0"call_id": "live-nbsp-1",',
    '\u00a0\u00a0\u00a0\u00a0"arguments": {"scope": "run\u00a0time"}',
    '\u00a0\u00a0}',
    '}',
  ].join('\n');

  const [call] = parseVisiblePlwcToolCalls([visible(`json\n${payload}`)]);
  assert.equal(call?.callId, 'live-nbsp-1');
  assert.deepEqual(call?.arguments, { scope: 'run\u00a0time' });
});

test('ignores event-shaped tool JSON', () => {
  const text = JSON.stringify({
    call_id: 'workspace-list-17',
    name: 'plwc_workspace_operation',
    type: 'tool_event_start',
  });

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(text)]), []);
});

test('rejects unknown and near-match tool names', () => {
  for (const name of ['plwc_governor_apply', 'plwc_status ', 'PLWC_STATUS', 'unknown_tool']) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(wrappedCall(name, 1))]), []);
  }
});

test('fails closed for malformed JSON without returning a preceding partial call', () => {
  const malformed = [
    wrappedCall('plwc_status', 1, [['scope', 'runtime']]),
    '{"plwc_tool_call":{"name":"plwc_profile","call_id":2',
  ].join('\n');

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(malformed)]), []);
});

test('rejects incomplete wrappers, direct objects, and extra fields', () => {
  const incomplete = wrappedCallWithEnvelope({ call_id: 1, name: 'plwc_status' });
  const directObject = JSON.stringify({ arguments: { scope: 'runtime' }, call_id: 1, name: 'plwc_status' });
  const extraTopLevel = JSON.stringify({
    extra: true,
    plwc_tool_call: { arguments: { scope: 'runtime' }, call_id: 1, name: 'plwc_status' },
  });
  const extraEnvelope = wrappedCallWithEnvelope({
    arguments: { scope: 'runtime' },
    call_id: 1,
    execute: true,
    name: 'plwc_status',
  });

  for (const text of [incomplete, directObject, extraTopLevel, extraEnvelope]) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(text)]), []);
  }
});

test('rejects empty and prototype-sensitive argument keys', () => {
  const empty = wrappedCall('plwc_status', 2, [['', 'runtime']]);
  const prototypeKey = wrappedCall('plwc_status', 3, [['__proto__', 'runtime']]);
  const nestedPrototypeKey = wrappedCall('plwc_governor', 4, [
    ['onboarding_answers', JSON.parse('{"safe":{"constructor":"blocked"}}') as JsonValue],
  ]);

  for (const text of [empty, prototypeKey, nestedPrototypeKey]) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(text)]), []);
  }
});

test('deduplicates by a stable key and prefers rendered text over editor copies', () => {
  const editorCopy = visible(
    wrappedCall('plwc_workspace_operation', 'call-9', [
      ['path', 'notes.txt'],
      ['operation', 'read'],
    ]),
    { sourceId: 'editor-copy', sourceKind: 'editor-copy' },
  );
  const rendered = visible(
    wrappedCall('plwc_workspace_operation', 'call-9', [
      ['operation', 'read'],
      ['path', 'notes.txt'],
    ]),
    { sourceId: 'rendered-code', sourceKind: 'rendered' },
  );

  const calls = parseVisiblePlwcToolCalls([editorCopy, rendered]);

  assert.equal(calls.length, 1);
  const selectedCall = calls[0];
  assert.ok(selectedCall);
  assert.equal(selectedCall.sourceId, 'rendered-code');
  assert.deepEqual(selectedCall.arguments, { operation: 'read', path: 'notes.txt' });

  const editorCall = parseVisiblePlwcToolCalls([editorCopy])[0];
  const renderedCall = parseVisiblePlwcToolCalls([rendered])[0];
  assert.ok(editorCall);
  assert.ok(renderedCall);
  const editorKey = editorCall.callKey;
  const renderedKey = renderedCall.callKey;
  assert.equal(editorKey, renderedKey);
  assert.equal(editorCall.callSignatureKey, renderedCall.callSignatureKey);
});

test('uses conversation_id and call_id as identity while keeping payload changes detectable', () => {
  const original = visible(
    wrappedCall('plwc_status', 'shared-call', [['scope', 'runtime']]),
    { conversationId: '/c/first' },
  );
  const changed = visible(
    wrappedCall('plwc_status', 'shared-call', [['scope', 'config']]),
    { conversationId: '/c/first' },
  );
  const otherConversation = visible(
    wrappedCall('plwc_status', 'shared-call', [['scope', 'runtime']]),
    { conversationId: '/c/second' },
  );

  const [firstCall, changedCall, otherConversationCall] = parseVisiblePlwcToolCalls([
    original,
    changed,
    otherConversation,
  ]);

  assert.ok(firstCall);
  assert.ok(changedCall);
  assert.ok(otherConversationCall);
  assert.equal(firstCall.callKey, changedCall.callKey);
  assert.notEqual(firstCall.callSignatureKey, changedCall.callSignatureKey);
  assert.notEqual(firstCall.callKey, otherConversationCall.callKey);
});

test('ignores hidden editor copies even when they appear before visible content', () => {
  const hiddenCopy = visible(wrappedCall('plwc_status', 1, [['scope', 'config']]), {
    visible: false,
    sourceId: 'hidden-editor-copy',
    sourceKind: 'editor-copy',
  });
  const rendered = visible(wrappedCall('plwc_status', 1, [['scope', 'runtime']]), {
    sourceId: 'rendered-code',
  });

  const [call] = parseVisiblePlwcToolCalls([hiddenCopy, rendered]);

  assert.ok(call);
  assert.equal(call.sourceId, 'rendered-code');
  assert.deepEqual(call.arguments, { scope: 'runtime' });
});

test('does not interpret arbitrary prose or direct JSON objects as tool calls', () => {
  const prose = `Please run this: ${wrappedCall('plwc_status', 1)}`;
  const directObject = JSON.stringify({ name: 'plwc_status', call_id: 1, arguments: {} });

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(prose)]), []);
  assert.deepEqual(parseVisiblePlwcToolCalls([visible(directObject)]), []);
});
