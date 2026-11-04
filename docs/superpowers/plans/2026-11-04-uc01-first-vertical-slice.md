# UC-01 Meal-to-Cart First Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the smallest independently testable MealMate workflow that converts a sourced shared-meal request into a verified single-store grocery draft, supports material edits and explicit safe-to-accept *cart* confirmation, and exposes a minimal conversational API without inventing food/catalog facts.

**Architecture:** Keep deterministic source-backed recipe → ingredient/pantry allocation → selected SKU/package → allergen assessment pure and testable. Explicitly distinguish **candidate generation** from **verification of an unchanged selected SKU mapping**; retain all recipe-component and pantry-item identities through to food evidence and acceptance. Add bounded alternatives, a session-scoped request+draft revision store, then a thin HTTP/intent adapter. A catalog port returns complete, coherent catalog views (SKU rows plus snapshot) and an attested refresh result; no cross-source mixing or guessed facts.

**Tech Stack (proposed, NOT previously selected):** Python **3.12**, Pydantic **2.x** for typed source/request/cart records, FastAPI for a small JSON API, stdlib `sqlite3` for local transactional request+draft CAS, `pytest` + FastAPI TestClient/`httpx` for tests, and versioned JSON synthetic fixtures. Use an installable `src/` package with setuptools build backend; validate clean installation with `python -m pip install -e '.[dev]'`. CI uses a deterministic `IntentInterpreter` stub; Task 9 adds a **separately tested live LLM adapter** with explicit collected/executed test evidence. The LLM never supplies recipe quantities, allergen clearance or SKU/stock/price facts. Pin exact dependencies when implementing after compatibility review.

**Spec:** `docs/superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md` (33 proposed acceptance cases), `docs/DATA_CONTRACT.md` (authoritative field semantics), `docs/PRODUCT.md`. Tracking: https://github.com/hungtvb/mealmate/issues/2 and design PR https://github.com/hungtvb/mealmate/pull/3.

**Base-state constraint:** As of this plan, the repository has documentation but **no `pyproject.toml`, application modules, tests, or runtime CI**. This plan must be reviewed as a **stacked PR targeting `docs/uc01-meal-to-cart-design`**; implement in a separate code PR after design/plan approval and the upstream design PR is merged in authorized order. No code is authorized by creating this plan.

## Global Constraints

- One selected store, one shared family meal (multiple dishes allowed); all shared recipe components use the union of diners' declared allergens/restrictions.
- Recipe-first from complete curated `recipe_id/version` and `base_servings/default_serving_role`; never let an LLM invent quantities, catalog entries, stock or prices.
- Whole sellable packs, integer VND, `subtotal_vnd=Σ(packs×price_vnd_per_pack)`; 140,000-VND golden budget and 116,000-VND golden subtotal.
- `max_evaluated_candidates=3` **including initial**; SKU substitutions count as new candidates, preserving user request revision and hard constraints.
- Canonical `ingredient_id + food_form + sourced unit conversion`; pantry only deducted when quantity confirmed. No one SKU allocated to multiple different ingredient demands.
- Keep `cart_verification_status`, `meal_allergen_status`, `user_review_state` separate. Unknown pantry-only allergen evidence permits explicit cart acceptance with warning; unknown selected SKU/recipe evidence blocks it; known conflicts reject the meal. Never say medically “safe.”
- Price and stock have independent source-defined expiries; refreshed data must be in a new **coherent source-attested** same-store snapshot. Fail closed on incompatibility. No global TTL.
- `verification_basis` binds request, cart, catalog, recipe and FoodEvidence revisions. Read-only turns do not mutate request; acceptance is an explicit revision-checked **draft** transition and never a payment/order or stock reservation.
- Keep the first-slice subtotal explicitly **excluding shipping, tax and promotions**. No fake "checkout total."
- Local synthetic fixtures are test data, **not** evidence of a live provider, medical safety or true stock reservation. No personal health data, secrets or proprietary ShopMate code in git.

## Review Focus — inputs that can silently break correctness

1. **Multi-allergen same SKU and two pantry packages:** `SHRIMP` absent but `PEANUT` cross-contact unknown on a selected SKU blocks acceptance; two allocated pantry packages with different evidence must each be checked and warned distinctly (Tasks 2 and 4, `test_ac17`, `test_two_pantry_packages_distinct_evidence`).
2. **Overlapping ingredient demands / rounding:** add tomato demands from two dishes and deduct one pantry quantity *before* selecting a whole pack (Tasks 2–3, `test_ac12`).
3. **Time-of-check/time-of-use and source refresh:** acceptance after stock expiry or recipe/label revision change fails; compatible vs incompatible price carry-forward is source-attested with a new coherent catalog view, never fabricated (Tasks 1 and 7, `test_ac28`, `test_ac33_compatible_refresh`, `test_ac33_incompatible_refresh`).
4. **Follow-up intent and request CAS:** read-only explanation preserves revision; applied serving edit survives service restart and cannot race acceptance based on a stale request (Task 6, `test_ac27`, `test_restart_preserves_request_constraints`, `test_request_edit_races_accept`).
5. **Fallback evidence and candidate cap:** no fourth candidate; an alternate SKU must be evaluated with its own price/stock/label and the same user's constraints (Task 5, `test_ac23`, `test_ac29`, `test_ac30`).

## Proposed file map (new files, subject to stack approval)

- `pyproject.toml`: minimal runtime/development dependencies and `pytest` settings.
- `src/mealmate/__init__.py`, `src/mealmate/models/__init__.py`, `src/mealmate/models/{meal,catalog,cart}.py`: installable Python package and small Pydantic records with the Data Contract fields; integer VND and UTC-aware timestamps.
- `src/mealmate/ports.py`: `RecipeSource`, `CatalogSource`, `EvidenceSource` protocols; versioned candidate discovery, complete SKU view and attested refresh.
- `src/mealmate/fixtures.py` and `tests/fixtures/uc01_golden.json`: read-only synthetic F-UC01-POS plus scoped AC29/30/33 variants and explicit compatible/incompatible refresh attestation fixtures; no real personal data.
- `src/mealmate/quantities.py`: recipe scaling, aggregation and pantry allocation with a **source identity/consumption trace**.
- `src/mealmate/cart_builder.py`: propose typed version-bound SKU selections; verify exactly the chosen selection, complete packs, subtotal and stock/budget.
- `src/mealmate/allergens.py`: assess recipe-component, selected SKU and allocated pantry subject identities, preserving per-allergen evidence revisions.
- `src/mealmate/search.py`: bounded candidate evaluator and distinct no-candidate outcomes.
- `src/mealmate/drafts.py`: SQLite session-scoped `MealRequest` **and** `DraftCart`, dual-version CAS, session expiry/delete and guarded acceptance.
- `src/mealmate/service.py`: request/turn mutation, sourced-candidate re-evaluation, refresh and acceptance orchestration.
- `src/mealmate/api.py`, `src/mealmate/intent.py`, `src/mealmate/llm_intent.py`: thin FastAPI HTTP, interpreter protocol and later provider-backed structured extraction boundary.
- `tests/test_{fixtures,quantities,cart_builder,allergens,search,drafts,api}.py`, `tests/test_uc01_e2e.py`: meaningful scenario-driven tests, not test count for its own sake.

## Task 1 — Typed records and a reproducible source fixture

**Files:** Create `pyproject.toml` (setuptools build backend + editable `src/` packaging, `[project.optional-dependencies].dev`, registered `live_llm` pytest marker), `src/mealmate/__init__.py`, `src/mealmate/models/__init__.py`, `src/mealmate/models/{meal,catalog,cart}.py`, `src/mealmate/ports.py`, `src/mealmate/fixtures.py`, `tests/fixtures/uc01_golden.json`, `tests/test_fixtures.py`.

**Interfaces:**
- `load_fixture(fixture_id: str) -> FixtureBundle`, with typed `MealRequest`, four versioned `Recipe` records, `CatalogView(snapshot: CatalogSnapshot, skus: list[ProductSKU])` containing six FG-01 SKUs, per-SKU price/stock fact refs and `FoodEvidence`; source fixture IDs are synthetic and explicit. `CatalogView` and `CatalogRefreshResult(view: CatalogView | None, price_carry_forward_attested: bool, attestation_ref: str | None, problem_code: str | None)` are defined in `models/catalog.py`.
- `RecipeSource.get(recipe_id: str, version: str) -> Recipe | None`, `RecipeSource.list_eligible(request: MealRequest, as_of: datetime) -> list[Recipe]` (sourced IDs/versions only) and `RecipeSource.current_version(recipe_id: str, as_of: datetime) -> str | None` (for acceptance-time revision checks). `CatalogSource.get_view(store_id: str, as_of: datetime) -> CatalogView` returns the coherent `CatalogSnapshot` **plus** version-bound SKU rows; `CatalogSource.refresh_view(store_id: str, previous: CatalogView, expired_facts: Literal['PRICE','STOCK','BOTH'], as_of: datetime) -> CatalogRefreshResult` returns a newly issued coherent view with provider evidence or an explicit failure. `EvidenceSource.current_for_subject(subject_ref: FoodSubjectRef, as_of: datetime) -> FoodEvidence | None` returns the current typed evidence/revision, never only an old pinned record. Define `FoodSubjectRef` as the typed composite recipe `(recipe_id, version, component_id)`, SKU `(store_id, sku, snapshot_id)` or pantry `(request_id, pantry_item_id)` in `models/catalog.py`; no display-name matching.

- [ ] **Step 1 — failing tests:** `test_golden_fixture_is_typed_and_versioned` validates 4 curated recipes, 3 pantry identities, 6 SKU rows under `CatalogView.snapshot=S-FG-001`, source IDs/revisions, 06:00Z observation / 08:00Z price / 06:30Z stock deadlines and rejects invalid price. `test_sourced_recipe_and_sku_discovery` proves `list_eligible()` returns sourced recipe IDs/versions and `get_view()` exposes those six matching FG-01 SKUs without invented IDs. `test_catalog_refresh_attestation_fixture` pins an attested new snapshot carrying forward still-valid price with fresh stock, and an incompatible/missing-attestation outcome; unknown future stock numbers must not be fabricated. `test_clean_src_editable_install` (CI smoke) imports the installed `mealmate` package from a clean Python 3.12 environment.
- [ ] **Step 2 — prove RED:** after `python -m pip install -e '.[dev]'` in a fresh Python 3.12 virtual environment, run `python -m pytest tests/test_fixtures.py -q` → FAIL because fixture contracts are not yet implemented (not because `mealmate` is an uninstalled package). The smoke install/import succeeds once the minimal package metadata exists.
- [ ] **Step 3 — minimal implementation:** implement Pydantic source models and the protocol/fixture adapters with exact spec §11 rows. `pyproject.toml` must contain a real `[build-system]` for setuptools, `package-dir` / `src` discovery and `dev` extra for pytest/httpx/FastAPI; register `live_llm` under `[tool.pytest.ini_options].markers`. Synthetic AC33 compatible and incompatible refresh responses must be distinguishable through `CatalogRefreshResult`; no unsourced data.
- [ ] **Step 4 — prove GREEN:** clean Python 3.12 venv → `python -m pip install -e '.[dev]'` → exit 0; `python -c 'import mealmate'` → exit 0; `python -m pytest tests/test_fixtures.py -q` and current non-live suite → PASS. CI must repeat the clean install before running tests.
- [ ] **Step 5 — commit:** `git add pyproject.toml src tests && git commit -m "feat: pin UC-01 typed source fixture"`.

## Task 2 — Deterministic recipe quantities and pantry deduction

**Files:** Create `src/mealmate/quantities.py`, `tests/test_quantities.py`.

**Interfaces:** `resolve_needs(request: MealRequest, dishes: list[PlannedDish], recipes: RecipeSource) -> NeedsResolution`, defined in `quantities.py`: `NeedsResolution.needs: list[IngredientNeed]` for aggregate `ingredient_id + food_form + unit` quantities, `recipe_component_uses: list[RecipeComponentUse]` retaining `(recipe_id, recipe_version, component_id)` and actual scaled quantity, and `pantry_allocations: list[PantryAllocation]` retaining `(request_id, pantry_item_id)`, actual deducted quantity, form/unit, and evidence subject reference. Only **confirmed** pantry quantities generate allocations; `IngredientNeed` includes `required_qty`, `confirmed_pantry_qty`, `buy_qty`. No intermediate pack rounding.

- [ ] **Step 1 — failing tests:** `test_ac12_aggregate_before_rounding` aggregates 300+200 g tomatoes and deducts 100 g confirmed pantry to buy **400 g**, retaining both recipe component refs. `test_two_pantry_packages_distinct_evidence_trace` allocates two confirmed packages of one ingredient, each preserving its unique `pantry_item_id` and scoped evidence reference, even when the entire recipe need is covered by pantry. `test_ac26_side_serving_edit` changes R04 4→6 and expects 600 g greens / **2600 ml** combined water, supplied from a traced pantry item. `test_ac11_unknown_raw_cooked_conversion` fails closed without sourced factors.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_quantities.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** use sourced recipe/version and serving yield; create a component use for every scaled ingredient including seasonings and pantry-only food; allocate confirmed pantry deterministically across individual item IDs, retaining each allocation's evidence identity. Calculate aggregate needs with decimal/rational arithmetic; no unsourced conversion, no pack rounding here.
- [ ] **Step 4 — prove GREEN:** same command and full current suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/quantities.py tests/test_quantities.py && git commit -m "feat: resolve recipe and pantry quantities"`.

## Task 3 — Package selection and economic cart verification

**Files:** Create `src/mealmate/cart_builder.py`, `tests/test_cart_builder.py`.

**Interfaces:** `build_cart(request: MealRequest, dishes: list[PlannedDish], needs: list[IngredientNeed], catalog: CatalogSnapshot, as_of: datetime) -> DraftCart` with independently populated `cart_verification_status` and structured `problems[]`; meal-allergen status is assessed in Task 4, not implicitly cleared here.

- [ ] **Step 1 — failing tests:** `test_ac01_golden` → **5 SKU lines / 6 complete packs / 116000 VND / budget 140000 VND / cart VERIFIED** at 06:10Z. `test_ac06_full_packs` → 600 g with 500-g pack at 75000 VND costs **150000**, leaves 400 g; not 90000. `test_ac09_repriced_candidate` → **148000** and `BUDGET_EXCEEDED`. `test_ac14_multi_ingredient_allocation` rejects a bundled SKU used for two demands.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_cart_builder.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** select the lowest *total full-pack* eligible SKU for each one canonical ingredient/form/quantity, validate complete snapshot and integer stock, preserve every source ref. If a fact expires or compatible source is absent, return `DATA_UNAVAILABLE`, not a guessed price/stock. Do not claim global optimization.
- [ ] **Step 4 — prove GREEN:** same and current full suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/cart_builder.py tests/test_cart_builder.py && git commit -m "feat: calculate sourced sellable cart packs"`.

## Task 4 — Allergy evidence eligibility, separate from cart arithmetic

**Files:** Create `src/mealmate/allergens.py`, `tests/test_allergens.py`.

**Interfaces:** `assess_allergens(request: MealRequest, dishes: list[PlannedDish], lines: list[CartLine], evidence: EvidenceSource) -> AllergyAssessment`, containing `meal_allergen_status`, `acceptance_blocked`, and typed `problems[]` each with `allergen_id`, `subject_ref` and source.

- [ ] **Step 1 — failing tests:** `test_ac17` two allergens on same SKU: PEANUT unknown stays `REVIEW_REQUIRED` and **blocks** purchased-SKU acceptance despite SHRIMP assessed absent. `test_ac21` unknown pantry-only evidence yields `REVIEW_REQUIRED` with visible warning **but does not block cart acceptance** if all non-pantry evidence passes. `test_ac24` selected SKU unknown blocks. `test_ac03` known recipe/SKU allergen conflicts reject candidate.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_allergens.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** check each declared allergen separately on each used recipe component, selected SKU and relied-on pantry item; never infer `ASSESSED_ABSENT` from label omission or one other allergen. Keep warning and cart state independent; no medical-safety label.
- [ ] **Step 4 — prove GREEN:** same and current suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/allergens.py tests/test_allergens.py && git commit -m "feat: gate allergy evidence by source"`.

## Task 5 — Bounded evidence-backed candidate search

**Files:** Create `src/mealmate/search.py`, `tests/test_search.py`.

**Interfaces:** `search_candidates(request: MealRequest, recipe_source: RecipeSource, catalog: CatalogSnapshot, evidence: EvidenceSource, preferred: Candidate | None, as_of: datetime, max_candidates: int = 3) -> SearchResult`. Define `Candidate` and `SearchResult` in `search.py`. Candidate identity includes complete recipe versions/dish servings plus selected SKU/pack combination; `SearchResult` contains candidate IDs, attempted blockers, outcome and acceptable draft (if any). All candidate checks use the supplied deterministic `as_of`.

- [ ] **Step 1 — failing tests:** `test_ac23_three_total_candidates` evaluates C01+C02+C03 **once each**, never C04, and gives `NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET`. `test_ac29` re-evaluates prior tomato SKU after price refresh and finds sourced ALT yielding **120000 VND**. `test_ac30` replaces out-of-stock tofu in coherent `S-FG-004` with a sourced 400-g alternative yielding **119000 VND**. `test_ac31_mixed_stores_rejected` blocks a basket mixing FG-01 and FG-02.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_search.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** evaluate initial + at most two *distinct full candidates*, using complete recipe-first logic and catalog-sourced alternatives. No budget/allergen relaxation, no automatic store switching, no modification of an already ACCEPTED draft. Use the approved separate `NO_ACCEPTABLE_CART_IN_EVALUATED_SET` outcome for economically valid but non-pantry allergen-ineligible candidates.
- [ ] **Step 4 — prove GREEN:** same and current suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/search.py tests/test_search.py && git commit -m "feat: bound budget and stock alternatives"`.

## Task 6 — Persisted draft and material-versus-read-only turns

**Files:** Create `src/mealmate/drafts.py`, `src/mealmate/service.py`, `tests/test_drafts.py`.

**Interfaces:** `DraftRepository.save_new(draft: DraftCart) -> DraftCart`; `DraftRepository.get(cart_id: str) -> DraftCart | None`; `DraftRepository.compare_and_set(cart_id: str, expected_revision: int, updated: DraftCart) -> bool`. `MealService(recipe_source: RecipeSource, catalog_source: CatalogSource, evidence_source: EvidenceSource, repo: DraftRepository)`; `MealService.apply_change(cart_id: str, change: AppliedChange, as_of: datetime) -> DraftCart`; `MealService.explain(cart_id: str, question: str) -> Explanation`. Define `AppliedChange` (validated whitelisted dimension and new value) and `Explanation` (sourced text + citations) in `service.py`; never treat arbitrary chat text as an applied change.

- [ ] **Step 1 — failing tests:** `test_ac27_read_only_turn` preserves `conversation_revision`, cart revision and current verification for “Vì sao chọn món này?”. `test_ac20_material_change` increments effective request revision and invalidates old acceptance, then rebuilds quantities. `test_ac26` edited R04 → **132000 VND / 7 packs**. Duplicate pantry IDs and unconfirmed oil quantity do not silently deduct stock (`AC04/AC18`).
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_drafts.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** SQLite transactional local CAS keyed on `cart_id + revision`, a single user request revision for material changes, immutable applied-change records, and explanation-only path with **no mutation**. Persist only explicit active-session constraints/drafts; do **not** create cross-session preference/allergy memory without separate explicit user confirmation.
- [ ] **Step 4 — prove GREEN:** same and current suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/drafts.py src/mealmate/service.py tests/test_drafts.py && git commit -m "feat: version conversational draft revisions"`.

## Task 7 — Freshness and evidence revision gate at explicit acceptance

**Files:** Modify `src/mealmate/drafts.py`, `src/mealmate/service.py`; create `tests/test_acceptance.py`.

**Interfaces:** `MealService.accept(cart_id: str, expected_revision: int, as_of: datetime) -> AcceptanceResult`, with `ACCEPTED | RECONFIRM_REQUIRED | BLOCKED` and typed reason codes. Define `AcceptanceResult` in `drafts.py` and persist `verification_basis` (including per-SKU fact validity and typed recipe/evidence revisions) with each draft. The result is a draft approval, **not** an order.

- [ ] **Step 1 — failing tests:** `test_ac08_accept_verified` explicit action transitions one current cart to ACCEPTED. `test_ac19_stock_expired` at 06:31Z denies old snapshot. `test_ac28_recipe_or_label_revision_race` denies stale verified basis even when stock/price valid. `test_ac33_price_valid_stock_expired` at 06:45Z reuses price **only if** provider issues a compatible new coherent snapshot, otherwise returns DATA_UNAVAILABLE/reconfirmation. `test_double_accept_and_stale_revision` rejects the second stale CAS; `test_ac21_pantry_warning_stays_visible` permits cart acceptance with unresolved pantry warning only.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_acceptance.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** build and compare `verification_basis={request_revision, cart_revision, snapshot_id, catalog_source_revision, selected_recipe_versions, selected_food_evidence_revisions}` against fresh consistent authoritative reads; re-evaluate all checks. Only after passing, perform one local `UPDATE ... WHERE revision=? AND user_review_state='DRAFT'` with affected-row check. **No claim of cross-provider ACID**; if source cannot supply compatible version/provenance or the basis changes during confirmation, fail closed, refresh and demand new shopper confirmation.
- [ ] **Step 4 — prove GREEN:** same and full suite → PASS.
- [ ] **Step 5 — commit:** `git add src/mealmate/drafts.py src/mealmate/service.py tests/test_acceptance.py && git commit -m "feat: revalidate evidence before draft acceptance"`.

## Task 8 — Thin API and conversational boundary with scenario-level E2E

**Files:** Create `src/mealmate/api.py`, `src/mealmate/intent.py`, `tests/test_api.py`, `tests/test_uc01_e2e.py`, `.github/workflows/ci.yml`.

**Interfaces:** `IntentInterpreter.interpret(text: str, current_request: MealRequest | None) -> ParsedTurn`; define `ParsedTurn` in `intent.py`, with `action` in `CREATE | APPLY_CHANGE | EXPLAIN | CLARIFY` and schema-whitelisted fields. Deterministic stub tests the contract, not free-form language understanding. FastAPI `create_app(service: MealService, interpreter: IntentInterpreter) -> FastAPI`. Routes: `POST /v1/drafts` (structured typed request), `GET /v1/drafts/{id}`, `PATCH /v1/drafts/{id}` (explicit material change), `POST /v1/drafts/{id}/accept` (explicit action + revision), `POST /v1/chat` (parsed turn; never an implicit accept).

- [ ] **Step 1 — failing tests:** API test verifies valid structured fixture returns five lines / six packs / **116000 VND** with provenance; invalid budget and negative/unknown quantities return explicit 422/problem types. E2E `test_uc01_happy_to_accept` does POST draft→GET→explicit ACCEPT with version, no order. `test_uc01_unknown_purchased_sku_blocked` and `test_uc01_expired_stock_requires_reconfirm` exercise AC24/AC33 through the HTTP boundary. `test_uc01_chat_followups` uses a deterministic interpreter stub to test “Vì sao?” vs actual portion edit preserving constraints and allergy warnings. `test_ac32_personal_menu_not_supported` returns clear limitation.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_api.py tests/test_uc01_e2e.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** wire the already tested service into FastAPI; use a deterministic `IntentInterpreter` for replayable CI and make any real LLM extraction a separate injectable adapter requiring strict schema validation/timeout/error handling. A real LLM or MCP provider test is **not** a success claim for this task until explicitly configured and executed. No frontend design or fake checkout.
- [ ] **Step 4 — prove GREEN:** `python -m pytest -q` and `python -m compileall -q src/mealmate` → PASS. CI must execute these commands against Python 3.12; check actual workflow logs, not just checkmark status. Record scenario results with exact data source (`synthetic fixture` / `live integration`).
- [ ] **Step 5 — commit:** `git add src/mealmate/api.py src/mealmate/intent.py tests/test_api.py tests/test_uc01_e2e.py .github/workflows/ci.yml && git commit -m "feat: expose testable draft-cart API"`.

## Task 9 — Provider-backed conversational intent (after deterministic baseline)

**Files:** Create `src/mealmate/llm_intent.py`, `tests/test_llm_intent.py`, `tests/test_llm_uc01_integration.py`; modify `src/mealmate/api.py` to inject the real interpreter when explicitly configured, retaining the deterministic stub for tests.

**Interfaces:** `ProviderIntentInterpreter.interpret(text: str, current_request: MealRequest | None) -> ParsedTurn` implements Task 8's interpreter interface. Configuration is supplied by environment (`MEALMATE_LLM_BASE_URL`, `MEALMATE_LLM_API_KEY`, `MEALMATE_LLM_MODEL`) and never committed. A provider's response must be parsed into the existing whitelisted `ParsedTurn` schema; `CLARIFY`/typed error on missing or malformed fields rather than silent assumptions.

- [ ] **Step 1 — failing tests:** `test_llm_extracts_four_diners_and_budget` with a stub provider response maps an initial Vietnamese meal request to canonical typed fields, without a fabricated recipe. `test_llm_followup_keeps_declared_allergens` preserves allergies across a material dish edit. `test_llm_explanation_is_read_only` does not increment `conversation_revision`. `test_llm_cannot_auto_accept_or_inject_sku_price` rejects a tool/model output that tries to submit/clear an allergen or overwrite verified catalog facts. `test_provider_timeout_and_bad_json` returns clear typed failure and leaves draft unchanged.
- [ ] **Step 2 — prove RED:** `python -m pytest tests/test_llm_intent.py -q` → FAIL.
- [ ] **Step 3 — minimal implementation:** one provider adapter with bounded timeout/retry, explicit structured-output validation and untrusted-text handling. Source-backed deterministic service recomputes all meal/cart facts after parsed intent; no direct LLM route to draft acceptance or product mutations.
- [ ] **Step 4 — prove GREEN:** `python -m pytest -q` → PASS with stubs. Run `python -m pytest tests/test_llm_uc01_integration.py -q -m live_llm` **only** when credentials are connected; report `NOT_RUN` otherwise, not PASS. When live enabled, assert at least one end-to-end natural-language request and one follow-up preserve scoped constraints and create an accurate draft from **known synthetic catalog facts**.
- [ ] **Step 5 — commit:** `git add src/mealmate/llm_intent.py src/mealmate/api.py tests/test_llm_intent.py tests/test_llm_uc01_integration.py && git commit -m "feat: validate natural-language meal intent"`.

## Post-task acceptance, review, and release gates

- **Minimal end-to-end proof required before expanding scope:** AC01 exact sourced cart, AC06/12 quantities, AC17/21/24 allergy split, AC19/28/33 acceptance-time race/freshness, AC23/29/30 bounded fallback, AC26/27 follow-ups, AC31/32 store/shared-meal boundaries. Other AC IDs remain tracked as explicit coverage debt until tested; do **not** assert 33/33 pass merely because 33 scenario descriptions exist.
- **Full baseline:** `python -m pytest -q`; `python -m compileall -q src/mealmate`; scenario coverage table with actual test identifiers and passing/failing statuses. Before calling the feature an **AI-assisted natural-language** experience, run Task 9's provider-backed integration with configured credentials and a known catalog fixture. An unavailable live provider must be explicitly `NOT_RUN`, never claimed PASS.
- **Quality gate after each task:** review task diff against its interfaces and ACs, run all existing tests, note trade-offs and update Issue/PR evidence. Before merge, request a fresh independent review and fix actionable issues. Do not count self-review as independent.
- **Explicitly deferred:** multi-store optimization, individual meals, payment/checkout, reservations, medical meal guarantees, long-term allergy memory, vector DB/RAG for structured quantities, MCP transport until actual provider boundary, LangGraph/multi-agent until orchestration needs it, and UI styling. Evaluate any ShopMate reuse by ownership/license/correctness first; import nothing by default.
- **Execution sequence:** approve this plan + technical stack → merge design PR #3 only with explicit authorization → merge stacked planning PR in order → create a separate implementation branch/PR → perform Tasks 1–8 via TDD, then Task 9 when a provider is configured, with review gates. Do not merge PR #3, this planning PR, or a future code PR without explicit user authorization. No implementation work is authorized by this planning document.
