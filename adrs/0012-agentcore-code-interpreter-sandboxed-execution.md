# ADR-0012: Use AgentCore Code Interpreter for sandboxed Python execution

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Agent developers, Security
- **Tags:** agentcore, tools, security

## Context

Some citizen inquiries involve lightweight computation — unit
conversions, date math, small CSV analyses of public records. Giving
the agent a Python interpreter is useful, but executing arbitrary
model-generated code in the agent's own process is unsafe (filesystem
access, network egress, dependency injection, etc.).

AgentCore ships a managed **Code Interpreter** service that runs Python
in an isolated sandbox with pre-installed common libraries and session
state that persists across calls.

## Decision

Expose Code Interpreter to the agent as a framework-agnostic tool under
`tools/code_interpreter/`. The tool:

- Starts a session lazily (`start()` on first call) and reuses the
  client for subsequent calls.
- Invokes `executeCode` with `language: "python"` and
  `clearContext: false` so state persists within a session.
- Returns the execution result as a JSON string for the agent to
  consume.
- Exposes `cleanup()` to stop the session explicitly; the service
  times out inactive sessions automatically.

The IAM surface on the agent role is exactly the three actions the SDK
needs — `StartCodeInterpreterSession`, `StopCodeInterpreterSession`,
`InvokeCodeInterpreter` — scoped to
`arn:aws:bedrock-agentcore:${region}:aws:code-interpreter/*`.

Framework-specific wrappers (e.g. `StrandsCodeInterpreterTools`) live
next to the core tool and are imported by the relevant patterns.

## Alternatives Considered

- **Run model-generated code in a subprocess on the runtime
  container.** Rejected: weakest possible sandbox, direct access to
  the container's IAM and filesystem.
- **Stand up a Firecracker/Gvisor sandbox ourselves.** Rejected: large
  ops project, and AgentCore Code Interpreter is exactly this service,
  managed.
- **Disallow code execution entirely.** Rejected: forfeits a genuinely
  useful capability for a narrow set of citizen queries.

## Consequences

### Positive
- Strong isolation by default; no extra infra to operate.
- Session-persistent state enables multi-turn analyses.
- Tool layer is framework-agnostic; patterns add only a thin wrapper.

### Negative / Trade-offs
- Coupling to another AgentCore primitive with its own pricing and
  quotas.
- Sessions are implicit — long-running sessions can leak if
  `cleanup()` isn't called on abnormal exit. Rely on service timeout
  as a backstop.
- No access to private data stores from the sandbox, by design —
  tools that need VPC-scoped data should go through the Gateway
  (ADR-0011), not Code Interpreter.

### Neutral
- Available libraries are whatever Code Interpreter ships; custom
  dependencies are not installable into the sandbox.

## Implementation Notes

- `tools/code_interpreter/code_interpreter_tools.py` — core
  `CodeInterpreterTools` class.
- Strands wrapper used in
  `patterns/strands-single-agent/basic_agent.py`.
- IAM policy in
  `infra-cdk/lib/backend-stack.ts::createAgentCoreRuntime`
  (~line 286).
- `docs/TOOL_AC_CODE_INTERPRETER.md` — usage guide.

## References

- Internal: `docs/TOOL_AC_CODE_INTERPRETER.md`
- External: [Bedrock AgentCore Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter.html)
