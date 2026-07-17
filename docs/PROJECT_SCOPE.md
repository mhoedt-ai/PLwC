# Project Scope

## Goal

Build PLwC Gateway as one governed local MCP gateway for Claude Desktop and other MCP clients.

PLwC must combine profile governance, protected memory, safe local tools, Docker-based execution and audit logging behind one visible MCP server.

## Not the Goal

PLwC is not:

- a fully autonomous 24/7 agent platform
- a direct replacement for Claude Code or Claude Cowork
- a generic unrestricted Desktop Commander clone
- a system that gives the model unconstrained host access
- a rewrite of PLfC / PBA from scratch
- a rewrite of Hardened Commander from scratch

## Product Principle

The agent may help the user work.

It may not silently change the rules that keep it safe.

## Tracked Client Integrations

- `V1-LOCAL-CHATGPT-ADAPTER-001`: **PLwC Chat Bridge**, a PLwC-specific local
  ChatGPT browser client adapter based on an MCP SuperAssistant proof of
  concept. Status: design and local prototype; proposed for the v0.2.0-rc19
  development track and not part of the current Open Beta support matrix. See
  [`LOCAL_CHATGPT_CLIENT_ADAPTER.md`](LOCAL_CHATGPT_CLIENT_ADAPTER.md).
- `V1-REMOTE-MCP-FACADE-001`: future authenticated remote MCP facade for hosted
  ChatGPT custom apps. This is a separate deployment class from the local
  browser adapter.
