# Agent-Ready Repository Bootstrap — Design

**Status:** Bootstrap scope. This document does not approve the MealMate application design.

## Intent
Make an empty GitHub repository usable by AI agents for business-first design and PR-based collaboration while deliberately **not** scaffolding application code.

## Approaches
1. Full ShopMate fork — fastest code import, but inherits domain and correctness issues. Rejected by selective reuse direction.
2. Full application scaffold — gives runnable framework before UC-01/data design, at high risk of premature architecture.
3. **Lean docs-first bootstrap (selected for this task)** — README, AGENTS.md, product scope, UC draft, architecture direction, PR/issue templates and safe ignore rules. No runtime dependencies.

## Goals
- Clear starting context for any agent session
- Review gates for design, code, tests and PR
- Shared business goal, initial scenario and safety boundaries
- Source of truth and docs navigation without governance overload

## Non-goals
- No backend, frontend, model provider, vector DB, data seeding or CI runner in this task
- No imported ShopMate code
- No claims that UC-01 acceptance criteria are yet passing

## Repo workflow
One minimal initial README commit was required on the empty default branch. All remaining setup is proposed by a dedicated bootstrap PR. Future work must use feature branches and PRs.

## Next step
Review and approve UC-01/data contracts; then use superpowers:writing-plans to plan a narrow vertical slice with tests.
