# ADR-0009: Support both Docker and ZIP deployment modes for agents

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform, Agent developers
- **Tags:** runtime, deployment

## Context

AgentCore Runtime accepts agent artifacts in two shapes:

1. A container image in ECR (`AgentRuntimeArtifact.fromAsset`) — needs
   Docker available at deploy time.
2. A Python ZIP in S3 (`AgentRuntimeArtifact.fromS3`) — no Docker needed,
   but limited to Python agents that can run under the managed runtime.

Operators have different constraints: some CI environments block Docker,
some agent frameworks (notably Claude Agent SDK) require Node.js plus the
`claude-code` CLI inside the image and therefore *must* ship as Docker.

## Decision

Support both modes, selected by `config.yaml::backend.deployment_type`:

- `docker` (default) — CDK builds an image from
  `patterns/<pattern>/Dockerfile` for `linux/arm64` and pushes to ECR.
- `zip` — CDK reads every `.py` file in the selected pattern plus shared
  `gateway/` and `tools/` modules, base64-encodes them, and passes them
  to a **zip-packager Lambda** that assembles `deployment_package.zip`
  in an S3 bucket. A content hash over the requirements and source
  drives change detection so `cdk deploy` only re-packages when inputs
  change.

Claude-Agent-SDK patterns raise at synth time if `zip` is selected —
they need Docker.

## Alternatives Considered

- **Docker-only.** Rejected: blocks users in Docker-restricted CI
  environments and is overkill for simple Python patterns.
- **ZIP-only.** Rejected: Claude Agent SDK patterns can't be expressed
  as a flat Python ZIP, and Docker gives more reproducible agent
  environments.
- **SAM-style bundled layers.** Rejected: AgentCore Runtime expects one
  of its two supported artifact shapes.

## Consequences

### Positive
- Developers without Docker can still iterate (zip path).
- Reproducibility / heavy dependencies live in Docker path.
- Dockerless path is deterministic via a content-hash-driven custom
  resource.

### Negative / Trade-offs
- Two deploy code paths to keep working (more CI surface).
- The zip path recursively walks `gateway/` and `tools/`; new shared
  directories must be added explicitly (see `backend-stack.ts`).
- A hard fail for Claude SDK + zip is good safety but is an easy
  stumbling block for new contributors.

### Neutral
- Images target `linux/arm64` to match Graviton-based Lambda layers
  used elsewhere in the stack (e.g. Powertools layer on Feedback
  Lambda).

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts::createAgentCoreRuntime` —
  branch at ~line 123 (`deploymentType === "zip"`). Zip path uses
  `ZipPackagerLambda` + `cr.Provider`; Docker path uses
  `AgentRuntimeArtifact.fromAsset`.
- `infra-cdk/lambdas/zip-packager/` — packaging Lambda source.
- `patterns/<pattern>/Dockerfile` — per-pattern images.
- Guard for Claude SDK patterns at ~line 116 raises a clear deploy-time
  error.

## References

- Internal: `docs/DEPLOYMENT.md`
- External: [Bedrock AgentCore Runtime artifacts](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-artifacts.html)
