# MealMate — Agent Working Agreement

These rules apply to humans and AI coding agents. **Read the current version of this file before every independent repository task**, from the relevant branch. Also read any nested AGENTS.md for affected paths. Do not rely on a previous session's copy.

## Product boundary
- MealMate helps customers plan **home-cooked meals** and prepare a grocery cart from a single store catalog.
- Initial workflow: meal request -> menu -> ingredient quantities -> available SKUs -> verified draft cart -> human confirmation.
- Source of truth: docs/PRODUCT.md and the currently reviewed use-case design. docs/UC-01.md is a **draft**, not an implementation authorization.
- Do not add unrelated features, multi-agent frameworks, live payments, restaurant ordering, or ShopMate source just to increase technology coverage.

## Working method (Superpowers when available)
1. Understand the business problem, evidence, user outcomes, constraints and failure modes before proposing a solution.
2. For nontrivial work: compare approaches, write a design in docs/superpowers/specs/, and obtain human review/sign-off before implementation.
3. Before **every code change**, state scope, affected files, intended behavior and verification. Small changes can proceed after a short plan; significant changes require an approved design and implementation plan.
4. Write stepwise plans in docs/superpowers/plans/; implement vertical slices with tests (TDD for behavior changes), then request review and verify outcomes.
5. Use Superpowers skills (brainstorming, writing-plans, test-driven-development, requesting-code-review, verification-before-completion) where the agent environment makes them available; follow the same gates if not.
6. No unverified claims: distinguish static checks, mock tests, integration tests and E2E with real providers.

## Repository hygiene
- Work on a dedicated branch and PR. **Never commit feature work directly to main.** The initial README was the one-time bootstrap needed to create a base branch.
- Keep README short; place design rationale in docs/, task tracking in GitHub Issues/PRs, and status/evidence in their associated records.
- Do not merge your own PR without authorization. Sync issue/PR acceptance criteria and verification evidence after each completed task.
- Do not store secrets, personal health data, generated evidence dumps, proprietary ShopMate code without verified permission, or large datasets in git.
- Prefer narrow, cohesive changes; avoid premature abstraction and dead scaffolding.

## Correctness and safety
- Only catalog/pricing/inventory services can provide SKU, stock and price facts; LLM may propose, not invent them.
- A deterministic verifier must enforce quantity, pack-size, budget and catalog consistency.
- Allergies are safety constraints, not preferences. If ingredient/cross-contact evidence is missing, mark uncertain and exclude from an asserted-safe cart; do not claim medical suitability.
- Illness-related nutrition constraints require explicitly provided restrictions; do not infer a treatment diet or dispense medical advice.
- Cart creation is a draft action; purchasing/payment requires separate explicit customer confirmation.

## Task completion checklist
- Updated design/requirements when behavior or decisions changed
- Relevant tests and negative/failure scenarios run with recorded results
- Risks and limitations stated, including anything not tested
- PR/issue references and evidence synchronized
