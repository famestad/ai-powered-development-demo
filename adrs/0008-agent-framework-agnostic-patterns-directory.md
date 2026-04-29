# ADR-0008: Framework-agnostic agent patterns directory

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Agent developers, Platform
- **Tags:** agent, runtime, extensibility

## Context

The agent ecosystem is moving fast. Strands, LangGraph, and Anthropic's
Claude Agent SDK each have their own strengths; AG-UI is emerging as a
cross-framework streaming protocol. We want to:

- Let the Maplewood team try different orchestration frameworks without
  re-deploying the whole infra.
- Keep shared concerns (tool clients, memory, auth extraction,
  guardrails) out of any one framework.
- Allow the frontend to render streaming output regardless of which
  backend framework produced it.

## Decision

Structure agent code as pluggable **patterns** under `patterns/`. A
pattern is a self-contained folder with its own `requirements.txt` and
`Dockerfile`, plus an entrypoint module invoked by
`BedrockAgentCoreApp`. The active pattern is selected in
`infra-cdk/config.yaml`:

```yaml
backend:
  pattern: strands-single-agent
```

Current patterns:

| Pattern | Framework | Notes |
|---|---|---|
| `strands-single-agent` | Strands | Default. Uses Gateway MCP client, Memory session manager, Code Interpreter. |
| `langgraph-single-agent` | LangGraph | Same capability surface, different framework. |
| `agui-strands-agent` | Strands + AG-UI | Emits AG-UI events over SSE. |
| `agui-langgraph-agent` | LangGraph + AG-UI | Same, for LangGraph. |
| `claude-agent-sdk-single-agent` | Claude Agent SDK | Requires Docker deploy; needs Node + `claude-code`. |
| `claude-agent-sdk-multi-agent` | Claude Agent SDK | Sub-agents pattern. |

Shared code lives outside patterns:

- `tools/` — framework-agnostic tool logic (Code Interpreter).
- `gateway/` — Gateway client + guardrails.
- `patterns/utils/` — auth (`extract_user_id_from_context`), SSM helpers.

The **folder-name prefix is a contract**: the frontend picks a parser
from the prefix (`strands-`, `langgraph-`, `claude-`, `agui-`) — see
ADR-0015.

## Alternatives Considered

- **Pick a single framework and standardize.** Rejected: the "right"
  framework for a given problem changes faster than we want to
  re-architect.
- **Runtime framework switch inside one codebase.** Rejected: creates
  transitive dependency pressure (e.g. LangGraph + Strands + Claude SDK
  all in one wheel) and obscures which code path is live.
- **Separate repo per framework.** Rejected: the infra, tools,
  guardrails, and frontend are shared.

## Consequences

### Positive
- Swapping frameworks is a config change + redeploy.
- Each pattern owns its dependencies → smaller, purpose-built images.
- Shared utilities (`tools/`, `gateway/`, `patterns/utils/`) stay
  framework-agnostic.

### Negative / Trade-offs
- The folder-prefix contract must be preserved when renaming.
- Some patterns have platform constraints (Claude Agent SDK requires
  Docker — ADR-0009).
- Multiple patterns mean more CI permutations to keep green.

### Neutral
- The pattern boundary is enforced by convention, not by a Python
  package layout.

## Implementation Notes

- `patterns/<pattern>/` — entrypoint (e.g. `basic_agent.py`,
  `langgraph_agent.py`, `agent.py`), `requirements.txt`, `Dockerfile`.
- `infra-cdk/lib/backend-stack.ts::createAgentCoreRuntime` — chooses
  Dockerfile / ZIP packaging per pattern; enforces Docker-only
  constraint for Claude SDK (~line 116).
- `infra-cdk/config.yaml` — `backend.pattern` field documents the
  prefix-to-parser mapping.
- `frontend/src/lib/agentcore-client/client.ts::getParser` — routes on
  the same prefix.

## References

- Internal: `docs/AGENT_CONFIGURATION.md`, `docs/AGUI_INTEGRATION.md`,
  `docs/STREAMING.md`
- External: [AG-UI protocol](https://docs.ag-ui.com/concepts/overview)
