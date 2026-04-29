# ADR-0007: Run agents on Bedrock AgentCore Runtime

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform, Agent developers
- **Tags:** runtime, agentcore

## Context

We need a managed execution environment for long-running, streaming,
tool-using agents that:

- Terminates Cognito JWTs and propagates trusted user identity into the
  agent (instead of trusting a `user_id` in the payload body).
- Streams responses back over HTTP/SSE without us operating a load
  balancer, ECS/EKS, or API Gateway WebSocket plumbing.
- Integrates natively with AgentCore Memory, Gateway, Identity, and Code
  Interpreter.
- Supports deployment both as a Docker image (ECR) and as a zipped Python
  runtime (S3) — see ADR-0009.

## Decision

Host the agent on **Amazon Bedrock AgentCore Runtime**. Key settings:

- **Authorizer:** JWT (`RuntimeAuthorizerConfiguration.usingJWT`) pointed
  at the Cognito discovery URL with the user-pool client ID as allowed
  audience.
- **Protocol:** HTTP (the AG-UI patterns also deploy as HTTP today because
  CloudFormation does not yet accept an `AGUI` enum).
- **Network mode:** configurable per `config.yaml`.
  - `PUBLIC` (default) — runtime is internet-accessible through AgentCore.
  - `VPC` — imports a user-provided VPC, subnets, and optional SGs for
    private-network isolation. Operators are responsible for the required
    VPC endpoints (see `docs/DEPLOYMENT.md`).
- **Request header allow-list:** `Authorization` only, so the agent can
  safely extract `sub` from the validated JWT rather than trusting the
  request body.
- **Execution role:** a dedicated `AgentCoreRole` with least-privilege
  grants for Memory, Gateway SSM lookup, Code Interpreter, OAuth2
  credential provider, and the two relevant Secrets Manager entries.
- **Environment variables:** `MEMORY_ID`, `STACK_NAME`,
  `GATEWAY_CREDENTIAL_PROVIDER_NAME`, plus `CLAUDE_CODE_USE_BEDROCK=1`
  for Claude Agent SDK patterns.

## Alternatives Considered

- **Host the agent on ECS Fargate behind API Gateway.** Rejected:
  requires us to build JWT auth, streaming, session routing, and
  AgentCore integration ourselves.
- **Lambda + Function URL.** Rejected: 15-minute cap, no native streaming
  story that matches AgentCore's, and no tie-in to Memory/Gateway.
- **App Runner.** Rejected: no AgentCore integration.

## Consequences

### Positive
- Managed JWT enforcement means no custom authorizer code.
- Native streaming over SSE suits multi-turn, tool-using agents.
- Clean integration with the other AgentCore primitives (Memory, Gateway,
  Identity, Code Interpreter).
- VPC mode is a single config switch when required.

### Negative / Trade-offs
- Coupling to AgentCore — portability off the platform is a project of
  its own.
- Alpha CDK L2 plus raw L1 for some related resources; API surface may
  shift.
- AG-UI protocol isn't fully modeled in CloudFormation yet (a known gap
  called out in `backend-stack.ts` comments).

### Neutral
- IAM grants live on the shared `AgentCoreRole`; as new tools are added,
  be deliberate about scoping additions.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts::createAgentCoreRuntime` — runtime
  creation (~line 353), JWT authorizer (~line 228), network configuration
  builder (~line 951), execution-role grants (~lines 258–333).
- `infra-cdk/lib/utils/agentcore-role.ts` — execution role construct.
- `patterns/utils/auth.py::extract_user_id_from_context` — trusted
  user-ID extraction from the validated JWT.

## References

- Internal: `docs/DEPLOYMENT.md`, `docs/STREAMING.md`
- External: [Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
