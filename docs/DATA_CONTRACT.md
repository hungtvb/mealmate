# UC-01 — Grocery Data Contract & Verification

**Status:** PROPOSED — requires UC-01 design sign-off; **pantry Option B and purchased-SKU Option A approved as product decisions**; no implementation authorized.  
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

**Revision rule (material changes only):** `conversation_revision` is the **version of the effective meal request**, not a count of chat turns. Increment it and invalidate prior verification/acceptance only when a user **applies a change** to a relevant constraint (diners, budget, meal type, dislikes, allergy/restriction, confirmed pantry data) or chooses/edits a proposed dish/cart. Update only the named dimension and preserve every unnamed constraint, including declared allergies. **Read-only** explanations, provenance questions, clarifications that do not yet commit a change, or hypothetical comparisons do **not** mutate the request or invalidate a still-current cart. An independently expired/changed authoritative fact can nevertheless require re-verification. `DraftCart.request_revision` pins the material `MealRequest.conversation_revision` used for its proposal.

### Recipe, RecipeIngredient, PlannedDish

`Recipe`: `recipe_id`, `version`, `title`, `base_servings` (>0), `default_serving_role` (`main`/`side`/`shared`), `ingredients[]`, `source_ref`, `data_completeness`. The curated `base_servings` counts **role-specific portions**, not complete meals: for example, a four-portion vegetable side is a side for four diners. Role and yield must come from the reviewed recipe source, not LLM inference.

`RecipeIngredient`: stable `component_id` (unique within a `recipe_id + version`), `ingredient_id`, `quantity`, `unit`, `food_form`; sauces, spice mixtures and other processed ingredients are explicitly represented. References use the **versioned composite** `(recipe_id, recipe_version, component_id)`; a change to recipe contents creates a new version and evidence cannot silently follow it. A `data_completeness` failure excludes the recipe from a verified cart, not necessarily from a clearly labeled exploratory suggestion.

`PlannedDish`: `recipe_id`, `recipe_version`, `target_servings`, `serving_role` (main/side/shared), `portion_rationale`. **Approved automatic portion Option A:** for an initial shared meal proposal, select a supported role-specific portion plan using curated recipe `base_servings`/yield, meal composition and diner count; do **not** require the user to specify each serving amount. Four side portions are **not** four complete meals. The LLM may choose among sourced role/portion options, but must not fabricate ingredient quantities or serving yields. Record recipe version, chosen role and portion rationale; reject/clarify when recipe role, yield or portion guidance is insufficient. The user may change `target_servings` for a dish; update its ingredient need by `recipe_ingredient.quantity × target_servings / base_servings`, then re-aggregate, re-deduct pantry, re-evaluate sellable packs, total price/stock and food evidence. Invalidate any old verification/acceptance on edit. Never round the intermediate ingredient quantities prematurely.

### Ingredient

`ingredient_id`, `canonical_name`, `aliases[]`, `measurement_dimension`, `food_form`, `approved_conversion_refs[]`.

Aggregate ingredient requirements only when identity, dimension and food form match, or when an explicit conversion permits it. No guessed yield, density, recipe ingredient substitutes or nutrient values.

### ProductSKU

`sku`, `ingredient_id`, `food_form`, `pack_quantity`, `pack_unit`, `price_vnd_per_pack`, `stock_packs`, `catalog_snapshot_id`, `food_evidence_ref`.

One SKU represents **one ingredient demand** in UC-01; mixed food bundles and one SKU allocated across different canonical ingredient demands are unsupported. Matching recipe and pantry requirements to products requires identical canonical `ingredient_id`, compatible `food_form` and convertible quantity units with explicit factors. Never join by display name or label text. The mapping is reviewed; `stock_packs` is an integer count of **sellable packs**, not ingredient mass. An ingredient already fully covered by confirmed pantry stock does not require a SKU in the cart.

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

**Approved product boundary — Option B (2026-11-04):** Cart purchase-data verification is **independent** from the meal's allergy assessment. If the user's pantry item lacks allergen evidence, display the specific warning and still allow the user to **accept a cart that independently passes pack, budget, price, stock and snapshot checks**, after showing the limitation. The meal retains `meal_allergen_status=REVIEW_REQUIRED`; neither accepting the cart nor acknowledging the warning changes this status or asserts allergy suitability. Known incompatible recipe components or selected products are a different case: **reject that meal candidate** and do not present it as an allergen-compliant suggestion. Food preparation, utensils and home cross-contact remain outside MealMate's verification boundary.

**Approved purchased-SKU boundary — Option A (2026-11-04):** If **any selected SKU** lacks adequate ingredient-presence or cross-contact assessment for a declared allergen, it is **ineligible for an acceptable cart**. Keep `meal_allergen_status=REVIEW_REQUIRED` and identify the exact SKU/allergen and missing evidence; do not infer absence. Search for a **different, independently evidenced** SKU mapped to the same canonical ingredient/form/unit, then recompute its package count, stock, price, budget and meal-allergen assessment. If no eligible substitute is available, request reliable label/supplier evidence or a recipe change and leave the cart as `DRAFT` (or present a clearly marked non-acceptable provisional quote). Customer acknowledgment cannot override a purchased-SKU evidence failure. A verified cart price/stock subtotal is **not** equivalent to SKU allergy clearance; no medical guarantee is asserted even if assessments pass.

Allergy details should remain in the active conversation by default, without long-term persistence unless separately consented and governed.

**Background (non-Vietnamese regulatory references, not compliance certification):** [WHO/FAO risk-assessment overview](https://www.who.int/publications/i/item/B09028) and [UK FSA precautionary labelling guidance](https://www.gov.uk/government/publications/precautionary-allergen-labelling/precautionary-allergen-labelling). Both discuss unintended allergen presence and the role of evidence-based cross-contact risk assessment.

### CartLine and DraftCart

`CartLine`: `ingredient_id`, `required_qty`, `confirmed_pantry_qty`, `buy_qty`, `sku`, `packs`, `price_per_pack_vnd`, `line_total_vnd`, `source_refs[]`.

`buy_qty = max(0, required_qty - confirmed_pantry_qty)` after compatible unit conversion. If `buy_qty = 0`, no SKU line should be purchased (but recipe/allergen evidence still applies to pantry food). Otherwise `packs = ceil(buy_qty / pack_quantity)`; require `packs <= stock_packs`.

`DraftCart`: `cart_id`, `revision`, `request_revision`, `planned_dishes[]`, `lines[]`, `subtotal_vnd`, `budget_vnd`, `snapshot_id`, `verified_at`, `verification_basis`, `cart_verification_status`, `meal_allergen_status`, `problems[]`, `user_review_state`, `accepted_at?`. `verification_basis` pins `{ request_revision, cart_revision, snapshot_id, catalog_source_revision, selected_recipe_versions[], selected_food_evidence_revisions[] }`: each evidence reference is the typed `subject_ref + evidence_id + evidence_revision` for every selected recipe component, purchased SKU and relied-on pantry item. This is the **basis of the presented cart and warnings**, not proof that external sources can be locked. A later source revision or recipe component change cannot silently reuse the old assessment.

**Budget policy (approved, Option A):** `subtotal_vnd = Σ(line.packs × line.price_per_pack_vnd)`. Calculate the cost of complete sellable packages, including unused ingredient amounts; never prorate by the ingredient quantity consumed. A cart can be `VERIFIED` only when `subtotal_vnd <= budget_vnd`. Taxes, shipping and discounts are excluded from this proposed subtotal and must be disclosed.

**Three independent statuses (approved pantry B + purchased-SKU A):**
- `cart_verification_status`: `VERIFIED`, `INFEASIBLE`, `DATA_UNAVAILABLE`. This covers **purchasable SKU packs, unit compatibility, quantities, price, stock, budget and snapshot validity only**; it is not a meal-suitability claim. `VERIFIED` requires no unresolved cart-data errors.
- `meal_allergen_status`: `NOT_ASSESSED` (no allergies declared), `ASSESSED_NO_KNOWN_CONFLICT` (specified allergen checks passed with scoped evidence; **not medically safe**), `REVIEW_REQUIRED` (some declared allergen evidence is unknown, including pantry), `KNOWN_CONFLICT` (a known allergen conflict exists). A meal with `KNOWN_CONFLICT` is not an eligible recommendation for a shopper with that declared allergy; offer a different recipe/SKU rather than treat acknowledgment as clearance.
- `user_review_state`: `DRAFT`, `ACCEPTED`, `REJECTED`. For the **approved pantry-only Option B**, a user may explicitly `ACCEPT` a currently cart-VERIFIED draft despite `meal_allergen_status=REVIEW_REQUIRED` **when its unresolved allergen evidence is restricted to pantry items**, the specific limitations are visibly disclosed, and the meal has **no KNOWN_CONFLICT**. Unknown allergen evidence for **any purchased SKU** is **acceptance-blocking by approved Option A**; the user must receive a verified eligible substitute, reliable scoped evidence, or a revised menu before cart acceptance. Acceptance approves the *shopping cart contents*, **not the food's allergy suitability, order placement or payment**. The user must not be told that accepting clears any warning.

**Acceptance-time verification (TOCTOU, with versioned food evidence):** At the customer's explicit ACCEPT action (`as_of_accept`), first obtain a consistent authoritative read of the **current** recipe versions/component lists, selected SKU and pantry FoodEvidence `subject_ref + evidence_revision`, and catalog price/stock snapshot facts. Compare **every** value against the stored `verification_basis` — including `request_revision`, `DraftCart.revision`, `snapshot_id`, `catalog_source_revision`, selected recipe versions and selected food-evidence revisions — along with `observed_at <= as_of_accept < price_valid_until` and `stock_valid_until`. Re-evaluate quantities, selected packs, price, stock, budget and **all** declared-allergen assessments. Apply a conditional `DRAFT → ACCEPTED` update **atomically with the stored draft/request version check**; an external provider is *not* assumed to participate in the database transaction. If a required source cannot supply consistent readable version identifiers, **do not accept**; refresh, reverify, present the changed menu/cart/warnings and request explicit confirmation again.

The acceptance gate requires `cart_verification_status=VERIFIED`, no `meal_allergen_status=KNOWN_CONFLICT`, and unresolved allergen evidence **limited to pantry items** (approved pantry Option B); any unknown purchased-SKU assessment **blocks acceptance** (approved SKU Option A). Newly known allergen conflicts reject that meal candidate. Missing/changed/expired evidence of **either recipe components or product labels** must invalidate the previously verified basis, even if a price/stock snapshot remains current. Changed pantry evidence must refresh the warning and be redisplayed before confirmation, not silently treated as clearance. This is **not** a stock reservation, does not lock external price/stock after acceptance and cannot create an order/payment.

On changed cart/request data invalidate old cart verification and user acceptance; on changed food evidence recalculate `meal_allergen_status` and warnings. Never silently discard previously declared allergens, and never infer that missing pantry evidence is safe.

## 4. Verifier output and partial search

Store **all** known issues in `problems[]`, not merely one string:

`{ code, subject_type, subject_ref, evidence_ref?, severity, next_action }`

Examples: `SKU_OUT_OF_STOCK`, `PRICE_EXPIRED`, `UNKNOWN_CROSS_CONTACT`, `ALLERGEN_ASSESSMENT_MISSING`, `KNOWN_ALLERGEN_PRESENT`, `PANTRY_QUANTITY_UNKNOWN`, `UNIT_CONVERSION_MISSING`, `BUDGET_EXCEEDED`, `DUPLICATE_SKU_ALLOCATION`, `ACCEPTANCE_REVISION_CONFLICT`, `ACCEPTANCE_EVIDENCE_REVISION_CONFLICT`. Allergen-related problems also identify the relevant `allergen_id`.

**Approved proactive fallback — Option A:** If an evaluated candidate is over the hard pack-price budget (`BUDGET_EXCEEDED`) or cannot supply required sellable packages (`SKU_OUT_OF_STOCK`), MealMate **automatically evaluates** alternative **sourced** SKU selections or curated recipes before asking the shopper to decide, bounded to `max_evaluated_candidates=3` total including the initial candidate. Each distinct complete `recipe/version + per-dish target servings + selected SKU/pack combination` counts as a candidate once; a different SKU for the same ingredient counts as a **new candidate**. A proactive search is **not a material user-request edit**: keep `MealRequest.conversation_revision` and all constraints unchanged across C01→C02→C03; each newly presented cart proposal receives its **own** draft/cart revision and verification basis. Never overwrite a previously `ACCEPTED` cart. Only evaluate candidates preserving diners, budget, dislikes, allergies, explicit restrictions and confirmed pantry constraints. For any alternative, recompute aggregate ingredient needs, pantry deduction, pack counts, stock, full-pack subtotal, food evidence and snapshot validity from authoritative data; never trust a prior candidate's verified subtotal or label. Never silently change an `ACCEPTED` cart or auto-accept a replacement. Present a currently verified acceptable alternative as a **new DRAFT** with reasons and its exact price; require explicit shopper approval. If no candidate qualifies within the bound, return the appropriate bounded outcome with observed reasons and offer **user-controlled** edits (including raising the budget); do not raise constraints automatically. Candidate search and verification do not create an order or reserve stock.

Keep **cart problems** and **meal allergen problems** explicitly typed in `problems[]`; one does not overwrite the other. No unresolved cart errors may coexist with `cart_verification_status=VERIFIED`. An unknown pantry allergen affects `meal_allergen_status=REVIEW_REQUIRED` **without silently changing cart verification**. Known allergy conflicts exclude that meal candidate; candidate-level economic failure remains `INFEASIBLE` for the cart proposal. When **all** of at most `max_evaluated_candidates=3` (including the initial proposal, at most two alternatives) fail **cart-data verification**, report `NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET` (AC23), after proactive budget/stock fallback attempts where eligible alternatives exist. If cart facts are verified but **every** evaluated candidate is ineligible for acceptance due to **non-pantry allergy evidence** (selected-SKU assessments under Option A or insufficient recipe-component evidence), report `NO_ACCEPTABLE_CART_IN_EVALUATED_SET` and identify the evidence gaps; do **not** falsely claim economic verification failed. Neither outcome proves no other menu exists. These are conversation outcomes, not cart statuses.

## 5. Traceable worked examples

The canonical UC-01 spec contains the small four-dish example, pack prices and failure cases; **do not maintain a second set of numbers here**.

The corresponding expected invariants are:

- Tomato amounts from two dishes aggregate **before** pantry subtraction and package rounding.
- Pantry rice can fulfill a requirement without purchasing rice, but does not exempt that component from declared-allergen checks. A priced, purchasable cart can be `cart_verification_status=VERIFIED` and explicitly `ACCEPTED` while the meal remains `meal_allergen_status=REVIEW_REQUIRED` because pantry evidence is unknown; there is no allergy-safety assertion.
- A single bundle/SKU cannot be double-counted across different canonical ingredient demands.
- If a price changes or a new snapshot expires, the old cart loses `VERIFIED`; never keep a stale subtotal.
- If pantry quantity is unknown, seek clarification or plan a conservative *purchased* quantity without asserting pantry coverage; do not represent unknown as zero confirmed stock.
- Budget feasibility and allergen assessment are separate checks. Unknown pantry allergy evidence must not falsely clear meal suitability, but does not automatically fail price/stock-verified purchased packs.

## 6. Data acceptance gate before seed generation

The smallest accepted fixture must include:

- Curated full recipe ingredients (including seasoning where applicable), **role-specific serving guidance**, explicit proposed `PlannedDish` targets, source-backed rationale and ingredient units/forms. Include a user edit changing one side dish's target servings without resetting other constraints (AC26).
- One-store SKU/pack/price/stock snapshot with consistent UTC validity windows and source revisions.
- Per-allergen, traceable ingredient-presence and cross-contact evidence for recipe, SKU and pantry contexts; include a **two-allergen** case where `SHRIMP` is assessed absent but `PEANUT` is unknown on the same SKU.
- Negative **purchased-SKU Option A** case where a selected SKU's declared-allergen evidence is UNKNOWN: even with correct price/stock, acceptance is blocked. A separate positive replacement case must demonstrate a different evidenced SKU with fresh pack, stock and budget re-verification.
- At least one example with two dishes sharing an ingredient, one unknown pantry quantity, one cross-form conversion failure, one expired snapshot and one changed price.
- Reproducible `as_of` plus **acceptance-time** expiry/revision checks for source snapshot, selected recipe versions and every selected FoodEvidence record; read-only chat must preserve a current draft while actual constraint edits invalidate it (AC27–AC28). Proactive budget/stock fallback must use newly sourced, compatible alternative SKU/cart facts, preserve all unchanged request constraints, and remain a DRAFT pending explicit approval (AC29–AC30). Include duplicate pantry-item and changed-recipe-version cases and asserted cart line amounts/statuses; verify against the UC-01 acceptance matrix before implementing runtime.

## 7. Questions reserved for product review

1. **Approved portion Option A:** automatically propose role-aware dish servings from curated recipe yields and allow user edits. Recipe-first versus SKU-first product strategy still awaits overall sign-off; never permit invented quantities.
2. **Approved budget Option A:** actual purchasable-pack subtotal. Single-store/single-shared-meal scope remains proposed for final product sign-off.
3. **Approved pantry Option B and purchased-SKU Option A:** keep price/stock cart verification separate from meal-allergen checks. Pantry-only uncertainty permits cart acceptance with explicit warning; any purchased-SKU allergen evidence gap blocks acceptance and triggers substitution/evidence requests. Neither outcome claims the meal is medically safe.
4. Accept **per-snapshot expiry timestamps** rather than one global TTL for all price/stock data?

Decisions explicitly marked **approved** above are recorded product choices; remaining design questions are still proposed and require overall review.
