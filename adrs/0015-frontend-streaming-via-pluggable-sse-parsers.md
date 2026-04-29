# ADR-0015: Pluggable SSE parsers in the frontend AgentCore client

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Frontend, Agent developers
- **Tags:** frontend, streaming, sse

## Context

AgentCore Runtime streams agent responses as Server-Sent Events, but
the *shape* of those events depends on the framework running inside
the agent:

- **Strands** emits its own event schema (tool use, message deltas,
  lifecycle).
- **LangGraph** emits LangChain-style message chunks.
- **Claude Agent SDK** emits Anthropic-style events.
- **AG-UI** provides a unified cross-framework schema
  (`TEXT_MESSAGE_CONTENT`, `TOOL_CALL_*`, `RUN_FINISHED`).

The frontend needs to render all of these without forking the UI per
framework, and adding a new backend pattern should not require
restructuring `ChatInterface`.

## Decision

The React client library
(`frontend/src/lib/agentcore-client/`) owns a pluggable parser
registry:

- `client.ts::getParser` picks a parser based on the pattern-name
  prefix:
  - `agui-*` → `parsers/agui.ts`
  - `langgraph-*` → `parsers/langgraph.ts`
  - `claude-*` → `parsers/claude-agent-sdk.ts`
  - `strands-*` (default) → `parsers/strands.ts`
- Each parser normalizes framework-specific events into a shared
  `StreamEvent` union: `text`, `tool_use_start`,
  `tool_use_delta`, `tool_result`, `message`, `result`, `lifecycle`.
- `ChatInterface.tsx` consumes `StreamEvent`s only, so UI code is
  framework-agnostic.

The folder-prefix contract from ADR-0008 is the coupling point: if a
pattern changes framework, rename the folder to match the parser (or
add a new parser).

## Alternatives Considered

- **Branching UI code on pattern.** Rejected: leaks framework
  semantics into the view layer.
- **Make every backend emit AG-UI.** Rejected *for now*: we want AG-UI
  and native Strands/LangGraph/Claude patterns side by side so we can
  evaluate them. Long-term standardization on AG-UI is a plausible
  future ADR.
- **Server-side normalization (runtime maps events → canonical
  schema).** Rejected: adds runtime middleware, and framework
  features evolve faster than we want to maintain a translation
  layer server-side.

## Consequences

### Positive
- New frameworks are a new parser file plus a prefix — no UI change.
- UI stays decoupled from framework-specific event semantics.
- Makes comparison (A/B) between frameworks cheap.

### Negative / Trade-offs
- The `StreamEvent` union is a *lowest-common-denominator*; genuinely
  unique framework events risk being lost.
- Silent fallback to `parseStrandsChunk` for unknown prefixes can
  mask misconfiguration; consider logging a warning.
- Parser code must keep up with framework version changes.

### Neutral
- `docs/STREAMING.md` is the authoritative guide for parser authors.

## Implementation Notes

- `frontend/src/lib/agentcore-client/client.ts::getParser` — prefix
  dispatch.
- `frontend/src/lib/agentcore-client/parsers/` — per-framework
  parsers.
- `frontend/src/lib/agentcore-client/types.ts` — canonical
  `StreamEvent` union.
- `docs/STREAMING.md`, `docs/AGUI_INTEGRATION.md` — background.

## References

- Internal: `docs/STREAMING.md`, `docs/AGUI_INTEGRATION.md`
- External: [AG-UI protocol](https://docs.ag-ui.com/concepts/overview),
  [Server-Sent Events (WHATWG)](https://html.spec.whatwg.org/multipage/server-sent-events.html)
