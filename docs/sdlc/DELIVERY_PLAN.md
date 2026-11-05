# SDLC Delivery Plan, Change Control and Stage Gates

**Version:** 0.1 | **Status:** DRAFT planning, not an implementation authorization. Implementation source: [existing Superpowers Task 1–9 plan](https://github.com/hungtvb/mealmate/pull/4) on open PR #4.

## Delivery model and task granularity

**Vertical, testable slices** with one owner and meaningful test oracles, not a large frontend-first rebuild. Each significant code change follows: current AGENTS.md → impacted spec/approved implementation plan → branch → RED/implementation/GREEN → scenario regression → independent review → issue/PR evidence → separate owner merge authorization. No direct commit to main; no self-merge.

## Current stacked chain observed on 2026-11-05

| PR | Head / scope | Observed state | Gate still required |
| --- | --- | --- | --- |
| [#3](https://github.com/hungtvb/mealmate/pull/3) | docs/uc01-meal-to-cart-design; UC-01 canonical design + data contract | OPEN, business options approved | Engineering sign-off and explicit merge authorization |
| [#4](https://github.com/hungtvb/mealmate/pull/4) | docs/uc01-implementation-plan; 9-task technical plan | OPEN Draft; review issues reported resolved | **Explicit technical stack/plan approval** |
| [#5](https://github.com/hungtvb/mealmate/pull/5) | Source fixtures + quantity/pantry Tasks 1–2 | OPEN Draft; Python 3.12 CI synthetic reported | Independent code review, authorized merge order |
| [#6](https://github.com/hungtvb/mealmate/pull/6) | Sourced cart economics Task 3 | OPEN Draft, synthetic CI reported | Independent code review, authorized merge |
| [#7](https://github.com/hungtvb/mealmate/pull/7) | FoodEvidence allergen assessor Task 4 | OPEN Draft, synthetic CI reported | Independent code review, authorized merge |
| [#8](https://github.com/hungtvb/mealmate/pull/8) | Bounded fallback Task 5 | OPEN Draft; reports 70 Python 3.12 synthetic tests | Fresh review/CI and authorized merge |
| This SDLC PR | Documentation/control and handoff only | Draft review | Owner review; no app code or automatic go-ahead |

This table is a dated baseline only. Codex **must re-query live GitHub** and respect actual PR bases/head commits.

## Implementation sequence after review gates

| Stage | Scope | Proof and delivery checkpoint |
| --- | --- | --- |
| G0 Business | Validate canonical source, baseline and traceability | Approved UC-01 choices, open differences registered |
| G1 Engineering design | Approve PR #4 plan/stack and any LLD/API conflicts; align this SDLC suite | Named reviewers and explicit owner sign-off |
| G2 Existing deterministic core | Independently review/resolve PR #5–#8 and merge only when authorized in dependency order | Actual Python 3.12 CI, negative tests and patch review |
| G3 Task 6 | Persist MealRequest + DraftCart + session TTL/deletion; applied vs read-only; immutable accepted drafts | Restart, dual CAS, AC20/26/27 tests |
| G4 Task 7 | Acceptance-time snapshot/evidence/recipe revision checking and compatible refresh | AC08/19/21/28/33 and concurrent race tests |
| G5 Task 8 | Thin FastAPI and deterministic HTTP/service/SQLite E2E | Actual AC01/24/27/33 HTTP test + clean CI |
| G6 Task 9 | Optional configured provider structured-intent boundary | Real live_llm collected/executed >0, non-mutating adverse tests |
| G7 Consumer UI (separate P1 approval) | Accessible chat, editable menu/cart, warning/accept controls | UX review and browser E2E |
| G8 Production integration (separate future use case) | Real retailer/auth/deploy/operations | Vendor contract, threat review, release checklist, rollback |

Do **not** turn G6/G7/G8 into blockers for completing G5 deterministic first slice; always label which capability is being claimed.

## Decision gates / change requests

A material change request needs: reason and user impact, business-rule ID and affected AC, alternatives considered, implementation/data/API/UI/test impacts, risks, review owner and rollback consideration. Record accepted changes in [DECISIONS.md](../DECISIONS.md), update relevant canonical spec and [TRACEABILITY.md](TRACEABILITY.md), then create a scoped implementation PR. Avoid duplicate documents or “requirements by chat only.”

**Potential integration discrepancy:** current Task 5 outcome string for evidence-ineligible candidate differs from canonical UC-01. Log and resolve with one test, not a blanket rename. Verify initial shared-dish composition requirement in Task 8; current pure search initial candidate may not represent the full golden menu by itself. Avoid assuming these are already fixed or production defects without executing full scenarios.

## Definition of Ready (per code task)

Approved boundary and design; owner-known constraints and negative cases; cited source/data contract; one task-sized plan with affected files; test oracle for both success and rejection; PR base selected; secrets/CI strategy clear.

## Definition of Done (per task)

Actual behavior implemented at specified commit, tests run and recorded with exact environment/counts, negative case covered, lint/import/build applicable, independent review feedback addressed, requirements and issue/PR acceptance updated, limitations declared. **No status promotion based solely on code presence, mock assertions or the agent's own summary.**

## Release gating

First release gate is a working local fixture-backed API, **not** production launch. Public launch requires independently approved identity/access isolation, real source correctness, legal/privacy review, secrets handling, operational monitoring and rollback. See [OPERATIONS](OPERATIONS.md).
