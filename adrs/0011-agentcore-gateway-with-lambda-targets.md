# ADR-0011: Expose tools through AgentCore Gateway with Lambda targets

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Agent developers, Platform
- **Tags:** agentcore, gateway, tools

## Context

The agent needs a safe, extensible way to invoke backend tools
(lookup a permit status, file a 311 request, query public records).
AgentCore Gateway supports two topologies:

- **Standalone MCP Gateway** — tools are built into the gateway
  itself.
- **Lambda targets** — gateway acts as an MCP proxy routing each tool
  call to a dedicated Lambda.

Maplewood tools will eventually span multiple data sources with very
different IAM scopes, languages, and scaling characteristics.

## Decision

Run an AgentCore Gateway with **Lambda targets**, one Lambda per tool.
Gateway configuration:

- Protocol: **MCP** (`supportedVersions: ["2025-03-26"]`).
- Authorizer: **CUSTOM_JWT**, discovery URL = Cognito, allowed clients
  = the machine client (ADR-0005).
- Target credential provider: `GATEWAY_IAM_ROLE` — the Gateway assumes
  a dedicated role with permissions for Lambda invoke, Bedrock
  `InvokeModel`, SSM parameter reads, Cognito describe, and CloudWatch
  Logs. Each tool Lambda has only the IAM it needs.
- Tool schema: loaded from the tool's `tool_spec.json` (inline
  payload), keeping schema next to the Lambda source.

Each tool Lambda follows the "one tool per Lambda" convention:

```python
delimiter = "___"
original = context.client_context.custom["bedrockAgentCoreToolName"]
tool_name = original[original.index(delimiter) + len(delimiter):]
return {"content": [...]}
```

Gateway URL is written to SSM (`/${stack_name_base}/gateway_url`) so
agent patterns read it at runtime without hard-coding.

## Alternatives Considered

- **Standalone MCP Gateway.** Rejected: couples tool logic to gateway
  infrastructure; independent scaling, deploy, and IAM become harder.
- **Direct tool execution inside the agent process.** Rejected:
  blast-radius concerns, conflates agent logic with integration
  code, and loses per-tool IAM.
- **API Gateway + Lambda instead of AgentCore Gateway.** Rejected:
  we'd lose MCP-native tool discovery and Gateway-side auth and tool
  schema handling.

## Consequences

### Positive
- Clean separation of concerns — new tools ship as a Lambda + schema,
  no gateway infra changes.
- Per-tool IAM least privilege.
- Language flexibility per tool (sample tool is Python today; nothing
  stops adding TS/Rust later).
- Gateway handles HTTP / MCP framing; Lambda stays focused on logic.
- Cost scales with actual tool usage.

### Negative / Trade-offs
- Extra hop (Gateway ↔ Lambda) vs. in-process tools — latency cost is
  small but real.
- Gateway IAM role is broad relative to any single tool; new tools
  needing additional AWS access should pass through their own
  Lambda's role, not the gateway role.
- Semantic search for tool discovery is available but off by default
  (commented out in CDK); enable per use case.

### Neutral
- Tool names are namespaced (`<target>___<tool>`); the sample shows
  how to strip the prefix.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts::createAgentCoreGateway`
  (~line 607) — gateway, target, IAM role, SSM output.
- `gateway/tools/sample_tool/` — reference Lambda with
  `tool_spec.json`.
- `patterns/*/tools/gateway.py` (and
  `tools/gateway` imported from patterns) — client-side MCP usage.
- `docs/GATEWAY.md` — architecture walkthrough.

## References

- Internal: `docs/GATEWAY.md`
- External: [Bedrock AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html),
  [Model Context Protocol](https://modelcontextprotocol.io)
