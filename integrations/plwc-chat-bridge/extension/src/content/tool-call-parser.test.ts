import assert from 'node:assert/strict';
import test from 'node:test';

import {
  PLWC_TOOL_NAMES,
  parseVisiblePlwcToolCalls,
  type JsonValue,
  type PlwcToolName,
  type ToolCallTextCandidate,
} from './tool-call-parser.js';

function jsonlCall(
  name: PlwcToolName | string,
  callId: number | string,
  parameters: ReadonlyArray<readonly [string, JsonValue]> = [],
): string {
  return [
    JSON.stringify({ type: 'function_call_start', name, call_id: callId }),
    JSON.stringify({ type: 'description', text: `Run ${name}` }),
    ...parameters.map(([key, value]) => JSON.stringify({ type: 'parameter', key, value })),
    JSON.stringify({ type: 'function_call_end', call_id: callId }),
  ].join('\n');
}

function visible(text: string, overrides: Partial<ToolCallTextCandidate> = {}): ToolCallTextCandidate {
  return { text, visible: true, sourceKind: 'rendered', ...overrides };
}

test('accepts exactly the eight canonical PLwC tool names', () => {
  const calls = parseVisiblePlwcToolCalls(
    PLWC_TOOL_NAMES.map((name, index) => visible(jsonlCall(name, index + 1))),
  );

  assert.deepEqual(calls.map(call => call.name), PLWC_TOOL_NAMES);
  assert.equal(calls.length, 8);
});

test('parses fenced JSONL and preserves nested JSON argument values', () => {
  const text = [
    '```jsonl',
    jsonlCall('plwc_governor', 'plan-17', [
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

test('rejects unknown, legacy, and near-match tool names', () => {
  for (const name of ['plwc_governor_apply', 'plwc_status ', 'PLWC_STATUS', 'unknown_tool']) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(jsonlCall(name, 1))]), []);
  }
});

test('fails closed for malformed JSON without returning a preceding partial call', () => {
  const malformed = [
    jsonlCall('plwc_status', 1, [['scope', 'runtime']]),
    '{"type":"function_call_start","name":"plwc_profile","call_id":2',
  ].join('\n');

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(malformed)]), []);
});

test('rejects incomplete calls, mismatched IDs, unknown events, and extra fields', () => {
  const incomplete = jsonlCall('plwc_status', 1).split('\n').slice(0, -1).join('\n');
  const mismatchedId = jsonlCall('plwc_status', 1).replace(
    '{"type":"function_call_end","call_id":1}',
    '{"type":"function_call_end","call_id":2}',
  );
  const unknownEvent = jsonlCall('plwc_status', 1).replace(
    '{"type":"description","text":"Run plwc_status"}',
    '{"type":"execute","text":"Run plwc_status"}',
  );
  const extraField = jsonlCall('plwc_status', 1).replace(
    '{"type":"function_call_end","call_id":1}',
    '{"type":"function_call_end","call_id":1,"execute":true}',
  );

  for (const text of [incomplete, mismatchedId, unknownEvent, extraField]) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(text)]), []);
  }
});

test('rejects duplicate, empty, and prototype-sensitive argument keys', () => {
  const duplicate = jsonlCall('plwc_workspace_operation', 1, [
    ['path', 'first.txt'],
    ['path', 'second.txt'],
  ]);
  const empty = jsonlCall('plwc_status', 2, [['', 'runtime']]);
  const prototypeKey = jsonlCall('plwc_status', 3, [['__proto__', 'runtime']]);
  const nestedPrototypeKey = jsonlCall('plwc_governor', 4, [
    ['onboarding_answers', JSON.parse('{"safe":{"constructor":"blocked"}}') as JsonValue],
  ]);

  for (const text of [duplicate, empty, prototypeKey, nestedPrototypeKey]) {
    assert.deepEqual(parseVisiblePlwcToolCalls([visible(text)]), []);
  }
});

test('deduplicates by a stable key and prefers rendered text over editor copies', () => {
  const editorCopy = visible(
    jsonlCall('plwc_workspace_operation', 'call-9', [
      ['path', 'notes.txt'],
      ['operation', 'read'],
    ]),
    { sourceId: 'editor-copy', sourceKind: 'editor-copy' },
  );
  const rendered = visible(
    jsonlCall('plwc_workspace_operation', 'call-9', [
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
});

test('ignores hidden editor copies even when they appear before visible content', () => {
  const hiddenCopy = visible(jsonlCall('plwc_status', 1, [['scope', 'config']]), {
    visible: false,
    sourceId: 'hidden-editor-copy',
    sourceKind: 'editor-copy',
  });
  const rendered = visible(jsonlCall('plwc_status', 1, [['scope', 'runtime']]), {
    sourceId: 'rendered-code',
  });

  const [call] = parseVisiblePlwcToolCalls([hiddenCopy, rendered]);

  assert.ok(call);
  assert.equal(call.sourceId, 'rendered-code');
  assert.deepEqual(call.arguments, { scope: 'runtime' });
});

test('does not interpret arbitrary prose or direct JSON objects as JSONL events', () => {
  const prose = `Please run this: ${jsonlCall('plwc_status', 1)}`;
  const directObject = JSON.stringify({ name: 'plwc_status', call_id: 1, parameters: {} });

  assert.deepEqual(parseVisiblePlwcToolCalls([visible(prose)]), []);
  assert.deepEqual(parseVisiblePlwcToolCalls([visible(directObject)]), []);
});
