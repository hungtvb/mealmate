# UC-01 — Meal Request to Verified Grocery Cart (Design)

**Status:** PROPOSED / AWAITING PRODUCT SIGN-OFF  
**Owner:** MealMate product & engineering  
**Tracking:** [Issue #2](https://github.com/hungtvb/mealmate/issues/2)  
**Date:** 2026-11-04

This is the **canonical design** for UC-01. [docs/UC-01.md](../../UC-01.md) is the short entry point. No app code or external ShopMate source may be imported based solely on this draft.

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

**Proposed rule:** The LLM can interpret intent, pick among valid recipes, explain or suggest alternatives. It cannot create a recipe quantity or product fact without structured source evidence.

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
  P -- No --> M[No feasible plan / needs review]
  K --> N{User edits?}
  N -- Yes --> B
  N -- No --> O[User reviews/accepts draft only]
```

**Bound the retries**: attempt up to three alternate menus per request (proposed limit; tune later). No silent loop or mutation of inventory. Data issues produce an explicit conflict, not optimistic assumptions.

## 5. Data contracts (logical, not DB tables yet)

Required fields and semantics; exact Python/JSON schemas are deferred to the implementation plan.

| Contract | Required fields | Invariants |
| --- | --- | --- |
| `MealRequest` | `request_id`, `diners` (positive int), `budget_vnd` (nonnegative integer), `meal_type`, `dislikes[]`, `allergens[]`, `dietary_restrictions[]`, `pantry[]`, `conversation_revision` | Constraints on shared dishes are cumulative; allergies never demoted to soft preferences |
| `Recipe` | `recipe_id`, `version`, `title`, `base_servings`, `ingredients[]`, `tags[]`, `source_ref` | Each ingredient has `ingredient_id`, raw quantity, canonical unit and food form; absent ingredient/quantity means cannot use for verified cart |
| `Ingredient` | `ingredient_id`, `canonical_name`, `aliases[]`, `measurement_dimension` | Conversions allowed only within compatible dimensions or via explicit preparation/yield factor |
| `ProductSKU` | `sku`, `mapped_ingredient_ids[]`, `pack_amount`, `pack_uom`, `sellable_unit`, `price_vnd`, `stock_packs`, `stock_checked_at`, `price_checked_at` | Price refers to **one sellable package**, stock counts packages; negative and unknown values rejected |
| `IngredientEvidence` | `sku`, `ingredient_statement`, `declared_allergens[]`, `cross_contact_status`, `label_source_ref`, `label_checked_at` | Cross-contact status explicitly KNOWN_PRESENT / ASSESSED_ABSENT / UNKNOWN; absent warning text is not evidence of safety |
| `CartLine` | `ingredient_id`, `required_qty`, `pantry_qty`, `buy_qty`, `sku`, `packs`, `price_per_pack_vnd`, `line_total_vnd`, `evidence_refs[]` | `buy_qty = max(0, required_qty - confirmed_pantry_qty)`; pack quantity covers buy_qty |
| `DraftCart` | `cart_id`, `revision`, `lines[]`, `subtotal_vnd`, `budget_vnd`, `verification_status`, `problems[]`, `source_snapshot_id` | Not an order; versioned and revalidated after any modification or price/stock change |

**Data provenance:** recipe `source_ref`, ingredient mapping, product label record and catalog snapshot must be inspectable, not merely a natural-language citation added by an LLM.

**Food-form caveat:** 500 g cooked chicken is not interchangeable with 500 g raw chicken. A transformation requires an explicit yield/conversion factor. Otherwise mark unresolved rather than guessing.

**Health/privacy:** Do not collect disease diagnoses unless necessary; accept user-specified restrictions such as “ít muối” with an explicit meaning/threshold if quantitative filtering is expected. Do not persist personal health or allergy details beyond the active session by default.

## 6. Business rules and deterministic verification

1. Validate `diners > 0`, budget format/currency, and required serving information before computing.
2. Scale each recipe amount by `diners / base_servings` using decimal/rational arithmetic; do not round early. Account for recipe-specific serving assumptions (shared dishes can be smaller portions; data must specify total expected yields).
3. Aggregate only compatible `ingredient_id + measurement_dimension + food_form`; do not combine units or preparation forms by name alone.
4. Subtract pantry quantities **only if confirmed**. “Có gạo” without amount remains unresolved; it cannot silently zero out rice requirements.
5. For a single-SKU candidate: `packs = ceil(buy_qty / pack_amount)` after compatible unit conversion. Example **test fixture**: 600 g needed, 500 g packs at 75,000 VND, 2 packs required → 150,000 VND. With 200 g confirmed on hand, 1 pack → 75,000 VND.
6. For MVP, choose **one verified SKU per ingredient** from a bounded set; select the lowest **total purchasable package cost** that covers the required quantity and meets stock/ingredient constraints. This is not a guarantee of global optimality across multi-SKU combinations.
7. Price is computed only by trusted `sum(packs × price_vnd)`; insufficient stock, missing prices or incompatible units are hard blockers. Stock/price freshness is validated against a **configurable, documented policy**; threshold pending data review.
8. Budget is a hard cap on proposed cart subtotal. If no feasible combination, say why and offer a verified cheaper menu or a request to revise budget. Do not hide the cost of unused remainder of packs.
9. Allergens: exclude recipes known to contain the allergen; inspect SKU ingredient statement and cross-contact evidence. If information is missing/uncertain, return `REVIEW_REQUIRED` and **never label the item/cart allergen-safe**. A draft with unresolved allergy evidence cannot be auto-confirmed as verified.
10. Clinical context: no disease-based diet inference. Only explicit restrictions are enforceable; if insufficiently specified, ask or warn, not provide medical guarantees.
11. No missing-data fallbacks that reinterpret unknown stock as zero, unknown price as free, or unknown allergen status as safe.
12. After any user change, recalculate all affected quantities, prices and checks. A draft cart reflects its data snapshot and must be rechecked before any future checkout integration.

### Verification statuses
- `VERIFIED`: quantity, pack, budget, stock, price and required evidence checks satisfied for the specified snapshot. **Not a guarantee of medical allergen safety**.
- `REVIEW_REQUIRED`: human inspection/clarification needed; not safe to claim all constraints verified.
- `INFEASIBLE`: one or more hard constraints cannot be satisfied with available data/candidates.
- `DATA_UNAVAILABLE`: authoritative data missing, stale or inconsistent.

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
| AC01 | Dinner for 4, 300k VND | Menu & cart cover servings and verified pack subtotal <= budget **or** explicit infeasible outcome |
| AC02 | Avoid spicy food | No verified menu with known spicy dish; ambiguous seasoning clarified |
| AC03 | One diner allergic to shrimp | Reject known shrimp-containing recipes/SKUs; unknown label/cross-contact → REVIEW_REQUIRED, no safety assurance |
| AC04 | Have 200 g rice and unspecified oil | Deduct only 200 g rice; clarify or retain oil quantity, never assume all oil on hand |
| AC05 | Missing price / stale stock | DATA_UNAVAILABLE with no invented subtotal or availability; fresh alternatives reverified |
| AC06 | Need 600 g, 500 g pack at 75k | Two packages, 150k before pantry; insufficient stock blocks that SKU |
| AC07 | “Đổi món thịt sang cá, giữ ngân sách” | Replace dish, recompute from sources, retain all other active constraints |
| AC08 | User accepts draft | Only update draft status; cannot create order or payment |
| AC09 | Conflicting/no feasible request | Explicit INFEASIBLE reasons and permitted next actions, not fabricated compliance |
| AC10 | Price/stock changes after draft | Snapshot mismatch → revalidation before any future confirmed order |
| AC11 | Recipe uses cooked vs raw form without yield data | Cannot assert quantity match; ask/mark data unavailable |
| AC12 | Same ingredient in two recipes | Aggregate once and apply package rounding **after** aggregation |

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

**Sign-off gate:** This spec and its assumptions require user review. Once approved, create an implementation plan via Superpowers; no code, app scaffold or ShopMate import in this PR.
