# ADR-0002: AWS CDK as primary IaC with Terraform as supported alternative

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform / Infra
- **Tags:** infra, iac

## Context

The project needs reproducible, reviewable infrastructure deployments for
Cognito, AgentCore Runtime/Gateway/Memory, Amplify, API Gateway, Lambda,
DynamoDB, and supporting IAM. Two mainstream choices exist in the AWS
ecosystem: AWS CDK (TypeScript) and Terraform. FAST ships both to accommodate
teams standardized on either tool.

Some AgentCore resources are new enough that only **L1 CloudFormation
constructs** exist (e.g. `AWS::BedrockAgentCore::Memory`,
`AWS::BedrockAgentCore::Gateway`), while others have alpha L2 constructs
(`@aws-cdk/aws-bedrock-agentcore-alpha`). This favors an IaC tool that can
drop cleanly into CloudFormation L1 resources when needed.

## Decision

Use **AWS CDK (TypeScript) as the primary IaC** under `infra-cdk/`, nested
stacks composed by `FastMainStack` (Amplify → Cognito → Backend). Keep
`infra-terraform/` as a first-class alternative so teams that prefer Terraform
can deploy the same architecture. Teams should pick one and delete the other
from their fork.

## Alternatives Considered

- **Terraform only.** Rejected as primary: mixing alpha L2 AgentCore
  constructs with raw CloudFormation L1 is ergonomically cleaner in CDK; the
  Terraform path exists for teams that require it.
- **SAM / Serverless Framework.** Rejected: weaker first-class support for
  the full breadth of AgentCore resources.
- **Pulumi.** Rejected: smaller operator community in-house; no clear
  advantage over CDK for this stack.

## Consequences

### Positive
- CDK L2 + L1 interop lets us use ergonomic constructs where available and
  fall back to `cdk.CfnResource` for bleeding-edge AgentCore features.
- Nested-stack topology keeps Amplify, Cognito, and Backend concerns
  logically separated while deploying atomically.
- TypeScript authoring enables IDE type-checking on stack props and outputs.

### Negative / Trade-offs
- Two IaC implementations to keep in sync when FAST evolves.
- CDK alpha constructs can change signatures between releases.
- TypeScript is an added skill beyond Python (the agent code language).

### Neutral
- `cdk.out/` is generated; do not commit synth artifacts.

## Implementation Notes

- `infra-cdk/bin/` — CDK app entry point.
- `infra-cdk/lib/fast-main-stack.ts` — top-level stack wiring Amplify,
  Cognito, and Backend nested stacks.
- `infra-cdk/lib/backend-stack.ts` — AgentCore Runtime, Gateway, Memory,
  Feedback API, and IAM.
- `infra-cdk/config.yaml` — deployment configuration.
- `infra-terraform/` — alternative Terraform implementation with matching
  modules (`amplify-hosting/`, `cognito/`, `backend/`).

## References

- Internal: `docs/DEPLOYMENT.md`, `docs/TERRAFORM_DEPLOYMENT.md`
- External: [AWS CDK v2](https://docs.aws.amazon.com/cdk/v2/guide/home.html),
  [@aws-cdk/aws-bedrock-agentcore-alpha](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-bedrock-agentcore-alpha-readme.html)
