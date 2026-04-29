# Architectural Decision Records

This directory captures the architectural decisions that shape the Maplewood
Civic Services Agent and its underlying Fullstack AgentCore Solution Template
(FAST) foundation. Each ADR describes a single decision — the context, the
choice, the alternatives considered, and the consequences.

## Conventions

- Use `TEMPLATE.md` as the starting point for new ADRs.
- Number ADRs sequentially: `NNNN-kebab-case-title.md`.
- Never rewrite the intent of an accepted ADR. If a decision changes, write a
  new ADR and mark the old one `Superseded by ADR-XXXX`.
- Keep ADRs short and decision-focused. Implementation details that change
  over time belong in `docs/`, not here.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-adopt-fullstack-agentcore-solution-template.md) | Adopt the Fullstack AgentCore Solution Template (FAST) as the baseline | Accepted |
| [0002](0002-infrastructure-as-code-cdk-primary-terraform-alternative.md) | AWS CDK as primary IaC with Terraform as supported alternative | Accepted |
| [0003](0003-frontend-hosting-on-aws-amplify.md) | Host the React frontend on AWS Amplify Hosting | Accepted |
| [0004](0004-cognito-user-pool-for-user-authentication.md) | Use Amazon Cognito User Pool for end-user authentication | Accepted |
| [0005](0005-m2m-authentication-via-cognito-machine-client.md) | Machine-to-machine auth via a dedicated Cognito machine client | Accepted |
| [0006](0006-agentcore-identity-oauth2-credential-provider-token-vault.md) | Broker Runtime→Gateway tokens through AgentCore Identity Token Vault | Accepted |
| [0007](0007-bedrock-agentcore-runtime-for-agent-hosting.md) | Run agents on Bedrock AgentCore Runtime | Accepted |
| [0008](0008-agent-framework-agnostic-patterns-directory.md) | Framework-agnostic agent patterns directory | Accepted |
| [0009](0009-agent-deployment-docker-vs-zip.md) | Support both Docker and ZIP deployment modes for agents | Accepted |
| [0010](0010-agentcore-memory-short-term-default.md) | Use AgentCore Memory with short-term conversation history by default | Accepted |
| [0011](0011-agentcore-gateway-with-lambda-targets.md) | Expose tools through AgentCore Gateway with Lambda targets | Accepted |
| [0012](0012-agentcore-code-interpreter-sandboxed-execution.md) | Use AgentCore Code Interpreter for sandboxed Python execution | Accepted |
| [0013](0013-prompt-based-guardrails-for-civic-domain.md) | Enforce civic-domain guardrails via structured prompt injection | Accepted |
| [0014](0014-feedback-api-gateway-dynamodb-lambda.md) | Feedback API on API Gateway + Lambda + DynamoDB | Accepted |
| [0015](0015-frontend-streaming-via-pluggable-sse-parsers.md) | Pluggable SSE parsers in the frontend AgentCore client | Accepted |
| [0016](0016-amazon-bedrock-as-llm-provider.md) | Use Amazon Bedrock as the LLM provider | Accepted |
