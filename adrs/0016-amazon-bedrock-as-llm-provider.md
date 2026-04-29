# ADR-0016: Use Amazon Bedrock as the LLM provider

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform, Security, Agent developers
- **Tags:** bedrock, model, agentcore

## Context

Every agent pattern needs an LLM to reason, plan tool calls, and
compose responses. The options break down along two axes:

- **Where the model runs** — Amazon Bedrock (in-account, IAM-gated),
  Anthropic's API directly, OpenAI, Azure OpenAI, self-hosted, etc.
- **Which models are exposed** — a single provider locks us in;
  Bedrock gives us a catalog behind one IAM boundary.

We also have strong project-level constraints: Maplewood data stays
in AWS accounts under existing security review, AgentCore Runtime
itself is a Bedrock service, and some patterns (Claude Agent SDK) ship
a `CLAUDE_CODE_USE_BEDROCK=1` switch precisely so they can use Bedrock
instead of Anthropic's API.

## Decision

Standardize on **Amazon Bedrock** as the LLM provider across all agent
patterns:

- **Strands** patterns use `BedrockModel(model_id=...)` from
  `strands.models`.
- **LangGraph** patterns use LangChain's Bedrock integration
  (`ChatBedrock`).
- **Claude Agent SDK** patterns set `CLAUDE_CODE_USE_BEDROCK=1` in
  the runtime env so `claude-code` routes through Bedrock rather than
  calling Anthropic directly.

**Default model** across Strands / LangGraph / AG-UI patterns today:
`us.anthropic.claude-sonnet-4-5-20250929-v1:0` (Claude Sonnet 4.5 via
a US cross-region inference profile). Claude Agent SDK patterns default
to Opus (`us.anthropic.claude-opus-4-6-v1`) for orchestration; the
multi-agent pattern delegates some subagent work to Sonnet.

**IAM:** the agent execution role and the Gateway role are granted
`bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`
against *region-agnostic* resources (`arn:aws:bedrock:*::foundation-model/*`
and `arn:aws:bedrock:*:${account}:inference-profile/*`), because
cross-region inference profiles are the recommended way to access the
latest Claude models.

Model IDs are expressed as code constants in each pattern so:
- a swap is a local PR to a single file;
- the frontend (via ADR-0015) does not care which model produced the
  stream.

## Alternatives Considered

- **Anthropic API directly.** Rejected: moves model traffic and
  billing outside AWS, adds a second vendor to security-review,
  duplicates auth handling.
- **OpenAI / Azure OpenAI.** Rejected: same out-of-account concerns;
  no integration with AgentCore services beyond generic HTTP.
- **Self-hosted open models (SageMaker / Bedrock custom models).**
  Rejected for v1: operational weight is not justified by a
  citizen-inquiries workload; revisit if specific domain tuning
  becomes necessary.
- **Bedrock with a smaller/faster default (Haiku).** Rejected as
  default: early tool-use quality matters more than per-token cost
  for the initial rollout. Per-pattern override remains trivial.

## Consequences

### Positive
- All LLM traffic stays inside the AWS account under existing IAM
  and CloudTrail.
- Cross-region inference profiles (`us.*`) give resilience and
  access to the latest model versions without changing IAM.
- One billing boundary (AWS) for all model usage.
- Uniform Bedrock integration across frameworks — the per-pattern
  code is a one-liner.

### Negative / Trade-offs
- Locks us to models Bedrock exposes. Feature parity with upstream
  (Anthropic API) can lag by days.
- Wildcard resource scope (`foundation-model/*`,
  `inference-profile/*`) is broad; tighten to specific model ARNs if
  Maplewood security policy requires.
- Costs on the Opus default (Claude Agent SDK patterns) are
  materially higher than Sonnet. Revisit if those patterns go into
  production for Maplewood.

### Neutral
- Model-version pinning lives in code constants, not CDK. Revisit
  during normal PR review, not deploy-time configuration.

## Implementation Notes

- `patterns/strands-single-agent/basic_agent.py` — `BedrockModel`
  instantiation with Sonnet model id.
- `patterns/langgraph-single-agent/langgraph_agent.py` and
  `patterns/agui-langgraph-agent/agent.py` — LangChain Bedrock with
  the same model id.
- `patterns/claude-agent-sdk-*-agent/agent.py` — Opus model; Bedrock
  routing via `CLAUDE_CODE_USE_BEDROCK` env var set in
  `infra-cdk/lib/backend-stack.ts` (~line 345).
- `infra-cdk/lib/backend-stack.ts::createAgentCoreGateway` — Gateway
  role grants `bedrock:InvokeModel*` (~line 631).
- `infra-cdk/lib/utils/agentcore-role.ts` — agent execution role
  (Bedrock permissions live on this construct).

## References

- Internal: `patterns/*/README.md`, `docs/AGENT_CONFIGURATION.md`
- External: [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html),
  [Bedrock cross-region inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html),
  [Claude on Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)
