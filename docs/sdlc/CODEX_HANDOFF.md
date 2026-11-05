# Codex Engineering Handoff — MealMate UC-01

**Version:** 0.1 | **Status:** Ready for **repository audit and plan review**, **NOT yet a blanket authorization for implementation or merge**. Prepared 2026-11-05.

## Mission

Continue the existing MealMate repository toward a **verified, source-backed, single-store grocery draft cart** for one shared home-cooked meal. Do not start a new repository and do not fork ShopMate. Do not treat a fluent LLM response as a working cart or pretend current synthetic sources are live supermarket data.

Repository: https://github.com/hungtvb/mealmate

## Mandatory startup order (every independent task)

1. Fetch relevant branch HEAD and reread current AGENTS.md plus nested AGENTS.md in affected paths. Its instructions control workflow and review/merge permissions.
2. Read canonical docs/PRODUCT.md, docs/DECISIONS.md, docs/superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md, docs/DATA_CONTRACT.md, and this docs/sdlc/README.md.
3. Read existing docs/superpowers/plans/2026-11-04-uc01-first-vertical-slice.md from PR #4's branch, plus PR/issue review notes. **Plan/stack approval not presumed.**
4. Inspect GitHub Issue #2 and all PRs #3–#8, their real bases/heads, review threads, last CI jobs, code and changed paths. Some may have changed since this handoff.
5. Produce a short **as-built vs as-designed** audit matrix: FR/AC, existing module/tests, test actually executed, correctness risk, unresolved approval. Do not change code during this audit.
6. Identify the smallest next approved vertical slice, affected files, dependencies, exact behavioral tests and proposed PR base. For significant change, write/seek review of implementation plan before coding.
7. After explicit applicable sign-off: implement with regression/TDD, focused new branch/PR, independently review, synchronize issue and test evidence, never self-merge.

## Canonical source/branch topology at handoff

~~~text
main (bootstrap only)
 └── PR #3 docs/uc01-meal-to-cart-design (business design/data contract)
      ├── this docs-only SDLC handoff PR (parallel documentation review)
      └── PR #4 docs/uc01-implementation-plan (9-task plan)
           └── PR #5 feat/uc01-task01-source-fixtures (Tasks 1–2)
                └── PR #6 feat/uc01-task03-cart-verifier (Task 3)
                     └── PR #7 feat/uc01-task04-allergy-evidence (Task 4)
                          └── PR #8 feat/uc01-task05-bounded-fallback (Task 5)
~~~

All described PRs were open as inspected on 2026-11-05. **Never merge/rebase based on this static map without refreshing GitHub.** Do not create a duplicate Task 1–5 implementation on main.

## Current code modules observed at PR #8 head

Present: source models and ports, packaged synthetic fixture, quantity/pantry resolver, economic cart builder, evidence assessor, bounded source-backed search; deterministic pytest/CI reported. Missing in that stack: persisted session/draft, acceptance revalidation, API, live LLM adapter, UI, public auth and retailer integration. Python 3.12/Pydantic/FastAPI/SQLite choices are in PR #4 **proposed plan**, not automatically signed off.

## Business invariants Codex cannot relax

- Recipe-first, complete versioned curated recipe, role-aware automatic portions; one selected store, one shared meal (several shared dishes allowed).
- Every required quantity derives from recipe source, with canonical unit/form and confirmed pantry; no LLM/heuristic invented recipe amounts.
- Whole sellable packs; exact integer VND subtotal vs hard cap. No tax, shipping or promotions in UC-01 subtotal.
- All purchased SKU/price/stock facts from one coherent snapshot; independently expire, compatible refresh source-attested for every selected SKU; new draft after changes.
- Each declared allergen assessed independently for presence/cross-contact across recipe components, used pantry and selected SKU. Unknown purchased-SKU/recipe evidence blocks accept; pantry-only UNKNOWN may permit **explicit acceptance with prominent warning**; no medical-safety assertion.
- Search at most **three** complete distinct candidates total including initial; do not silently change store, diner count, budget, dislikes, allergies or pantry.
- Explicit Memory: preserve current conversation constraints and draft; only applied material changes revise request. No automatic cross-session health/allergy memory.
- ACCEPTED is a draft only, not order/payment/stock reservation. Must recheck source/recipe/evidence, then dual local request/cart CAS; stale => BLOCKED/RECONFIRM_REQUIRED.

## First engineering audit issues to triage

1. PR #8 currently returns NO_ALLERGY_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET; canonical [UC-01 §6](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) defines NO_ACCEPTABLE_CART_IN_EVALUATED_SET. Confirm intended API/domain vocabulary, add targeted regression, and only change code after review.
2. Current search initial menu without preferred selection chooses one sourced main/shared recipe; canonical golden is a multi-dish shared meal. Verify Task 8 composition behavior before claiming AC01 request-to-cart coverage. Do not assume automatic complete menu has been proven.
3. Task 6–9 may depend on fixing source port/schema limitations; compare to approved implementation plan before interface changes.
4. Current PR #8 pyproject.toml puts FastAPI/httpx under dev extra; when building Task 8 public runtime, review actual runtime dependency packaging rather than relying on CI's dev environment.
5. No live retailer/allergy provenance authenticity assurance or real LLM test evidence in core stack. Report these as limitations instead of suggesting all UC-01 has passed.

5. **Task 6/8 DTO and store-binding gap:** a public `POST /v1/drafts` must not trust client-supplied request/cart IDs, revisions, verification state or `as_of`. Current `MealRequest` has no selected-store field; define server-owned identities and persisted selected-store context before API work. Pin this with contract tests.
6. **External access boundary:** implement owner-scoped session authorization before exposing routes publicly. Until then, use only a loopback-bound synthetic local API; GET must remain non-mutating but show stale source status, and repeated accepts must obey CAS.

## Recommended execution order

**Phase A (audit/approval):** review current stacked diffs, plan/stack approval status and this SDLC package; create a concrete residual issue list and ask for needed technical approval (no repetitive reopening of accepted business-policy A/B decisions).

**Phase B (after approved plan and the Task 6/8 contract gates above):** close existing PR #5–#8 reviews and obtain explicit owner authorization to merge in order; implement Task 6 (persisted effective request + current draft and version CAS), Task 7 (revalidation/acceptance/attested refresh), Task 8 (typed API and real HTTP→service→SQLite synthetic E2E), Task 9 (optional real-provider structured intent). Each task has independent PR and test evidence.

**Phase C (separately approved):** review P1 UX and frontend plan; do not implement live payment, multi-store, medical diet guarantees or multi-agent platform without new scope.

## Codex output contract for each task

Return only verified facts in this structure:
- **Baseline:** branch/ref/sha, AGENTS version, relevant open PRs and approved docs.
- **Requirement:** BR/FR/SRS/AC IDs and expected positive/negative behavior.
- **Change plan:** exact files and interfaces, alternatives considered, why minimal.
- **Execution:** tests first, actual commands, real exit statuses and CI links; classify static/mock/integration/E2E/live.
- **Review:** findings and resolutions, regression risks, design drift.
- **Delivery:** branch/PR, updated issue/AC matrix, known gaps, merge gate still required.

## Handoff prompt to paste into Codex

> You are taking over MealMate (https://github.com/hungtvb/mealmate). First read the **latest applicable AGENTS.md** and docs/sdlc/README.md, then the canonical UC-01, DATA_CONTRACT, DECISIONS, PRD/SRS/HLD/LLD, traceability, test plan and existing PR #4 plan. Inspect Issue #2 and stacked PRs #3–#8 including review threads and actual CI. Do not write code yet. Deliver an evidence-backed status/requirements-gap audit and smallest next implementation plan, with exact affected files, AC test oracles and proposed PR base. Preserve all accepted business policies, never fabricate source data or medical assurances, and never auto-accept a cart. Do not rebuild existing core modules, work on main, self-merge or claim unexecuted E2E/LLM tests. After my approval of the applicable technical plan, implement task-by-task with TDD, independent review and recorded GitHub evidence.

## Definition of successful handoff

Codex can point to one authoritative business contract, one engineering plan (after sign-off), one requirement→AC→test mapping, one repo/PR baseline, visible safety boundaries and clear completion gates. **Handoff of documentation is not a guarantee of full implementation or an authorization to merge.**
