# UC-01 — Meal Request to Verified Grocery Cart (Design)

**Status:** PROPOSED / AWAITING PRODUCT SIGN-OFF  
**Owner:** MealMate product & engineering  
**Tracking:** [Issue #2](https://github.com/hungtvb/mealmate/issues/2)  
**Date:** 2026-11-04

This is the **canonical business/workflow design** for UC-01. [docs/UC-01.md](../../UC-01.md) is the short entry point; [docs/DATA_CONTRACT.md](../../DATA_CONTRACT.md) owns detailed field semantics and deterministic verification. No app code or external ShopMate source may be imported based solely on this draft.

## 1. Intent and why

A household shopper describes one **home-cooked meal**, diners, a grocery budget, dislikes, pantry items and relevant dietary restrictions. MealMate should return a plausible menu and a **buyable draft grocery cart** with traced recipe quantities, product pack counts, current price and stock evidence. The customer can revise the proposal before approving a cart. The application must not place an order or charge payment in UC-01.

**Success is not a fluent response; it is a verifiable proposal.** Failure means a confident but inaccurate cart, an unverified allergen claim, missing quantities, fabricated SKU or unintended checkout.

### Assumptions / not yet approved
- One simulated grocery store with an internally consistent catalog, price and inventory snapshot.
- Currency VND. A supplied budget caps the **subtotal of sellable packs in the cart**, before tax, shipping, discounts or vouchers. The UI explicitly labels exclusions.
- The meal is shared by all diners unless user requests otherwise. Shared dishes respect the union of explicit constraints; individual meal customization is deferred.
- Recipes and products are curated fixtures at first. No live retailer integrations, clinical diet planning or checkout.

## 2. Product approach comparison

| Approach | Pros | Risks / limitation | Status |
| --- | --- | --- | --- |
| A. LLM invents menu and ingredient list, then attempts SKU lookup | Highly flexible wording | Unbounded ingredient amounts; poor reproducibility; easier to hallucinate | Not recommended |
| **B. Recipe-first planning with structured recipes, then deterministic SKU/cart verification** | Traceable quantities, clear test oracle, easier constraints | Limited by coverage of recipe dataset | **Recommended; awaiting review** |
| C. SKU-first catalog optimizer generates recipes from available products | Strong stock awareness | Complicated recipe generation/quality; larger optimization surface | Deferred |

**Proposed rule:** The LLM can interpret intent, pick among valid recipes, explain or suggest alternatives. It cannot create a recipe quantity or product fact without structured source evidence. A recipe is eligible only when its complete ingredient list includes sauces, seasoning and processed components where available; incomplete declarations must not be treated as allergen-free.

## 3. Actor, scope and interaction

Primary actor: a household shopper. Optional: a supermarket operator supplies curated recipes and catalog. A staff admin interface is **out of scope**.

Sample request: “Bữa tối 4 người, tối đa 300.000đ; không cay, một người dị ứng tôm; nhà có 200 g gạo.”

Expected result:
- Menu with dish names, serving counts and explicit recipe versions.
- Aggregated ingredient list showing *required*, *already available*, *to buy*.
- SKU/package quantities and verified subtotal with item-level provenance.
- Dietary warnings or **REVIEW_REQUIRED** if suitability cannot be established.
- A draft cart that cannot be submitted/paid without a separate explicit action.

Follow-up such as “đổi món thịt thành cá, giữ nguyên ngân sách” must preserve diners, allergy and dislike constraints and recompute affected quantities and SKU pricing.

## 4. End-to-end flow

```mermaid
flowchart TD
  A[Meal request] --> B[Extract structured constraints]
  B --> C{Critical input missing?}
  C -- Yes --> D[Clarify with user]
  C -- No --> E[Select curated recipe candidates]
  E --> F[Scale servings & aggregate ingredient amounts]
  F --> G[Deduct confirmed pantry quantities]
  G --> H[Resolve compatible SKUs and sellable packs]
  H --> I[Check stock, prices, evidence and restrictions]
  I --> J{All hard constraints satisfied?}
  J -- Yes --> K[Present sourced menu & draft cart]
  J -- No --> L[Explain failure and assess alternatives]
  L --> P{Valid alternatives and retries left?}
  P -- Yes --> E
  P -- No --> M[No verified candidate in evaluated set]
  K --> N{User edits?}
  N -- Yes --> B
  N -- No --> O[User reviews/accepts draft only]
```

**Bound the retries**: attempt up to three alternate menus per request (proposed limit; tune later). No silent loop or mutation of inventory. Data issues produce an explicit conflict, not optimistic assumptions.

## 5. Data contracts (logical, not DB tables yet)

Logical overview below; **[DATA_CONTRACT.md](../../DATA_CONTRACT.md) is authoritative** for field meanings, evidence, snapshot validity, verification and review statuses. Exact Python/JSON schemas remain deferred to the implementation plan.

| Contract | Required fields | Invariants |
| --- | --- | --- |
| `MealRequest` | `request_id`, `diners`, `budget_vnd`, `allergens[]`, `pantry[]`, `conversation_revision`, other constraints | Allergens are canonical IDs per diner, combined for shared dishes. Each pantry item has stable `pantry_item_id`, quantity and independent food evidence. |
| `Recipe` | `recipe_id`, `version`, `title`, `base_servings`, `ingredients[]`, `tags[]`, `source_ref` | Recipe components have version-scoped `component_id`; ingredient/seasoning completeness required. |
| `PlannedDish` | `recipe_id`, `recipe_version`, `target_servings`, `serving_role` (shared dish / main course / side dish) | Scaling uses **explicit target servings per selected dish**, not automatically `diners` for every recipe. Each dish declares its intended contribution to the meal; multi-dish portion policy requires review. |
| `Ingredient` | `ingredient_id`, `canonical_name`, `aliases[]`, `measurement_dimension` | Conversions allowed only within compatible dimensions or via explicit preparation/yield factor |
| `ProductSKU` | `sku`, `ingredient_id`, `pack_quantity`, `pack_unit`, `price_vnd_per_pack`, `stock_packs`, `catalog_snapshot_id`, `food_evidence_ref` | One SKU satisfies one ingredient demand in UC-01; price and stock are values for sellable packs in the referenced store snapshot. |
| `FoodEvidence` | `evidence_id`, typed `subject_ref`, `ingredient_statement`, per-`allergen_id` `allergen_assessments[]`, `source_ref`, `evidence_revision` | Per-allergen ingredient presence and cross-contact require independent evidence; absent/missing assessment stays UNKNOWN, never a medical-safety certification. |
| `CatalogSnapshot` | `snapshot_id`, `store_id`, `observed_at`, `price_valid_until`, `stock_valid_until`, `source_ref` | Facts share one store snapshot and pass `observed_at <= as_of < valid_until`; stale/missing validity becomes `DATA_UNAVAILABLE`. |
| `CartLine` | `ingredient_id`, `required_qty`, `pantry_qty`, `buy_qty`, `sku`, `packs`, `price_per_pack_vnd`, `line_total_vnd`, `evidence_refs[]` | `buy_qty = max(0, required_qty - confirmed_pantry_qty)`; pack quantity covers buy_qty |
| `DraftCart` | `cart_id`, `request_revision`, `lines[]`, `subtotal_vnd`, `budget_vnd`, `verification_status`, `problems[]`, `snapshot_id`, `user_review_state` | Verification and explicit user acceptance are distinct. `ACCEPTED` requires a currently verified draft and is not an order. |

**Data provenance:** recipe `source_ref`, ingredient mapping, product label record and catalog snapshot must be inspectable, not merely a natural-language citation added by an LLM.

**Food-form caveat:** 500 g cooked chicken is not interchangeable with 500 g raw chicken. A transformation requires an explicit yield/conversion factor. Otherwise mark unresolved rather than guessing.

**Health/privacy:** Do not collect disease diagnoses unless necessary; accept user-specified restrictions such as “ít muối” with an explicit meaning/threshold if quantitative filtering is expected. Do not persist personal health or allergy details beyond the active session by default.

## 6. Business rules and deterministic verification

1. Validate `diners > 0`, budget format/currency, and required serving information before computing.
2. Set each `PlannedDish.target_servings` based on its role in the full menu and recipe yield, then scale its ingredients by `target_servings / base_servings` using decimal/rational arithmetic. **Do not assume four diners require four full servings of every dish.** Record the selected per-dish portion plan so a reviewer can check coverage; do not round intermediate quantities early.
3. Aggregate only compatible `ingredient_id + measurement_dimension + food_form`; do not combine units or preparation forms by name alone.
4. Subtract pantry quantities **only if confirmed**. “Có gạo” without amount remains unresolved; it cannot silently zero out rice requirements.
5. For a single-SKU candidate: `packs = ceil(buy_qty / pack_quantity)` after compatible unit conversion. Example **test fixture**: 600 g needed, 500 g packs at 75,000 VND, 2 packs required → 150,000 VND. With 200 g confirmed on hand, 1 pack → 75,000 VND.
6. For MVP, choose **one verified SKU per ingredient** from a bounded set; select the lowest **total purchasable package cost** that covers the required quantity and meets stock/ingredient constraints. **If one SKU maps to multiple different canonical ingredient demands, reject that combination for UC-01 rather than charge or allocate its packs twice.** This is not a guarantee of global optimality across multi-SKU combinations.
7. Price is computed only by trusted `sum(packs × price_vnd_per_pack)`; insufficient stock, missing prices or incompatible units are hard blockers. Stock and price facts must be from one compatible store `CatalogSnapshot`, with explicit `price_valid_until` and `stock_valid_until`. Validate at `as_of` as described in [DATA_CONTRACT.md](../../DATA_CONTRACT.md); no universal freshness TTL is assumed.
8. Budget is a hard cap on proposed cart subtotal. If no feasible combination, say why and offer a verified cheaper menu or a request to revise budget. Do not hide the cost of unused remainder of packs.
9. Allergens: apply the union of declared allergies across all diners sharing the meal; check every recipe ingredient (including sauces/seasonings), each selected SKU's label/cross-contact evidence **and any pantry ingredients relied on for that recipe**. Known incompatible ingredients are a hard rejection. Unknown/uncertain evidence returns `REVIEW_REQUIRED` and **never an allergen-safe claim**. A draft with unresolved allergy evidence cannot become `VERIFIED` or be automatically approved.
10. Clinical context: no disease-based diet inference. Only explicit restrictions are enforceable; if insufficiently specified, ask or warn, not provide medical guarantees.
11. No missing-data fallbacks that reinterpret unknown stock as zero, unknown price as free, or unknown allergen status as safe.
12. After any user change, invalidate prior verification and acceptance, recalculate all affected quantities, prices and checks. A draft cart reflects its data snapshot and must be rechecked before any future checkout integration. UC-01's accepted draft is **never** an order.

### Verification statuses
- `VERIFIED`: quantity, pack, budget, stock, price and required evidence checks satisfied for the specified snapshot. **Not a guarantee of medical allergen safety**.
- `REVIEW_REQUIRED`: further trustworthy ingredient/allergen evidence or clarification required; user acknowledgment alone does not grant verified or accepted status.
- `INFEASIBLE`: one or more hard constraints cannot be satisfied with available data/candidates.
- `DATA_UNAVAILABLE`: authoritative data missing, stale or inconsistent.

### Reporting multiple constraint failures

A cart/result must retain **all** observed blockers as structured `problems[]` (reason code, affected recipe/ingredient/SKU, evidence reference and suggested next action), even when one primary status is shown. The primary status is a summary **not** a substitute for individual reasons:
- Known unsafe/forbidden ingredients and known infeasible hard constraints: reject the candidate as `INFEASIBLE`.
- Missing authoritative facts needed to decide safety, price, stock or conversions: `DATA_UNAVAILABLE` for the affected candidate, except unresolved allergen/cross-contact evidence is explicitly `REVIEW_REQUIRED`.
- A candidate is `VERIFIED` **only if no unresolved blockers remain**; customer review of a warning is not evidence that the product is safe.
- If reasons overlap, show the complete list and require a fresh candidate evaluation rather than infer success from a single status. Do not use a failure of one candidate to claim that *no* possible menu is feasible. Exhausting the bounded search returns `NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET`, a **conversation outcome**, not a verified statement that every menu is infeasible.

## 7. Boundaries (why agentic, why deterministic)

| Responsibility | Proposed executor |
| --- | --- |
| Interpret conversation and preserve explicit constraints | LLM with structured extraction + validation |
| Plan a menu from valid candidates | Bounded planner (LLM may rank/justify, never invent recipe facts) |
| Search recipe knowledge | Structured recipe records; RAG only for unstructured explanations with cited sources |
| Scale recipe, normalize units and deduct pantry | Deterministic recipe/ingredient resolver |
| Read SKU, stock, label and price | Catalog/inventory/price service (possibly MCP adapter; transport is a separate decision) |
| Select sellable packs and budget-check | Deterministic cart builder / verifier |
| Present alternatives, caveats and revise | Orchestrated dialog |
| Review and approve draft cart | Customer explicit action; **not payment** |

Use one orchestration flow initially, not a predeclared army of agents. Superpowers applies to development workflow, not runtime architecture.

## 8. Acceptance scenarios / test oracles

| ID | Input | Required observed behavior |
| --- | --- | --- |
| AC01 | Fixed positive fixture §11: 4 diners, 140,000 VND, snapshot S-FG-001 | Must be `VERIFIED`, 5 purchased lines/6 packages, exactly 116,000 VND; unconditional `INFEASIBLE` **fails**. |
| AC02 | Avoid spicy food | No verified menu with known spicy dish; ambiguous seasoning clarified |
| AC03 | One diner allergic to shrimp | Reject known shrimp-containing recipes/SKUs; unknown label/cross-contact → REVIEW_REQUIRED, no safety assurance |
| AC04 | Have 200 g rice and unspecified oil | Deduct only 200 g rice; clarify or retain oil quantity, never assume all oil on hand |
| AC05 | Missing price / stale stock | DATA_UNAVAILABLE with no invented subtotal or availability; fresh alternatives reverified |
| AC06 | Need 600 g, 500 g pack at 75k | Two packages, 150k before pantry; insufficient stock blocks that SKU |
| AC07 | “Đổi món thịt sang cá, giữ ngân sách” | Replace dish, recompute from sources, retain all other active constraints |
| AC08 | User accepts currently verified draft | Change `user_review_state` to `ACCEPTED` only when `verification_status=VERIFIED`; cannot create order or payment. Unknown allergy evidence blocks acceptance. |
| AC09 | Fixed 140,000 VND fixture with G-TOM500 price raised to 50,000 VND | Candidate `INFEASIBLE` with BUDGET_EXCEEDED (148,000 VND); bounded search exhaustion reports NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET, not global impossibility. |
| AC10 | Price/stock changes after draft | Snapshot mismatch → revalidation before any future confirmed order |
| AC11 | Recipe uses cooked vs raw form without yield data | Cannot assert quantity match; ask/mark data unavailable |
| AC12 | Same ingredient in two recipes | Aggregate once and apply package rounding **after** aggregation |
| AC13 | Four diners share a main and two side dishes | Record each dish's planned serving target; no blind multiplication of full-meal portions across all dishes |
| AC14 | One combo SKU appears eligible for two distinct ingredient demands | Reject unsupported cross-ingredient allocation; never count one package twice or double-charge stock |
| AC15 | Declared allergy; processed seasoning or pantry item has unknown evidence | Preserve `REVIEW_REQUIRED`; never treat recipe or pantry as automatically safe |
| AC16 | Stale stock and incompatible ingredient in the same candidate | Preserve both reason codes with evidence; never return a verified cart |

### Demonstration set (synthetic; not production evidence)
Construct a tiny but coherent fixture: 8-12 recipes, 20-40 SKUs, clear price/stock snapshots, explicit ingredient and allergen evidence. Include positive, impossible-budget, missing-label and stale-stock cases. This is a **proposed test design**, not data already created.

### Evidence gate
Before approving UC-01 implementation, require: defined data contracts, fixed test oracles, a deterministically reproducible cart example, negative allergy cases, and clear criteria for live LLM evaluation. Later classify test evidence as unit, integration, E2E or human review. No fabricated PASS rates.

## 9. ShopMate selective reuse decision

| Module family | Proposed disposition | Proof required before import |
| --- | --- | --- |
| LangGraph workflow/checkpoint patterns | **Study / possibly reuse** | Clear state and resume semantics, bounded retry and tests |
| MCP transport/client utilities | **Evaluate for reuse** | Proper error handling, timeouts, actual protocol calls |
| Recipe/RAG loaders | **Adapt patterns only** | Corpus type, metadata/provenance and retrieval correctness |
| FastAPI/UI/test helpers | **Evaluate separately** | No hardcoded ShopMate retail assumptions; license |
| Refund/HITL, verifier, security fallbacks | **Do not reuse as-is** | Previously observed correctness concerns require new boundaries |
| A2A and Deep Agents | **Defer** | Concrete multi-service/long-horizon need and tested benefit |

The ShopMate archive is a reference, not an approved source dependency. Verify ownership/license and permission before copying any source.

## 10. Risks, anti-goals and review decisions

- **Coverage risk:** curated recipes may not cover diverse cuisines. Prefer honest "no suitable recipe" to hallucinated availability.
- **Price risk:** price/stock are time-sensitive; retain source snapshot and recheck.
- **Allergy risk:** absence of a printed "may contain" warning is not a guarantee. Present uncertainty without claiming suitability.
- **Optimization risk:** single-SKU-per-ingredient heuristic may be more expensive than combined packs; report subtotal as observed, do not call it globally optimal.
- **Interaction risk:** too many clarification questions prevent task completion; ask only when required for safety/correctness and otherwise provide clearly marked options.

### Decisions requested at review
1. Confirm whether the hard budget should cover **actual purchased packages** (recommended) or ingredient consumption cost. Current brief suggests purchased packages.
2. Confirm single-store + one shared meal for all diners as the first slice.
3. Confirm unknown allergy evidence blocks `VERIFIED` but can be shown in a clearly marked `REVIEW_REQUIRED` proposal for manual inspection.
4. Confirm recipe-first approach B and explicitly bounded alternatives.
5. Confirm the default shared-meal portion policy (main + side dishes) and that recipes/condiments/pantry inputs must each be assessed for declared allergies.
6. Confirm one-store `CatalogSnapshot` with explicit fact expiry and separate, non-overridable review for unresolved allergen evidence.

## 11. Golden fixture: positive deterministic test vector (synthetic)

**Fixture ID:** F-UC01-POS. This is fictional test data, not a live catalog, recipe validation or medical assurance. **Expected:** VERIFIED, five purchased SKU lines / six packages, 116,000 VND and no observed constraint blockers. An implementation returning INFEASIBLE always fails AC01.

**Request:** `request_id=REQ-001`, `conversation_revision=1`, four diners, budget 140,000 VND, dinner, `allergens=[]`, `dislikes=[]` and no dietary restrictions. Pantry: `P01` 500 g dry rice, `P02` 100 g tomatoes, `P03` 3000 ml water, with quantities confirmed. These are user statements, not independent health assessments.

**Snapshot:** `store_id=FG-01`, `snapshot_id=S-FG-001`, `source_ref=fixture:grocery/FG-01`, `source_revision=stock-price-v1`, `observed_at=2026-11-04T06:00:00Z`, `price_valid_until=2026-11-04T08:00:00Z`, `stock_valid_until=2026-11-04T06:30:00Z`, `as_of=2026-11-04T06:10:00Z`. All sellable SKU rows below use this snapshot, its source revision and integer VND prices.

**Recipes:** All four are `version=v1`, `base_servings=4`, `target_servings=4`, `data_completeness=COMPLETE`, with `source_ref=fixture:recipe/<recipe_id>@v1`; each `PlannedDish` has `portion_rationale=shared household dish`. Each listed ingredient is complete for this narrowly curated sample: there are **no unlisted seasonings, sauces or cooking inputs**. Water is included explicitly for cooking and supplied by the pantry.

| Recipe | Role | Complete RecipeIngredient lines (stable component IDs) |
| --- | --- | --- |
| R01 Cơm trắng | side | c01 dry rice 400 g; c02 water 600 ml |
| R02 Trứng chiên cà chua | main | c01 eggs 4 pcs; c02 tomatoes 300 g; c03 cooking oil 20 ml |
| R03 Canh đậu phụ cà chua | side | c01 tomatoes 200 g; c02 tofu 400 g; c03 water 800 ml |
| R04 Rau cải luộc | side | c01 greens 400 g; c02 water 800 ml |

**Store catalog:** Every listed SKU has one canonical ingredient mapping and `food_evidence_ref=FE-<sku>`. Stock is measured in sellable packages; snapshots and sources are as defined above.

| SKU | ingredient_id | Pack | Price (VND) | Stock packs |
| --- | --- | --- | ---: | ---: |
| G-RICE1000 | rice | dry rice 1000 g | 26,000 | 5 |
| G-EGG10 | eggs | eggs 10 pcs | 30,000 | 3 |
| G-TOM500 | tomato | tomatoes 500 g | 18,000 | 5 |
| G-OIL500 | oil | cooking oil 500 ml | 28,000 | 3 |
| G-TOFU200 | tofu | tofu 200 g | 12,000 | 5 |
| G-GREEN500 | greens | greens 500 g | 16,000 | 3 |

**Expected deterministic outcome:**

| Ingredient | Total required | Confirmed pantry | To buy | SKU pack count | Charged cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dry rice | 400 g | 500 g | 0 g | 0 | 0 VND |
| Eggs | 4 pcs | 0 | 4 pcs | 1 × G-EGG10 | 30,000 VND |
| Tomatoes | 500 g | 100 g | 400 g | 1 × G-TOM500 | 18,000 VND |
| Cooking oil | 20 mL | 0 | 20 mL | 1 × G-OIL500 | 28,000 VND |
| Tofu | 400 g | 0 | 400 g | 2 × G-TOFU200 | 24,000 VND |
| Greens | 400 g | 0 | 400 g | 1 × G-GREEN500 | 16,000 VND |
| **Total** | | | | **6 packages** | **116,000 VND** |

This example checks a key invariant: tomatoes used in two recipes are **aggregated before** subtracting pantry supply and rounding to packs. The user is charged for purchasable packs, including unused remainder; food already covered by the pantry does not produce a cart line.

**Controlled negative variations:**
- If G-TOFU200 stock falls from 5 to **1**, the two-pack tofu line cannot be marked verified. Try a separately evidenced available alternative; otherwise surface `INFEASIBLE`.
- If G-TOM500 price changes from **18,000** to **50,000 VND**, the unchanged basket totals **148,000 VND** and exceeds the 140,000 VND cap. Replan or return `INFEASIBLE`; never keep the old subtotal.
- If a shopper declares **shrimp allergy** and G-TOFU200 has `cross_contact_status=UNKNOWN` or no trusted ingredient label, return `REVIEW_REQUIRED`; do **not** mark tofu or the whole menu allergen-safe. Request reliable label/vendor confirmation or select another evidenced product.
- If `as_of` is at or beyond the snapshot's `stock_valid_until` or `price_valid_until`, return `DATA_UNAVAILABLE` until authoritative refresh. Snapshot validity is a documented data contract, not an invented global TTL.

### Minimum fixture review gate

Before constructing any larger synthetic dataset, validate this exact worked example and its four negative variations on paper. Additional recipe/SKU coverage should be driven by uncovered acceptance scenarios, not by arbitrary row counts.

**Sign-off gate:** This spec and its assumptions require user review. Once approved, create an implementation plan via Superpowers; no code, app scaffold or ShopMate import in this PR.
