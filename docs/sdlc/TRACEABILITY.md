# Requirements Traceability Matrix — UC-01

**Version:** 0.1 | **Status:** DRAFT. Maps business needs → PRD FR → SRS → acceptance scenario → delivery task/test. **Mapping is not a test execution claim.** Canonical expected results live in [UC-01](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md).

## Business need to functional and architecture owners

| Business need | FR IDs | SRS IDs | Primary design component |
| --- | --- | --- | --- |
| BN-01 Curated shared meal | FR-01/03/04 | SRS-01/02 | RecipeSource, planner |
| BN-02 Quantity correctness | FR-04/05 | SRS-02/03 | resolve_needs |
| BN-03 Confirmed pantry | FR-02/05 | SRS-03/08 | PantryAllocation and effective request |
| BN-04 Whole-pack budget | FR-06/09 | SRS-04/05/07 | cart_builder and search |
| BN-05 Single-store feasibility | FR-06/07/12 | SRS-04/05/09 | CatalogSource, acceptance revalidator |
| BN-06 Scoped allergy evidence | FR-08/10/12 | SRS-06/09 | allergens, EvidenceSource |
| BN-07 Sourced alternatives | FR-09/10 | SRS-07 | search_candidates |
| BN-08 Revision-safe conversation | FR-02/11/15 | SRS-08/11 | DraftRepository, MealService, IntentInterpreter |
| BN-09 Human acceptance | FR-10/12/13 | SRS-09/10 | service.accept, HTTP API |
| Future P1 UI | FR-16 | SRS-12 | Consumer client, separate design gate |

## Complete AC index, task and priority

| AC | Behavior to prove | FR | Planned task | Minimum automated layer |
| --- | --- | --- | --- | --- |
| 01 | Golden 116000 VND, 5 lines/6 packs | 03/05/06/10 | T1–3, T8 | Deterministic + HTTP E2E |
| 02 | Non-spicy source eligibility | 03 | T1, T5, T8 | Eligibility + API |
| 03 | Known shrimp allergy conflict | 08 | T4, T8 | Allergen + HTTP E2E |
| 04 | Confirmed pantry rice, oil unknown | 01/05 | T2, T8 | Quantity + API |
| 05 | Missing price/stale stock fail closed | 07 | T1, T3, T8 | Source + API |
| 06 | Full-pack rounding 600g/500g | 05/06 | T2–3 | Deterministic |
| 07 | Replace dish, preserve constraints | 03/11 | T6, T8–9 | Session + chat E2E |
| 08 | Explicit verified draft approval, no order | 12/13 | T7–8 | API/DB E2E |
| 09 | Pinned repriced 148000 candidate fails | 06 | T3/5 | Cart/fallback |
| 10 | Snapshot changed after draft | 07/12 | T7–8 | Acceptance E2E |
| 11 | Raw/cooked conversion requires factor | 05 | T2 | Quantities negative |
| 12 | Cross-recipe aggregation before rounding | 05 | T2–3 | Quantities/cart |
| 13 | Role-specific portions for shared 3-dish meal | 03/04 | T1/5/8 | Planner + E2E |
| 14 | Reject one SKU reused across distinct demands | 06 | T3 | Cart negative |
| 15 | Unknown seasoning/pantry allergen assessment | 08 | T4, T8 | Evidence + HTTP |
| 16 | Multiple blockers stock/ingredient retained | 07/08/10 | T3–5, T8 | Composite failure |
| 17 | Per-allergen UNKNOWN cross contact on SKU | 08/12 | T4, T7–8 | Evidence + acceptance |
| 18 | Distinct pantry IDs and recipe version | 05/08 | T2/4/7 | Provenance/version |
| 19 | Acceptance after stock expiry | 07/12 | T7–8 | Acceptance E2E |
| 20 | Applied material edit vs stale accept CAS | 02/11/12 | T6–8 | Concurrency E2E |
| 21 | Pantry-only unknown allowed with warning | 08/12 | T4/7/8 | Allergen + acceptance |
| 22 | No allergens => NOT_ASSESSED | 08/10 | T4/8 | Allergen/UI text |
| 23 | Exactly 3 candidates, no C04 | 09 | T5 | Bounded search |
| 24 | Unknown purchased SKU blocks accept | 08/12 | T4/7/8 | Acceptance E2E |
| 25 | Evinced tomato alternate 120000 | 06/08/09 | T3–5, T7 | Substitution |
| 26 | R04 edit 4→6, 132000, 7 packs | 04/05/11 | T2/6/8 | Session/cart E2E |
| 27 | Explanation/hypothetical read-only | 02/11 | T6/8/9 | Session/chat E2E |
| 28 | Recipe/label revision prevents acceptance | 07/08/12 | T4/7/8 | Acceptance race |
| 29 | Reprice fallback, ALT 120000 | 09 | T3/5/8 | Search + API |
| 30 | Tofu stock fallback, ALT 119000 | 09 | T3/5/8 | Search + API |
| 31 | Single selected store, coherent snapshot | 06/07 | T1/3/5/8 | Source/cart |
| 32 | No incompatible separate per-diner meals | 03/08 | T5/8 | Eligibility/API |
| 33 | Stock expires before price, attested refresh | 07/12 | T1/7/8 | Source/acceptance E2E |

FR IDs above omit the literal FR- prefix to keep table legible. All AC rows refer to the **canonical** expected outcomes, not new business policy.

## Test status lifecycle

Each row requires an actual named test and evidence record with:
- test identifier/path, AC/FR IDs, happy or negative category, fixture or source revision;
- environment (Python version, test lane, provider type), exact commit and CI run URL;
- observed result PASS / FAIL / NOT_RUN; skip count and reason;
- reviewer, issue/PR reference and outstanding limitation.

A test existing in open PR #5–#8 counts as **code present in branch**, not merged acceptance. As of inspected 2026-11-05 PR #8 reports **70 synthetic passing tests** in CI; that is evidence reported for deterministic core, not 33 API E2E scenarios, real LLM or real retailer. Tasks 6–9 and HTTP acceptance are **not implemented in that stack**.

## Open trace gaps requiring Codex review

| Gap | Evidence | Next action |
| --- | --- | --- |
| GAP-01 Stable search failure outcome name differs | Canonical no-acceptable outcome vs PR #8 NO_ALLERGY_ELIGIBLE... | Agree contract; add regression test and align response |
| GAP-02 Golden shared multi-dish creation via initial request not yet proven | Current search.py creates first main/shared dish when no preferred candidate; golden uses three dishes | Verify T8 request-to-menu composition, ensure sourced role-aware menu |
| GAP-03 Durable effective request + draft missing | No drafts.py/service.py in reviewed PR #8 | Implement T6 after plan approval |
| GAP-04 Snapshot/evidence acceptance race unproved in API | T7 not present | AC19/20/28/33 integration E2E |
| GAP-05 Public ownership/authn boundary TBD | No public deployment design | Separate security release gate |
| GAP-06 Live provider/retailer verification absent | Fixture-backed source, no llm_intent.py or retailer adapter | T9 live lane and future source integration |
| GAP-07 Consumer UX not designed/approved for code | P1 UX_SPEC is proposal | UX review and UI implementation plan |
| GAP-08 Exact API payload/status code freeze pending | Task 8 interfaces proposed, not implemented | Contract tests and engineering approval |

The gap list is a **dated review backlog**, not all confirmed runtime defects. Do not close from a prose statement; attach test and reviewer evidence.
