# ADR-0010: Use AgentCore Memory with short-term conversation history by default

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Agent developers, Platform
- **Tags:** agentcore, memory

## Context

A civic-services agent benefits from remembering what a citizen said
earlier in a session ("the permit I mentioned"), but long-term memory
strategies (extracting facts about a citizen, summarizing past
interactions, learning preferences) raise harder questions: data
minimization, retention, and consent. AgentCore Memory supports both:

- **Short-term:** raw conversation events stored per `actorId` /
  `sessionId`, retained for N days.
- **Long-term:** `SummaryMemoryStrategy`,
  `UserPreferenceMemoryStrategy`, `SemanticMemoryStrategy` that extract
  derived memory via additional model calls.

The `AWS::BedrockAgentCore::Memory` resource is CloudFormation-new
enough that only L1 constructs exist today.

## Decision

Default to **short-term only**: an `AgentMemory` resource with
`MemoryStrategies: []` and a 30-day `EventExpiryDuration`. Grant the
agent role:

- `bedrock-agentcore:CreateEvent`, `GetEvent`, `ListEvents` for writes
  and reads against the session stream.
- `bedrock-agentcore:RetrieveMemoryRecords` included now so adding a
  long-term strategy later does not require an IAM change.

Pass `MEMORY_ID` to the runtime container as an env var; agent code
constructs an `AgentCoreMemorySessionManager` with `(memory_id,
session_id, actor_id)` where `actor_id` is the JWT `sub`.

When long-term strategies are needed for a specific use case, that
becomes a *new* ADR that documents the data-handling implications —
not a silent code change.

## Alternatives Considered

- **Enable long-term strategies now.** Rejected: premature. We haven't
  yet decided what extracted memory is acceptable to store for a
  government-services domain.
- **Roll our own DynamoDB-backed memory.** Rejected: duplicates
  platform capability and breaks the SessionManager integrations in
  Strands/LangGraph.
- **Store memory in the Feedback DynamoDB table.** Rejected: mixing
  concerns; `actorId`/`sessionId` semantics and expiry belong to
  Memory.

## Consequences

### Positive
- Multi-turn context is available in the baseline with one CDK
  resource.
- Forward-compatible IAM means enabling long-term strategies later is
  a one-resource change.
- Clear separation of operational choice (short-term on by default)
  from policy choice (long-term requires a deliberate ADR).

### Negative / Trade-offs
- 30-day retention is a pick; Maplewood legal/compliance may mandate
  shorter. Revisit before go-live.
- L1 construct means no CDK type-safety on memory property shape.

### Neutral
- `Tags: { ManagedBy: "CDK" }` helps cost allocation and tracking.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts` — memory resource at ~line 238 and
  role policy at ~line 259.
- `patterns/strands-single-agent/basic_agent.py::_create_session_manager`
  — agent-side wiring.
- `docs/MEMORY_INTEGRATION.md` — full strategy reference.

## References

- Internal: `docs/MEMORY_INTEGRATION.md`
- External: [Bedrock AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html),
  [AWS::BedrockAgentCore::Memory](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrockagentcore-memory.html)
