# PLwC Chat Bridge rc19.dev9 Workspace Evidence And Sequencing

- Date: 2026-07-18
- Branch: `codex/plwc-chat-bridge-rc19`
- Trigger: ChatGPT reported an inventory filename as a verified path, then a
  denied move result was displayed as `SUCCEEDED`
- Environment: Windows PowerShell, signed-in Chrome, Node.js, PLwC loopback
  bridge

## Live Diagnosis

The actual discovery call used
`plwc_workspace_operation(operation="search", path="Wandorra",
query="Spielleiter")`. This operation searches text contents. It returned
mentions from `gen_inventar.js` and `Wandorra_Inventar.md`; it did not return a
filesystem entry for the DOCX. ChatGPT nevertheless reported the inventory
name as found at the Wandorra root and reused that unverified path for a move.

Read-only host verification found the real file at
`Wandorra\Hintergrund\Wandorra Spielleiterhandbuch Kladde.docx`. The inventory
candidate omitted `Hintergrund`. The marked move result contained `ok=false`,
`policy_decision="DENY"` and `decision="denied"`, while the bridge card showed
`SUCCEEDED` because it had trusted only the outer MCP `isError` flag.

After the dev9 runtime restart, a real read-only `file_info` call for that exact
path returned `ok=true`, kind `file` and size `47,958,266` bytes. No corrective
move was executed during diagnosis.

The same GPT response emitted `create_dir` and `move` calls together. Their
automatic executions could race, so one result occupied the composer while
the other attempted automatic return.

## rc19.dev9 Corrections

- The primer states that workspace `search` scans text contents and that
  inventory, index, profile, prior-chat and search-line paths are unverified
  candidates.
- Filename discovery must use a real `list` operation with sufficient depth,
  followed by `file_info` returning `ok=true` for the exact selected path.
- The primer permits only one tool call at a time and requires the matching
  result before a dependent call.
- Calls found in the same GPT response are also serialized defensively by the
  extension. A later call stays scheduled when the earlier call fails or its
  result cannot be returned to ChatGPT.
- Structured `ok=false`, `policy_decision="DENY"` and `decision="denied"`
  results are classified as failed or denied even when MCP transport itself
  completed normally.
- The gateway tool description and workspace describe payload now explain the
  content-search versus filename-discovery distinction.

## Automated Results

| Check | Result | Evidence |
| --- | --- | --- |
| Extension focused tests | PASS | Typecheck completed and 44 of 44 tests passed before the release build. |
| Public gateway contract tests | PASS | 8 of 8 focused Python integration tests passed. |
| Full bridge workspace check | PASS | Bridge 12 of 12 and extension 44 of 44 passed; production and browser-fixture builds completed. |
| Loopback runtime | PASS | Restarted runtime returned 8 of 8 tools and the corrected live workspace-search description. |

## Manual Signed-in Acceptance

Pending after loading `0.2.0-rc19.dev9` and inserting its newly generated
primer. Ask ChatGPT to locate a filename that appears in an inventory at a
stale path. It must treat that mention as a candidate, list real entries,
verify the exact path with `file_info`, and only then offer a mutation.
