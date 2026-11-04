"""UC-01 Task 3 — source-backed package economics and explicit SKU verification."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from importlib import import_module

from mealmate.fixtures import FixtureSources, load_fixture
from mealmate.models.catalog import CatalogView
from mealmate.models.meal import PlannedDish
from mealmate.quantities import IngredientNeed, NeedsResolution, resolve_needs

AT = datetime(2026, 11, 4, 6, 10, tzinfo=timezone.utc)
REPRICED_AT = datetime(2026, 11, 4, 6, 12, tzinfo=timezone.utc)


def api():
    return import_module("mealmate.cart_builder")


def golden():
    fixture = load_fixture("F-UC01-POS")
    source = FixtureSources(fixture)
    dishes = [
        PlannedDish(
            recipe_id=r.recipe_id,
            recipe_version=r.version,
            target_servings=4,
            serving_role=r.default_serving_role,
            portion_rationale="curated role-specific four servings",
        )
        for r in fixture.recipes
    ]
    resolution = resolve_needs(fixture.request, dishes, source)
    return fixture, dishes, resolution


def fresh_view(*, tomato_price=50000, alternative=False):
    fixture, _, _ = golden()
    view = fixture.catalog.model_dump()
    view["snapshot"]["snapshot_id"] = "S-FG-002"
    view["snapshot"]["source_revision"] = "stock-price-v2"
    view["snapshot"]["observed_at"] = datetime(2026, 11, 4, 6, 11, tzinfo=timezone.utc)
    for row in view["skus"]:
        row["catalog_snapshot_id"] = "S-FG-002"
        row["food_evidence_ref"]["parts"] = ("FG-01", row["sku"], "S-FG-002")
        row["price_fact_ref"] = "fixture:price/" + row["sku"] + "@price-v2"
        row["stock_fact_ref"] = "fixture:stock/" + row["sku"] + "@stock-v2"
        if row["sku"] == "G-TOM500":
            row["price_vnd_per_pack"] = tomato_price
    if alternative:
        alternate = next(r for r in view["skus"] if r["sku"] == "G-TOM500").copy()
        alternate["sku"] = "G-TOM500-ALT"
        alternate["price_vnd_per_pack"] = 22000
        alternate["stock_packs"] = 3
        alternate["food_evidence_ref"] = {"kind": "sku", "parts": ("FG-01", "G-TOM500-ALT", "S-FG-002")}
        alternate["price_fact_ref"] = "fixture:price/G-TOM500-ALT@price-v2"
        alternate["stock_fact_ref"] = "fixture:stock/G-TOM500-ALT@stock-v2"
        view["skus"].append(alternate)
    return CatalogView.model_validate(view)


def selection_for(resolution, view):
    candidates = api().propose_sku_selections(resolution.needs, view, limit=3)
    assert candidates
    return candidates[0]


def test_ac01_golden_five_lines_six_packs_116000() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    cart = api().build_cart(fixture.request, dishes, resolution, selected, fixture.catalog, AT)
    assert cart.cart_verification_status == "VERIFIED"
    assert cart.meal_allergen_status == "NOT_ASSESSED"
    assert cart.user_review_state == "DRAFT"
    assert (cart.subtotal_vnd, len(cart.lines), sum(line.packs for line in cart.lines)) == (116000, 5, 6)
    assert {line.sku: line.packs for line in cart.lines} == {
        "G-EGG10": 1, "G-TOM500": 1, "G-OIL500": 1,
        "G-TOFU200": 2, "G-GREEN500": 1,
    }
    tomato = next(line for line in cart.lines if line.ingredient_id == "tomato")
    assert (tomato.required_qty, tomato.confirmed_pantry_qty, tomato.buy_qty) == (500, 100, 400)
    assert (tomato.unused_qty, tomato.unit) == (Decimal(100), "g")
    assert all(line.source_refs and line.line_total_vnd == line.packs * line.price_per_pack_vnd for line in cart.lines)
    assert cart.verification_basis["catalog_source_revision"] == fixture.catalog.snapshot.source_revision
    assert cart.verification_basis["request_revision"] == fixture.request.conversation_revision
    assert cart.verified_at == AT
    assert cart.accepted_at is None


def test_ac06_full_packs_charges_150000_and_exposes_400g_unused() -> None:
    fixture, dishes, _ = golden()
    raw = fixture.catalog.model_dump()
    greens = next(row for row in raw["skus"] if row["sku"] == "G-GREEN500")
    greens["price_vnd_per_pack"] = 75000
    greens["price_fact_ref"] = "fixture:price/G-GREEN500@price-75k"
    view = CatalogView.model_validate(raw)
    needs = NeedsResolution(
        needs=[IngredientNeed("greens", "fresh_raw", "g", Decimal(600), Decimal(0), Decimal(600))],
        recipe_component_uses=[], pantry_allocations=[],
    )
    selected = selection_for(needs, view)
    request = fixture.request.model_copy(update={"budget_vnd": 200000})
    cart = api().build_cart(request, dishes, needs, selected, view, AT)
    assert cart.cart_verification_status == "VERIFIED"
    assert len(cart.lines) == 1
    line = cart.lines[0]
    assert (line.packs, line.line_total_vnd, cart.subtotal_vnd) == (2, 150000, 150000)
    assert (line.unused_qty, line.unit) == (Decimal(400), "g")


def test_ac09_repriced_original_sku_is_not_auto_reselected() -> None:
    fixture, dishes, resolution = golden()
    original = selection_for(resolution, fixture.catalog)
    view = fresh_view(tomato_price=50000)
    rebound = replace(original, snapshot_id=view.snapshot.snapshot_id)
    cart = api().build_cart(fixture.request, dishes, resolution, rebound, view, REPRICED_AT)
    assert cart.cart_verification_status == "INFEASIBLE"
    assert cart.subtotal_vnd == 148000
    assert "BUDGET_EXCEEDED" in {item["code"] for item in cart.problems}
    assert next(line.sku for line in cart.lines if line.ingredient_id == "tomato") == "G-TOM500"


def test_builder_preserves_explicit_choice_even_if_cheaper_alt_exists() -> None:
    fixture, dishes, resolution = golden()
    old = selection_for(resolution, fixture.catalog)
    view = fresh_view(tomato_price=50000, alternative=True)
    possible = api().propose_sku_selections(resolution.needs, view, limit=2)
    assert any(a.sku == "G-TOM500-ALT" for a in possible[0].selected_skus)
    old_rebound = replace(old, snapshot_id=view.snapshot.snapshot_id)
    cart = api().build_cart(fixture.request, dishes, resolution, old_rebound, view, REPRICED_AT)
    assert cart.subtotal_vnd == 148000
    assert "BUDGET_EXCEEDED" in {p["code"] for p in cart.problems}
    assert next(line.sku for line in cart.lines if line.ingredient_id == "tomato") == "G-TOM500"


def test_old_snapshot_selection_must_not_be_accepted_for_new_snapshot() -> None:
    fixture, dishes, resolution = golden()
    original = selection_for(resolution, fixture.catalog)
    cart = api().build_cart(fixture.request, dishes, resolution, original, fresh_view(), REPRICED_AT)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "SNAPSHOT_MISMATCH" in {p["code"] for p in cart.problems}
    assert not cart.lines


def test_ac14_one_sku_cannot_satisfy_multiple_ingredient_demands() -> None:
    fixture, dishes, resolution = golden()
    chosen = selection_for(resolution, fixture.catalog)
    eggs = next(s for s in chosen.selected_skus if s.ingredient_id == "eggs")
    tomato = next(s for s in chosen.selected_skus if s.ingredient_id == "tomato")
    duplicated = replace(chosen, selected_skus=tuple(
        replace(s, sku=eggs.sku) if s == tomato else s for s in chosen.selected_skus
    ))
    cart = api().build_cart(fixture.request, dishes, resolution, duplicated, fixture.catalog, AT)
    assert cart.cart_verification_status == "INFEASIBLE"
    assert "SKU_REUSED_FOR_DIFFERENT_INGREDIENT" in {p["code"] for p in cart.problems}
    assert cart.verified_at is None


def test_missing_sku_rows_fail_closed() -> None:
    fixture, dishes, resolution = golden()
    selection = selection_for(resolution, fixture.catalog)
    metadata_only = CatalogView(snapshot=fixture.catalog.snapshot, skus=[])
    cart = api().build_cart(fixture.request, dishes, resolution, selection, metadata_only, AT)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "SKU_NOT_FOUND" in {p["code"] for p in cart.problems}
    assert cart.verified_at is None


def test_stock_shortage_is_not_a_verified_cart() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    view_raw = fixture.catalog.model_dump()
    tofu = next(sku for sku in view_raw["skus"] if sku["sku"] == "G-TOFU200")
    tofu["stock_packs"] = 1
    tofu["stock_fact_ref"] = "fixture:stock/G-TOFU200@1pack"
    view = CatalogView.model_validate(view_raw)
    cart = api().build_cart(fixture.request, dishes, resolution, selected, view, AT)
    assert cart.cart_verification_status == "INFEASIBLE"
    assert "SKU_OUT_OF_STOCK" in {p["code"] for p in cart.problems}


def test_stock_expiry_is_independent_of_valid_price() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    at = datetime(2026, 11, 4, 6, 31, tzinfo=timezone.utc)
    cart = api().build_cart(fixture.request, dishes, resolution, selected, fixture.catalog, at)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "STOCK_EXPIRED" in {p["code"] for p in cart.problems}
    assert "PRICE_EXPIRED" not in {p["code"] for p in cart.problems}


def test_price_expiry_blocks_even_if_stock_was_newly_refreshed() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    at = datetime(2026, 11, 4, 8, 1, tzinfo=timezone.utc)
    cart = api().build_cart(fixture.request, dishes, resolution, selected, fixture.catalog, at)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "PRICE_EXPIRED" in {p["code"] for p in cart.problems}


def test_missing_selection_fails_closed_not_silently_purchased() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    reduced = replace(selected, selected_skus=selected.selected_skus[1:])
    cart = api().build_cart(fixture.request, dishes, resolution, reduced, fixture.catalog, AT)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "MISSING_SKU_SELECTION" in {p["code"] for p in cart.problems}


def test_no_allergy_clearance_claim_when_allergens_are_declared() -> None:
    fixture, dishes, resolution = golden()
    request = fixture.request.model_copy(update={"allergens": ["PEANUT"]})
    selected = selection_for(resolution, fixture.catalog)
    cart = api().build_cart(request, dishes, resolution, selected, fixture.catalog, AT)
    assert cart.cart_verification_status == "VERIFIED"
    assert cart.meal_allergen_status == "REVIEW_REQUIRED"
    assert cart.user_review_state == "DRAFT"


def test_wrong_store_is_not_a_verified_cart() -> None:
    fixture, dishes, resolution = golden()
    selected = selection_for(resolution, fixture.catalog)
    foreign = replace(selected, store_id="FG-02")
    cart = api().build_cart(fixture.request, dishes, resolution, foreign, fixture.catalog, AT)
    assert cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "STORE_MISMATCH" in {p["code"] for p in cart.problems}


def test_no_unbounded_number_of_candidate_selections() -> None:
    fixture, _, resolution = golden()
    view = fresh_view(alternative=True)
    candidates = api().propose_sku_selections(resolution.needs, view, limit=1)
    assert len(candidates) == 1
    assert any(s.sku == "G-TOM500-ALT" for s in candidates[0].selected_skus)
    assert api().propose_sku_selections(resolution.needs, view, limit=0) == []
