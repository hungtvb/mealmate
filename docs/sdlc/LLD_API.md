# Low-Level Design & API Contract — UC-01

**Version:** 0.1 | **Status:** DRAFT / API proposal, not implemented. The authoritative field semantics remain in [DATA_CONTRACT](../DATA_CONTRACT.md); the existing task-by-task engineering plan in PR #4 owns implementation ordering.

## Existing modules vs future modules

At reviewed PR #8 head (2026-11-05):
- **Present in open PR stack, not main:** models/meal.py, models/catalog.py, models/cart.py, ports.py, fixtures.py, quantities.py, cart_builder.py, allergens.py, search.py and deterministic tests.
- **Not present at that head:** drafts.py, service.py, api.py, intent.py, llm_intent.py, accepted-cart persistence, HTTP E2E, consumer UI.
- Do not replace mature source/quantities/cart/allergen/search modules merely to conform to a new diagram. Prefer extending interfaces with focused contract tests.

## Domain records and invariant ownership

| Record | Stable keys and critical fields | Owner |
| --- | --- | --- |
| MealRequest | request_id; conversation_revision; diners; meal_type; budget_vnd; dislikes; allergens; dietary_restrictions; pantry[] | Request/session service |
| PantryItem | request_id + pantry_item_id; ingredient_id; quantity; unit; food_form; quantity_confirmed; food_evidence_ref | User input + persisted effective request |
| Recipe | recipe_id + version; complete components with component_id; base_servings, serving_role and source_ref | Curated RecipeSource |
| PlannedDish | recipe_id/version, role, target_servings, source rationale | Meal planner, edit service |
| CatalogView | one snapshot_id/store_id, SKU rows, independent price/stock fact validity | CatalogSource |
| ProductSKU | SKU, ingredient_id, form, pack_qty/unit, price_vnd_per_pack, stock_packs, typed FoodEvidence ref | CatalogSource |
| FoodEvidence | typed recipe-component/SKU/pantry subject; evidence ID/revision; per-allergen ingredient and cross-contact assessments | EvidenceSource |
| CartLine | required/pantry/buy qty, SKU, packs, unused, unit price, line cost, source refs | Cart builder |
| DraftCart | cart_id, cart revision, request revision, selected dishes/lines, subtotal, verification basis, three statuses | Verifier + persistence |
| SessionState | effective MealRequest + current DraftCart + expires_at; accepted cart history immutable | DraftRepository (Task 6) |

No display-name joins; no floating-point money; Decimal intermediates; source time UTC. JSON field names should follow existing Pydantic records and [Data Contract](../DATA_CONTRACT.md), not this prose alone.

## Proposed service and port interfaces

- RecipeSource.get(recipe_id, version); list_eligible(effective_request, as_of); current_version(recipe_id, as_of).
- CatalogSource.get_view(store_id, as_of) returns **complete** coherent CatalogView; refresh_view(store_id, previous_view, expired_facts, as_of) returns source-attested CatalogRefreshResult. A still-valid carried price requires matching per-SKU fact ref and new snapshot.
- EvidenceSource.current_for_subject(typed_subject_ref, as_of) returns actual current revision or UNKNOWN.
- resolve_needs(request, dishes, recipes) gives needs plus recipe_component_uses + pantry_allocations.
- propose_sku_selections(needs, catalog, limit) proposes exact sourced mappings; build_cart(request, dishes, resolution, **selected**, catalog, as_of) verifies **that mapping** without switching SKUs.
- assess_allergens(request, resolution, purchased_lines, evidence, as_of) produces separate meal status, warnings/blockers and evidence revisions.
- search_candidates(request, sources, catalog, preferred, as_of, max_candidates=3) counts complete attempts and never edits accepted cart.
- DraftRepository.create_session / get_session / compare_and_set_session / delete_session (Task 6); one SQLite transaction verifies **both** request and cart revisions.
- MealService.create / apply_change / explain / accept (Tasks 6–8) handles orchestration and expiry/evidence refresh; never lets chat trigger accept.

### Key deterministic calculations

For each canonical need (ingredient_id, food_form, compatible dimension):
- required_qty = Σ(recipe_component_quantity × target_servings / base_servings)
- pantry_qty = min(required_qty, confirmed compatible pantry allocations)
- buy_qty = max(0, required_qty - pantry_qty)
- packs = ceil(buy_qty / source_sku.pack_quantity), **only when buy_qty > 0**
- unused_qty = packs × pack_quantity - buy_qty
- subtotal_vnd = Σ(packs × price_vnd_per_pack), integer VND
- price is current only if observed_at <= as_of < price_valid_until; stock analogous; each reference belongs to one coherent selected-store snapshot.

If required conversions are unknown or authoritative facts missing, preserve UNKNOWN and fail closed. Never suppress errors by changing menu inputs.

## HTTP routes — proposal from implementation plan Task 8

| Verb + route | Input | Successful response | Error / concurrency |
| --- | --- | --- | --- |
| POST /v1/drafts | Typed MealRequest + selected store/context | DraftCart and effective request, sources, problems | 422 invalid; explicit clarification/data unavailable |
| GET /v1/drafts/{id} | Session identity + authorization context | Current persisted request/draft; GET is read-only | 404 missing/deleted, 410 expired (proposed), auth gate for public |
| PATCH /v1/drafts/{id} | Whitelisted AppliedChange + expected request/cart revision | New verified DRAFT with incremented request revision | 409 stale version; 422 invalid edit; no partial mutation |
| POST /v1/drafts/{id}/accept | Explicit expected cart revision and authorized session | ACCEPTED / RECONFIRM_REQUIRED / BLOCKED with reasons | 409 stale/concurrent, 422 invalid, no duplicate order |
| POST /v1/chat | text + explicit session/cart context | Parsed CREATE / APPLY_CHANGE / EXPLAIN / CLARIFY result | Unsupported action / malicious fields rejected; NEVER implicit ACCEPT |

**Payload detail is deliberately not frozen:** use existing Pydantic models and complete Data Contract. Before coding API, add machine-readable OpenAPI examples and test expected status codes. GET behavior and 404/410 distinctions must be reviewed, not invented as an already approved contract.

## Example request/response sketches (illustrative, not final schema)

~~~json
{
  "request_id": "REQ-001",
  "conversation_revision": 1,
  "diners": 4,
  "meal_type": "dinner",
  "budget_vnd": 140000,
  "dislikes": [],
  "allergens": [],
  "dietary_restrictions": [],
  "pantry": [],
  "selected_store_id": "FG-01"
}
~~~

NOTE: selected_store_id is **illustrative context**, not yet a field in PR #8 MealRequest model; use a reviewed input/store-scoping contract before implementing. Golden fixture includes a different pantry; the JSON above is **not** golden AC01 fixture and must not be used to assert 116,000 VND.

~~~json
{
  "outcome": "RECONFIRM_REQUIRED",
  "cart_id": "CART-001",
  "previous_revision": 1,
  "problems": [{"code": "STOCK_EXPIRED", "source_ref": "fixture-only"}],
  "next_action": "REVIEW_NEW_DRAFT"
}
~~~

Response envelope is a proposal; fields/reason codes should be standardized with actual Task 7 types and [TRACEABILITY](TRACEABILITY.md).

## Revision and acceptance state machine

~~~mermaid
stateDiagram-v2
  [*] --> DRAFT: create sourced candidate
  DRAFT --> DRAFT: applied material edit/new version
  DRAFT --> DRAFT: source refresh and renewed review
  DRAFT --> ACCEPTED: explicit accept + current source/recipe/evidence + dual CAS
  DRAFT --> REJECTED: explicit reject
  ACCEPTED --> DRAFT: create separate NEW draft ID after edit
  ACCEPTED --> [*]
  REJECTED --> [*]
~~~

Accepted cart is immutable. API service MUST revalidate before CAS, but local CAS alone does not create an external provider transaction. Independently changed external facts after checking are beyond UC-01 stock reservation.

## Exception mapping and race tests

- Missing price/stock, expired fact, incompatible conversion, unavailable recipe/evidence → typed failure with no false VERIFIED.
- Revision mismatch from concurrent edit/accept, changed recipe/version/label, source-refresh price incompatibility → **no acceptance**, new review if feasible.
- No acceptable candidate in bounded search: return specific evaluated evidence and named outcome; currently PR #8's status string differs from canonical specification and needs explicit resolution before freezing API.
- Invalid LLM structured output → CLARIFY/typed error, no mutation. Unknown fields not accepted.
- Allergies persist across follow-up changes; do not create cross-session memory.

## Completion gate

Do not label API implemented until HTTP calls exercise actual FastAPI → MealService → DraftRepository → fixture source/verifier, with no hand-constructed success responses and with recorded AC01/08/19/21/24/27/28/33 coverage. 
