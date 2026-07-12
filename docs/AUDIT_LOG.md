# Audit Log

PLwC must record policy decisions and security-relevant events.

## Events

- allowed tool call
- denied tool call
- rewritten tool call
- protected path access attempt
- runtime mode change
- sandbox unavailable
- governance update accepted
- governance update rejected

## Event Schema

Gateway audit events are metadata-only. They may contain:

- `timestamp`
- `event`
- `tool_name`
- `action_type`
- `target_category`
- `high_risk`
- `policy_decision`
- `requirement_ids`
- `result_status`
- `error_category`
- bounded result metrics such as character counts or match counts

Gateway audit events must not contain raw tool arguments or raw tool results.
For preflight events, the gateway records only argument key names and target
category metadata. For completion events, the gateway records only result
status, policy decision, requirement IDs, error category and bounded metrics.

## Rule

Do not log sensitive file contents by default.

High-risk writes and sandbox execution must fail closed if the audit preflight
record cannot be safely redacted or written. Audit records must not contain raw
file contents, search hit lines, reflection evidence, shell commands, Python
code, stdout, stderr, profile-derived content, secrets, tokens, API keys,
passwords, bearer strings, cookies, private keys, authorization headers or full
host paths.

The audit logger applies recursive redaction as defense in depth for raw fields
such as `content`, `code`, `line`, `summary`, `evidence`, `command`, `stdout`,
`stderr`, `snapshot`, `compiled_layer`, `docker_args`, path-like fields, secret
assignments and private key blocks.
