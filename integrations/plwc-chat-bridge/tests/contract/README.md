# Contract Tests

Planned contract coverage:

- numeric JSON-RPC request IDs route correctly through the bridge;
- `tools/list` returns exactly the eight public PLwC facade tools;
- tool schemas match the current gateway build;
- policy denials are represented as governed PLwC results;
- mutating calls are not retried after ambiguous timeouts.
