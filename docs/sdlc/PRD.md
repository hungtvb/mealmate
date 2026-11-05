# Product Requirements Document (PRD) — MealMate UC-01

**Version:** 0.2 | **Status:** DRAFT for SDLC review (business options referenced here are already accepted in canonical UC-01; this document does not approve runtime/UI implementation). **Primary feature:** Request → Meal Plan → Verified Grocery Draft Cart.

## Product promise, audience and measures

A Vietnamese-first household shopping assistant for **one shared home-cooked meal** at **one selected supermarket**. Instead of a free-form grocery guess it presents curated recipes, sourced ingredient allocations and a checkable draft-cart quote with disclosure of missing/expired evidence. Primary actor is the household shopper; API/data providers are external dependencies.

Success means **no unsupported “VERIFIED” cart or allergy-safe claim**, a correct whole-pack subtotal or honest bounded failure, no implicit accept, preservation of explicit constraints, and acceptance-time revalidation. Quantitative adoption/latency targets require baselines; none is invented here.

## Scope and priority

| Priority | Feature area | Outcome |
| --- | --- | --- |
| P0 | Request intake | Typed diners/meal type/budget VND/dislikes/dietary/allergens/pantry; clarify missing essential facts |
| P0 | Curated meal planning | Versioned complete recipes; shared dishes; source-based editable portion roles/yields |
| P0 | Ingredient/pantry math | Aggregate canonical needs before rounding; confirmed pantry allocation with identity trace |
| P0 | Retail matching | One coherent store snapshot; verified pack sizes, prices, stocks and budget |
| P0 | Food evidence | Per-allergen ingredient and cross-contact assessment across used recipe/SKU/pantry subjects |
| P0 | Alternatives | Up to three complete sourced candidate evaluations including initial; no auto-relaxation |
| P0 | Active session and revisions | Persist effective constraints and draft; distinguish explanations, hypothetical and applied changes |
| P0 | Draft review/accept | Explicit action, current source/evidence revisions and local CAS; **no checkout** |
| P0 | API, deterministic tests, optional LLM | Typed HTTP and structured intent boundary; real provider lane independently verified |
| P1 (separate design gate) | Consumer UI | Chat, dish/portion editing, cart breakdown, warnings, version-safe accept |
| Deferred | Retailer checkout, multi-store, per-diner menus, medical plans, long-term allergy profile, MCP/RAG/multi-agent platform | Requires a new use case and design |

## User journeys and functional requirements

| ID | Need / observable behavior | Priority | Main AC |
| --- | --- | --- | --- |
| FR-01 | Parse/create typed request with required diners, selected store, meal type and positive integer-VND budget; no made-up facts | P0 | 01/04 |
| FR-02 | Retain session-scoped explicit constraints, support finite TTL and deletion | P0 | 20/27 |
| FR-03 | Select eligible complete curated recipes from source (never LLM-generated quantities) | P0 | 02/13/32 |
| FR-04 | Set role-aware servings automatically and allow applying edits with full recalculation | P0 | 13/26 |
| FR-05 | Canonicalize and aggregate ingredients, subtract only confirmed pantry, preserve component/package trace | P0 | 04/11/12/18 |
| FR-06 | Select source-backed SKU and verify whole-pack cost/budget on one store/snapshot | P0 | 01/06/09/14/31 |
| FR-07 | Treat price/stock independent expiry, compatibility and source version as mandatory | P0 | 05/19/28/33 |
| FR-08 | Independently assess each allergen across recipe/SKU/pantry subject with scoped evidence | P0 | 03/15/17/21/24/25 |
| FR-09 | Generate at most three fully verified candidate attempts without relaxing constraints | P0 | 23/29/30 |
| FR-10 | Present version, itemized amounts, pack count, unused remainder, subtotal, sources, warnings and three separate statuses | P0 | 01/21/22 |
| FR-11 | Explanation/hypothetical is read-only; applied edit increments effective request version and replaces draft | P0 | 07/20/26/27 |
| FR-12 | Explicit current revision-checked draft acceptance; no external order, reservation or charge | P0 | 08/19/21/28/33 |
| FR-13 | Typed API for create/get/edit/accept/chat through real service/state (no stubbed final response) | P0 | 01/08/24/27 |
| FR-14 | Optional provider-backed structured intent; reject unexpected actions, SKU/price injections and malformed outputs | P0 final stage | 07/27 |
| FR-15 | Expire/delete session context without cross-session promotion | P0 | session privacy tests |
| FR-16 | Consumer UI with accessible draft review and clear human approval | P1 | UX acceptance after design |

The full normative scenario table (AC01–AC33), especially AC33 independent expiry, lives in [canonical UC-01 §8](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md). Detailed field rules live in [DATA_CONTRACT.md](../DATA_CONTRACT.md).

## Critical product invariants

- **Economic verification is not allergy status.** Keep cart_verification_status (VERIFIED / INFEASIBLE / DATA_UNAVAILABLE), meal_allergen_status (NOT_ASSESSED / ASSESSED_NO_KNOWN_CONFLICT / REVIEW_REQUIRED / KNOWN_CONFLICT), user_review_state (DRAFT / ACCEPTED / REJECTED) separately.
- Missing purchased-SKU or recipe-component assessment for a declared allergen blocks cart **acceptance**. Unknown pantry-only evidence may permit separately verified cart acceptance **with warning**, not a safety assertion.
- Compute packs = ceil(to_buy / size_per_pack). Subtotal is sum of complete packs × integer VND price; not prorated consumption. First-slice totals omit tax, shipping, promotions and must say so.
- Use authoritative source-defined **price and stock** expiry separately; never splice incompatible snapshots. A refresh invalidates the previous approval and requires explicit reconfirmation.
- Only explicitly applied material changes modify effective constraints. Explanation, “what if”, or mere chat turn must not mutate a current draft.
- Never auto-accept, auto-purchase, store permanent allergy memory, silently switch store, invent retailer source facts or claim global optimum.

## Experience outcome (P1, not implementation approval)

One chat-centric request/constraints view, versioned dish-and-portions section, ingredient/pack cart section and warning/approval panel. Show price/stock provenance, exact warning subjects and “chưa gồm thuế/phí giao hàng/khuyến mãi”. CTA must read “Chấp nhận giỏ hàng nháp” or equivalent, **not “Đặt hàng”**. Detailed behavior: [UX_SPEC.md](UX_SPEC.md).

## Delivery alignment and success gates

- PR #3 contains canonical business design and contract; #4 contains proposed nine-task plan.
- PR #5 Tasks 1–2; #6 Task 3; #7 Task 4; #8 Task 5 are open stacked branches. Their presence is not merged delivery.
- Finish review/approval gates in order; deliver Task 6 session, Task 7 explicit acceptance, Task 8 HTTP E2E and Task 9 live-intent adapter **without rewriting completed modules**.
- Declare UC-01 implemented only after required deterministic and HTTP/service/persistence scenario tests actually pass and evidence is linked. Live LLM success needs a separate **executed >0** provider test lane.

**Change control:** if this summary conflicts with canonical UC-01 or DATA_CONTRACT, treat it as a review finding; do not silently modify product policy. 
