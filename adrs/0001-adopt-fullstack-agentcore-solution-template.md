# ADR-0001: Adopt the Fullstack AgentCore Solution Template (FAST) as the baseline

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Maplewood Civic Services team
- **Tags:** foundation, scaffolding

## Context

Maplewood needs a secured, web-accessible agent for handling citizen inquiries
(permits, utilities, public records, 311, etc.). Building all of the
surrounding infrastructure from scratch — authentication, hosting, agent
runtime wiring, tool plumbing, streaming — would take weeks and distract from
the actual civic-domain work (prompt engineering, guardrails, tool design).

FAST is an AWS Labs reference project that ships a deployable full-stack
AgentCore app out of the box: React frontend, Cognito auth, AgentCore Runtime,
AgentCore Gateway with Lambda tools, and optional Memory/Code Interpreter. Its
central — and only — dependency is AgentCore; it is agnostic to agent SDK
(Strands, LangGraph, Claude Agent SDK) and to coding assistant platform.

## Decision

Fork FAST and use it as the baseline for the Maplewood Civic Services Agent.
Customize the agent patterns, tools, and guardrails for the civic domain while
leaving the authentication, hosting, and runtime wiring largely intact.

## Alternatives Considered

- **Build from scratch on raw Bedrock + Lambda/API Gateway.** Rejected: weeks
  of undifferentiated heavy lifting for infra we would end up re-inventing in
  approximately the same shape.
- **Use a single agent framework's opinionated starter (e.g., a pure Strands
  or LangGraph template).** Rejected: couples us to one SDK, and we want the
  option to swap patterns (see ADR-0008).
- **Adopt a third-party agent hosting platform.** Rejected: operating on AWS
  and keeping data in-account is a hard requirement.

## Consequences

### Positive
- Deployable baseline within hours instead of weeks.
- Security-approved defaults (Cognito, IAM scoping, SSL-only S3).
- Built-in documentation-as-context for AI coding assistants
  (`vibe-context/`, `.amazonq/`, `.kiro/`) that accelerates customization.

### Negative / Trade-offs
- Inherits FAST's structural decisions (CDK layout, two-stack topology,
  naming conventions) that we must live with or explicitly diverge from.
- Upstream drift: keeping in sync with FAST releases is a separate concern
  that is not automated.

### Neutral
- FAST is explicitly *not* a production-ready solution; hardening for
  production is our responsibility (see `README.md` security note).

## Implementation Notes

- `README.md` — describes FAST baseline and tenets.
- `CLAUDE.md` — overlays Maplewood-specific conventions onto FAST.
- `vibe-context/` — AI-coding-assistant rules shipped by FAST and reused here.

## References

- Internal: `README.md`, `CLAUDE.md`
- External: [awslabs/fullstack-solution-template-for-agentcore](https://github.com/awslabs/fullstack-solution-template-for-agentcore)
