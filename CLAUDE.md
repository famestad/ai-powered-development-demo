# Maplewood Civic Services Agent

Fullstack AI agent for city hall citizen inquiries, built on the FAST template
(AWS AgentCore + React frontend).

## Project Structure

- `frontend/` — React + TypeScript + Vite + Tailwind + shadcn
- `patterns/` — Agent implementations (Strands, LangGraph)
- `tools/` — Framework-agnostic tool implementations
- `gateway/` — Gateway Lambda tools behind AgentCore Gateway
- `infra-cdk/` — CDK infrastructure
- `docs/` — Deployment and configuration guides

## Working with Pulse

Pulse (@pulse) is the project management agent. It manages Asana tasks, creates
GitHub issues, and coordinates work across the team.

When you complete work on a GitHub issue:
- Comment on the issue with a summary of what you did
- @mention @pulse to review your work and decide next steps
- Example: "@pulse implementation complete — please review and assign next task"

When you need a decision or approval before proceeding:
- Do NOT proceed without approval on non-trivial architectural decisions
- Comment on the issue explaining the options and tradeoffs
- @mention @pulse for review: "@pulse I need a decision on X vs Y before continuing"
- Wait for Pulse to respond before implementing

When you encounter a blocker:
- Comment on the issue describing the blocker
- @mention @pulse: "@pulse blocked — need Z to continue"

## Conventions

- This is a civic services demo for the City of Maplewood
- Agent handles: permits, utilities, public records, city council, parks & rec,
  311 service requests, and zoning inquiries
- Keep code changes focused on the issue you're assigned to
- Write tests for new functionality
- Do not modify infrastructure (CDK) without explicit approval
