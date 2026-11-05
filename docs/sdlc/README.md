# MealMate SDLC Documentation — Navigation and Control

**Document set:** v0.1, 2026-11-05. **Status: DRAFT FOR OWNER / ENGINEERING REVIEW.** These are review-ready specifications, not evidence of implementation completion, production readiness, approved runtime architecture, or authorization to merge/code. Scope is **UC-01 only**.

## Intended lifecycle and deliverables

| Phase | Controlled deliverable | Review gate |
| --- | --- | --- |
| Initiation | [PROJECT_CHARTER.md](PROJECT_CHARTER.md), [BRD.md](BRD.md) | Business problem, stakeholder, boundary |
| Requirements | [PRD.md](PRD.md), [SRS.md](SRS.md), [TRACEABILITY.md](TRACEABILITY.md) | Requirements measurable and linked to tests |
| Experience | [UX_SPEC.md](UX_SPEC.md) | UI behavior approved separately (P1) |
| Design | [HLD.md](HLD.md), [LLD_API.md](LLD_API.md), canonical UC-01 and Data Contract | Engineering design, threat model and technical stack approved |
| Quality | [TEST_PLAN.md](TEST_PLAN.md), [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md) | Tests, negative cases, risk sign-off |
| Build and integration | [DELIVERY_PLAN.md](DELIVERY_PLAN.md), [CODEX_HANDOFF.md](CODEX_HANDOFF.md) | Task-level plan reviewed before significant code |
| Release and operate | [OPERATIONS.md](OPERATIONS.md) | Proven E2E, security gate, roll-forward/rollback and owners |

This is a lightweight SDLC documentation system, informed by common requirements/design/test lifecycle practices. **Not a claim of ISO/IEC/IEEE certification**. We deliberately reuse existing canonical material rather than clone it into divergent copies.

## Normative source hierarchy and conflict rule

1. Current applicable [AGENTS.md](../../AGENTS.md) controls agent workflow and repo hygiene; reread before every task.
2. Approved business choices in [PRODUCT.md](../PRODUCT.md), [DECISIONS.md](../DECISIONS.md), the [UC-01 design](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md), and [DATA_CONTRACT.md](../DATA_CONTRACT.md) control product behavior and field semantics.
3. The separate [UC-01 implementation plan](../superpowers/plans/2026-11-04-uc01-first-vertical-slice.md) proposes task interfaces and stack. It is on PR #4's branch, **not yet approved**.
4. This SDLC package organizes requirements, lifecycle and handoff but **does not supersede** canonical UC-01 rules. Conflicts must be logged and resolved explicitly before implementing.
5. Source code/tests and PR metadata establish **actual implementation status**, never the mere presence of documentation.

## Version and approval states

- DRAFT: being reviewed, may change; no inferred permission to implement.
- APPROVED (business): policy choices accepted; **not** technical/merge approval.
- APPROVED (engineering): signed-off technical contract/implementation plan; still no PR merge without authorization.
- IMPLEMENTED: code exists in a named branch/commit; not necessarily tested or merged.
- VERIFIED: check with actual CI/test result, source, commit and date.
- RELEASED: deployed and passed explicit release gate.

**Baseline observed 2026-11-05:** main contains bootstrap only; PR #3 design, PR #4 plan, and PRs #5–#8 Tasks 1–5 are open/stacked (the latter are Draft). PR #8 reports 70 synthetic tests passing on Python 3.12; this is reported branch CI, not independent acceptance or live-provider validation. Tasks 6–9 and public UI are not implemented in this stack. **Codex MUST rediscover statuses before using this observation.**

## Document control and change policy

Each proposed change must identify owning requirement ID, the controlling business decision, impacted API/domain/model/UI/test, acceptance scenarios, and PR/issue. Use a task-scoped PR; do not change product policy in code without product-owner review. Keep historical decisions in [DECISIONS.md](../DECISIONS.md); no parallel decision register. Keep README.md at repo root brief. Evidence and task status belong to GitHub Issues/PRs, not generated screenshots/log dumps in git.

## Immediate handoff gate

Read [CODEX_HANDOFF.md](CODEX_HANDOFF.md). Codex may audit, plan and review against this **draft** package; it must not interpret this document PR as approval to implement, merge or deploy.
