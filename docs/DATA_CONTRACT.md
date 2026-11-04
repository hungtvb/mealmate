# UC-01 — Grocery Data Contract & Verification

**Status:** PROPOSED — requires UC-01 design sign-off; no implementation authorized.  
**Source design:** [UC-01](superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) · [Issue #2](https://github.com/hungtvb/mealmate/issues/2)

## 1. Purpose and boundary

Define **logical data contracts** and checkable invariants for one home-cooked meal → one-store **draft grocery cart**. This document owns field semantics and verification; the UC-01 design owns the business journey and acceptance scenarios. No DB schema, framework, API, data fixture or live supplier integration is approved here.

Two candidate designs were considered:

- **A. Free-form LLM output as the source of recipes and prices:** easy to prototype, impossible to verify reliably; rejected.
- **B. Curated recipe/SKU facts with typed evidence and deterministic cart verification:** repeatable and auditable; **proposed**.
- A future bundle/optimization model is deferred; UC-01 deliberately handles one SKU per canonical ingredient.

## 2. Shared conventions

| Concept | Proposed contract |
| --- | --- |
| Currency | Only `VND`; monetary amounts are **integer VND** (no floating-point prices). |
| Units | Canonical `g`, `ml`, `pcs`; kg↔g and L↔ml allowed. Pieces↔mass, cooked↔raw, drained↔net weight require explicit sourced factors. |
| Quantity | Positive decimal/rational for recipes/needs; zero allowed only for leftover/buy quantities; invalid or negative values rejected. Round only at sellable pack calculation. |
| Entity identity | Stable `recipe_id`, `ingredient_id`, `sku`; do not match by display name alone. |
| Provenance | Source ID + source revision/observed time attached to every authoritative recipe, label, price and stock fact. No fabricated metadata. |
| Time | UTC RFC3339 timestamps; validation occurs at an explicit `as_of` instant for deterministic replay. |
| Missing data | `UNKNOWN` is not zero, available, safe or verified. Preserve distinction between absent field and confirmed empty list. |

## 3. Logical records

The fields below describe required meaning, not a commitment to separate SQL tables.

### MealRequest

`request_id`, `conversation_revision`, `diners` (>0), `meal_type`, `budget_vnd` (>0 for budget-constrained flow), `dislikes[]`, `allergens[]`, `dietary_restrictions[]`, `pantry[]`.

`pantry[]` entries: stable `pantry_item_id` (unique within `request_id`, preserved across revisions for the same physical item), `ingredient_id`, `quantity`, `unit`, `food_form`, `quantity_confirmed` and optional `food_evidence_ref`. Two packages of the same food receive **different** `pantry_item_id` values. Quantity confirmation **does not** establish allergen safety. Unknown pantry quantity is not automatically deducted. Missing diners/budget triggers clarification rather than invention. Specific illness-related limits must be provided as restrictions; do not infer from a diagnosis.

**Revision rule:** Each new user turn updates only named constraints, retains all others (including declared allergies), increments `conversation_revision` and invalidates any old cart verification result.

### Recipe, RecipeIngredient, PlannedDish

`Recipe`: `recipe_id`, `version`, `title`, `base_servings` (>0), `ingredients[]`, `source_ref`, `data_completeness`.

`RecipeIngredient`: stable `component_id` (unique within a `recipe_id + version`), `ingredient_id`, `quantity`, `unit`, `food_form`; sauces, spice mixtures and other processed ingredients are explicitly represented. References use the **versioned composite** `(recipe_id, recipe_version, component_id)`; a change to recipe contents creates a new version and evidence cannot silently follow it. A `data_completeness` failure excludes the recipe from a verified cart, not necessarily from a clearly labeled exploratory suggestion.

`PlannedDish`: `recipe_id`, `recipe_version`, `target_servings`, `serving_role` (main/side/shared), `portion_rationale`. Ingredient need = `recipe_ingredient.quantity × target_servings / base_servings`. A four-person meal with three dishes **does not** imply three independent four-serving full meals; the chosen targets must be recorded and reviewable.

### Ingredient

`ingredient_id`, `canonical_name`, `aliases[]`, `measurement_dimension`, `food_form`, `approved_conversion_refs[]`.

Aggregate ingredient requirements only when identity, dimension and food form match, or when an explicit conversion permits it. No guessed yield, density, recipe ingredient substitutes or nutrient values.

### ProductSKU

`sku`, `ingredient_id`, `pack_quantity`, `pack_unit`, `price_vnd_per_pack`, `stock_packs`, `catalog_snapshot_id`, `food_evidence_ref`.

One SKU represents **one ingredient demand** in UC-01; mixed food bundles and one SKU allocated across different canonical ingredient demands are unsupported. The mapping is reviewed, not inferred from product naming. `stock_packs` is an integer count of **sellable packs**, not ingredient mass.

### CatalogSnapshot

`snapshot_id`, `store_id`, `observed_at`, `price_valid_until`, `stock_valid_until`, `source_ref`, `source_revision`.

A cart's selected SKU price and stock facts must refer to the **same logical store snapshot** or to separately versioned compatible reads with a documented consistency rule. UC-01 defaults to the single-snapshot approach.

At verification instant `as_of`, require `observed_at <= as_of < price_valid_until` and `observed_at <= as_of < stock_valid_until`. If either validity window is missing/expired, return `DATA_UNAVAILABLE` and request authoritative refresh. **No arbitrary universal TTL is assumed.** Drafts are reverified against a new snapshot before future order submission.

### FoodEvidence (allergen-specific, versioned)

`FoodEvidence`: `evidence_id`, `subject_type` (`recipe_component` / `sku` / `pantry_item`), `subject_ref`, `ingredient_statement` (or explicit unknown), `allergen_assessments[]`, `source_ref`, `evidence_revision`, `assessed_at`.

`subject_ref` is typed and unambiguous:
- Recipe: `(recipe_id, recipe_version, component_id)`; recheck when recipe version changes.
- SKU: `(store_id, sku, catalog_snapshot_id)` plus the label/evidence revision; do not reuse evidence from a different formulation or product.
- Pantry: `(request_id, pantry_item_id)`, with the specific user-supplied food/package and evidence revision. Two pantry packs never share an item reference just because they have the same ingredient ID.

**Allergen taxonomy:** `MealRequest.allergens[]` contains canonical `allergen_id` values, resolved from user aliases with clarification on ambiguity; examples for *synthetic tests only*: `SHRIMP`, `PEANUT`. Substances not confidently mapped remain unresolved; they are never silently dropped. Each `allergen_assessments[]` item has `allergen_id`, `ingredient_presence` (`PRESENT` / `ABSENT` / `UNKNOWN`), `cross_contact_status` (`KNOWN_PRESENT` / `ASSESSED_ABSENT` / `UNKNOWN`), `assessment_scope`, `source_ref`, `assessed_at`. Do not combine these into one unscoped scalar.

For **each declared allergen, for each relevant subject**, independently evaluate ingredient presence and cross-contact:
- `ingredient_presence=PRESENT` or `cross_contact_status=KNOWN_PRESENT` → reject the candidate as `INFEASIBLE` for that ingredient.
- `ingredient_presence=UNKNOWN`, `cross_contact_status=UNKNOWN`, or **missing that allergen's assessment entirely** → `REVIEW_REQUIRED`; one assessed allergen never clears another.
- Both `ingredient_presence=ABSENT` and `cross_contact_status=ASSESSED_ABSENT`, from appropriately scoped, traceable evidence → clears the **documented data checks for that allergen and subject only**, not medical risk. An empty label, absence of a `may contain` warning or a user's acknowledgment is not affirmative evidence.
- With **no declared allergens**, allergen-specific assessments are not a precondition to verifying *non-allergen* cart constraints; the result must say **"no allergens were assessed"**, not "allergen-safe".

Check complete recipe ingredients (including sauces and seasonings), selected SKUs and pantry foods involved in the chosen meal against the union of allergies declared for all diners sharing the meal. Home kitchen handling and utensil cross-contact are **outside** this retailer-data check.

**Pantry usability boundary (proposed):** The system can show a **priced, stock-checked provisional shopping list** separately from the status of the **whole meal plan**. If a relied-upon pantry item's allergen evidence is unknown, the whole meal/draft cannot become `VERIFIED` or `ACCEPTED`, but the UI must identify the one unresolved pantry item rather than hide other valid cart facts. Resolution requires reliable product/pack evidence for that allergen, replacing the pantry item with a separately assessed SKU, or removing/substituting the recipe component. A user's "I understand" is never a safety override. The app cannot certify home preparation as safe.

Allergy details should remain in the active conversation by default, without long-term persistence unless separately consented and governed.

**Background (non-Vietnamese regulatory references, not compliance certification):** [WHO/FAO risk-assessment overview](https://www.who.int/publications/i/item/B09028) and [UK FSA precautionary labelling guidance](https://www.gov.uk/government/publications/precautionary-allergen-labelling/precautionary-allergen-labelling). Both discuss unintended allergen presence and the role of evidence-based cross-contact risk assessment.

### CartLine and DraftCart

`CartLine`: `ingredient_id`, `required_qty`, `confirmed_pantry_qty`, `buy_qty`, `sku`, `packs`, `price_per_pack_vnd`, `line_total_vnd`, `source_refs[]`.

`buy_qty = max(0, required_qty - confirmed_pantry_qty)` after compatible unit conversion. If `buy_qty = 0`, no SKU line should be purchased (but recipe/allergen evidence still applies to pantry food). Otherwise `packs = ceil(buy_qty / pack_quantity)`; require `packs <= stock_packs`.

`DraftCart`: `cart_id`, `revision`, `request_revision`, `planned_dishes[]`, `lines[]`, `subtotal_vnd`, `budget_vnd`, `snapshot_id`, `verified_at`, `verification_status`, `problems[]`, `user_review_state`, `accepted_at?`. Verification is scoped to cart revision, request revision, recipe/evidence versions and catalog snapshot.

`subtotal_vnd = Σ(line.packs × line.price_per_pack_vnd)`; only charge actual **purchasable packages**, including unused leftovers. Require `subtotal_vnd <= budget_vnd` for `VERIFIED`.

**Two independent states:**
- `verification_status`: `VERIFIED`, `REVIEW_REQUIRED`, `INFEASIBLE`, `DATA_UNAVAILABLE` (describes checks for this evaluated candidate/snapshot, **not proof about all possible menus**).
- `user_review_state`: `DRAFT`, `ACCEPTED`, `REJECTED`. UC-01 permits `ACCEPTED` only for a currently `VERIFIED` draft and explicit user action. `REVIEW_REQUIRED` is view/edit/clarify only: acknowledgment is **not** a safety clearance. `ACCEPTED` is **not an order**.

**Acceptance-time verification (TOCTOU):** At the instant a customer accepts (`as_of_accept`), perform a **single atomic conditional update** (transaction or optimistic compare-and-swap) that checks the current `request_revision`, `DraftCart.revision`, previously verified recipe/evidence revisions, unchanged snapshot/source revision and `observed_at <= as_of_accept < price_valid_until` and `stock_valid_until` for every selected SKU. Re-evaluate required quantity/price/stock and unresolved food-evidence blockers. Only then transition `DRAFT → ACCEPTED`. Any stale/mismatched fact causes **no acceptance**, invalidates the prior result, refreshes/recalculates and asks for renewed confirmation; never silently accept a changed cart. This is **not a stock reservation** and does not guarantee availability after acceptance or authorize an order.

On stale snapshot or any request/cart edit, invalidate old `verification_status`, clear any old acceptance, recalculate and re-check. A user's acknowledgment of uncertainty cannot bypass the acceptance gate.

## 4. Verifier output and partial search

Store **all** known issues in `problems[]`, not merely one string:

`{ code, subject_type, subject_ref, evidence_ref?, severity, next_action }`

Examples: `SKU_OUT_OF_STOCK`, `PRICE_EXPIRED`, `UNKNOWN_CROSS_CONTACT`, `ALLERGEN_ASSESSMENT_MISSING`, `KNOWN_ALLERGEN_PRESENT`, `PANTRY_QUANTITY_UNKNOWN`, `UNIT_CONVERSION_MISSING`, `BUDGET_EXCEEDED`, `DUPLICATE_SKU_ALLOCATION`, `ACCEPTANCE_REVISION_CONFLICT`. Allergen-related problems also identify the relevant `allergen_id`.

The primary `verification_status` is a summary; no unresolved hard errors may coexist with `VERIFIED`. For multiple blockers, report all and avoid a misleading single cause. A rejected **candidate** is `INFEASIBLE` for its own constraints. After trying at most three candidate menus, the conversation outcome is **NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET**, not a claim that no possible menu exists. This conversation outcome is distinct from the cart's verification status.

## 5. Traceable worked examples

The canonical UC-01 spec contains the small four-dish example, pack prices and failure cases; **do not maintain a second set of numbers here**.

The corresponding expected invariants are:

- Tomato amounts from two dishes aggregate **before** pantry subtraction and package rounding.
- Pantry rice can fulfill a requirement without purchasing rice, but does not exempt that recipe component from declared-allergen checks. The paid basket may be priced correctly while the overall meal remains `REVIEW_REQUIRED` due to a specific pantry item's unknown evidence.
- A single bundle/SKU cannot be double-counted across different canonical ingredient demands.
- If a price changes or a new snapshot expires, the old cart loses `VERIFIED`; never keep a stale subtotal.
- If pantry quantity is unknown, seek clarification or plan a conservative *purchased* quantity without asserting pantry coverage; do not represent unknown as zero confirmed stock.
- Budget feasibility and ingredient safety are separate checks. A cheap cart with unresolved allergens is not `VERIFIED`.

## 6. Data acceptance gate before seed generation

The smallest accepted fixture must include:

- Curated full recipe ingredients (including seasoning where applicable), explicit `PlannedDish` targets and ingredient units/forms.
- One-store SKU/pack/price/stock snapshot with consistent UTC validity windows and source revisions.
- Per-allergen, traceable ingredient-presence and cross-contact evidence for recipe, SKU and pantry contexts; include a **two-allergen** case where `SHRIMP` is assessed absent but `PEANUT` is unknown on the same SKU.
- At least one example with two dishes sharing an ingredient, one unknown pantry quantity, one cross-form conversion failure, one expired snapshot and one changed price.
- Reproducible `as_of` plus **acceptance-time** expiry/revision checks, a duplicate pantry-item case and changed recipe version case, and asserted cart line amounts/statuses; verify against the UC-01 acceptance matrix before implementing runtime.

## 7. Questions reserved for product review

1. Accept **recipe-first with explicit per-dish serving targets** or permit the planner to invent quantities when recipe coverage is missing?
2. Keep **purchasable-pack subtotal** as the hard budget and single-store/single-shared-meal scope?
3. Keep **non-overridable review requirement** for unknown allergen evidence in UC-01, with no claim of medical suitability?
4. Accept **per-snapshot expiry timestamps** rather than one global TTL for all price/stock data?

All four are proposals for review, not decisions already approved.
