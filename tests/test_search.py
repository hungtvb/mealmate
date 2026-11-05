"""UC-01 Task 5: bounded, source-backed alternatives, no implicit acceptance."""
from dataclasses import replace
from datetime import datetime, timezone
from importlib import import_module

import pytest
from mealmate.cart_builder import propose_sku_selections, build_cart
from mealmate.fixtures import FixtureSources, load_fixture
from mealmate.models.catalog import AllergenAssessment, CatalogView, FoodSubjectRef
from mealmate.models.meal import PlannedDish, Recipe, RecipeIngredient
from mealmate.quantities import resolve_needs

AT = datetime(2026, 11, 4, 6, 12, tzinfo=timezone.utc)
BASE_AT = datetime(2026, 11, 4, 6, 10, tzinfo=timezone.utc)


def search_module():
    return import_module("mealmate.search")


def golden():
    bundle = load_fixture("F-UC01-POS")
    source = FixtureSources(bundle)
    dishes = [
        PlannedDish(recipe_id=r.recipe_id, recipe_version=r.version,
                    target_servings=4, serving_role=r.default_serving_role,
                    portion_rationale="curated role-specific source")
        for r in bundle.recipes
    ]
    needs = resolve_needs(bundle.request, dishes, source)
    choice = propose_sku_selections(needs.needs, bundle.catalog, 1)[0]
    return bundle, dishes, choice


def refreshed(bundle, snapshot_id, revision, updates, extra=None, allergens=()):
    """Versioned, coherent synthetic same-store catalog and current label subjects."""
    cat = bundle.catalog.model_dump()
    cat["snapshot"].update({
        "snapshot_id": snapshot_id, "source_revision": revision,
        "observed_at": "2026-11-04T06:11:00Z",
    })
    for row in cat["skus"]:
        row["catalog_snapshot_id"] = snapshot_id
        row["food_evidence_ref"] = {"kind": "sku", "parts": ["FG-01", row["sku"], snapshot_id]}
        row["price_fact_ref"] = f"fixture:price/{row['sku']}@{revision}"
        row["stock_fact_ref"] = f"fixture:stock/{row['sku']}@{revision}"
        row.update(updates.get(row["sku"], {}))
    for sku, original, changes in extra or []:
        row = next(row for row in cat["skus"] if row["sku"] == original).copy()
        row.update({"sku": sku, "catalog_snapshot_id": snapshot_id,
                    "food_evidence_ref": {"kind": "sku", "parts": ["FG-01", sku, snapshot_id]},
                    "price_fact_ref": f"fixture:price/{sku}@{revision}",
                    "stock_fact_ref": f"fixture:stock/{sku}@{revision}",
                    **changes})
        cat["skus"].append(row)
    view = CatalogView.model_validate(cat)
    originals = {e.subject_ref.parts[1]: e for e in bundle.evidence if e.subject_type == "sku"}
    alternative_origins = {sku: original for sku, original, _ in (extra or [])}
    new_evidence = []
    for product in view.skus:
        template = originals.get(product.sku) or originals[alternative_origins[product.sku]]
        new_evidence.append(template.model_copy(update={
            "evidence_id": f"FE-{snapshot_id}-{product.sku}",
            "subject_ref": product.food_evidence_ref,
            "evidence_revision": f"label-{revision}",
            "assessed_at": AT,
            "allergen_assessments": [
                AllergenAssessment(
                    allergen_id=a,
                    ingredient_presence="ABSENT",
                    cross_contact_status="ASSESSED_ABSENT",
                    assessment_scope="sku",
                    source_ref=f"fixture:label/{product.sku}@{revision}",
                    assessed_at=AT,
                ) for a in allergens
            ],
        }))
    evidence = [e for e in bundle.evidence if e.subject_type != "sku"] + new_evidence
    if allergens:
        evidence = [
            e if e.subject_type == "sku" else e.model_copy(update={
                "allergen_assessments": [
                    AllergenAssessment(
                        allergen_id=a, ingredient_presence="ABSENT",
                        cross_contact_status="ASSESSED_ABSENT",
                        assessment_scope=e.subject_type, source_ref=e.source_ref,
                        assessed_at=e.assessed_at,
                    ) for a in allergens
                ]
            })
            for e in evidence
        ]
    fresh = bundle.model_copy(update={"catalog": view, "evidence": evidence, "refreshed_evidence": []})
    return fresh


def invoke(bundle, preferred=None, *, limit=3, request=None, source=None):
    search = search_module()
    return search.search_candidates(
        request or bundle.request, source or FixtureSources(bundle), bundle.catalog,
        source or FixtureSources(bundle), preferred, AT, max_candidates=limit,
    )


def test_ac29_reprice_preserves_c01_original_then_offers_alt_c02() -> None:
    old, dishes, choice = golden()
    preferred = search_module().Candidate(dishes=dishes, selection=choice)
    changed = refreshed(
        old, "S-FG-005", "stock-price-v5",
        {"G-TOM500": {"price_vnd_per_pack": 50000}},
        extra=[("G-TOM500-ALT", "G-TOM500", {"price_vnd_per_pack": 22000, "stock_packs": 3})],
    )
    result = invoke(changed, preferred)
    assert len(result.attempts) == 2
    c01, c02 = result.attempts
    assert [a.candidate_id for a in result.attempts] == ["C01", "C02"]
    assert c01.cart.subtotal_vnd == 148000
    assert c01.cart.cart_verification_status == "INFEASIBLE"
    assert "BUDGET_EXCEEDED" in {p["code"] for p in c01.cart.problems}
    assert next(l.sku for l in c01.cart.lines if l.ingredient_id == "tomato") == "G-TOM500"
    assert c02.cart.cart_verification_status == "VERIFIED"
    assert (c02.cart.subtotal_vnd, len(c02.cart.lines), sum(l.packs for l in c02.cart.lines)) == (120000, 5, 6)
    assert next(l.sku for l in c02.cart.lines if l.ingredient_id == "tomato") == "G-TOM500-ALT"
    assert result.proposal is c02
    assert c02.cart.user_review_state == "DRAFT"
    assert c02.cart.request_revision == old.request.conversation_revision
    assert [a.cart.revision for a in result.attempts] == [1, 2]
    assert [a.cart.verification_basis["cart_revision"] for a in result.attempts] == [1, 2]


def test_ac30_out_of_stock_preferred_then_one_full_alt_tofu_pack() -> None:
    old, dishes, choice = golden()
    preferred = search_module().Candidate(dishes=dishes, selection=choice)
    changed = refreshed(
        old, "S-FG-004", "stock-price-v4",
        {"G-TOFU200": {"stock_packs": 1}},
        extra=[("G-TOFU400-ALT", "G-TOFU200", {
            "pack_quantity": 400, "price_vnd_per_pack": 27000, "stock_packs": 3,
        })],
    )
    result = invoke(changed, preferred)
    assert len(result.attempts) == 2
    assert result.attempts[0].cart.cart_verification_status == "INFEASIBLE"
    assert "SKU_OUT_OF_STOCK" in {p["code"] for p in result.attempts[0].cart.problems}
    assert next(l.sku for l in result.attempts[0].cart.lines if l.ingredient_id == "tofu") == "G-TOFU200"
    second = result.attempts[1]
    assert second.cart.cart_verification_status == "VERIFIED"
    assert (second.cart.subtotal_vnd, len(second.cart.lines), sum(l.packs for l in second.cart.lines)) == (119000, 5, 5)
    assert next(l.sku for l in second.cart.lines if l.ingredient_id == "tofu") == "G-TOFU400-ALT"
    assert result.proposal is second


def test_ac23_three_total_attempts_no_fourth_even_when_more_options(monkeypatch) -> None:
    old, dishes, choice = golden()
    changed = refreshed(
        old, "S-FG-005", "stock-price-v5",
        {"G-TOM500": {"price_vnd_per_pack": 50000}},
        extra=[
            ("G-TOM500-ALT", "G-TOM500", {"price_vnd_per_pack": 22000}),
            ("G-TOM500-ALT2", "G-TOM500", {"price_vnd_per_pack": 21000}),
            ("G-TOM500-ALT3", "G-TOM500", {"price_vnd_per_pack": 20000}),
        ],
    )
    search = search_module()
    original = search.build_cart
    seen = []
    failures = ["BUDGET_EXCEEDED", "SKU_OUT_OF_STOCK", "PRICE_EXPIRED"]

    def source_evaluator(*args):
        cart = original(*args)
        index = len(seen)
        seen.append(index)
        return cart.model_copy(update={
            "cart_verification_status": "DATA_UNAVAILABLE" if index == 2 else "INFEASIBLE",
            "problems": [{"code": failures[index]}],
            "verified_at": None,
        })

    monkeypatch.setattr(search, "build_cart", source_evaluator)
    result = invoke(changed, search.Candidate(dishes=dishes, selection=choice))
    assert seen == [0, 1, 2]
    assert [a.candidate_id for a in result.attempts] == ["C01", "C02", "C03"]
    assert result.proposal is None
    assert result.problem_code == "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET"


def test_allergy_ineligible_original_yields_evidence_backed_alt() -> None:
    old, dishes, choice = golden()
    changed = refreshed(
        old, "S-FG-003", "stock-price-v3", {},
        extra=[("G-TOM500-ALT", "G-TOM500", {"price_vnd_per_pack": 22000, "stock_packs": 3})],
        allergens=("PEANUT",),
    )
    records = []
    for evidence in changed.evidence:
        if evidence.subject_ref.kind == "sku" and evidence.subject_ref.parts[1] == "G-TOM500":
            records.append(evidence.model_copy(update={"allergen_assessments": []}))
        else:
            records.append(evidence)
    changed = changed.model_copy(update={"evidence": records})
    request = changed.request.model_copy(update={"allergens": ["PEANUT"]})
    prior = search_module().Candidate(dishes=dishes, selection=choice)
    result = invoke(changed, prior, request=request)
    assert len(result.attempts) == 2
    first, second = result.attempts
    assert first.cart.cart_verification_status == "VERIFIED"
    assert first.allergy.meal_allergen_status == "REVIEW_REQUIRED"
    assert first.allergy.acceptance_blocked
    assert second.cart.cart_verification_status == "VERIFIED"
    assert second.allergy.meal_allergen_status == "ASSESSED_NO_KNOWN_CONFLICT"
    assert second.allergy.acceptance_blocked is False
    assert first.cart.meal_allergen_status == first.allergy.meal_allergen_status
    assert second.cart.meal_allergen_status == second.allergy.meal_allergen_status
    assert second.cart.subtotal_vnd == 120000
    assert result.proposal is second
    assert result.proposal.cart.user_review_state == "DRAFT"


def test_all_economically_verified_but_allergy_ineligible_have_distinct_problem_code() -> None:
    old, dishes, choice = golden()
    changed = refreshed(old, "S-FG-003", "stock-price-v3", {}, allergens=("PEANUT",))
    changed = changed.model_copy(update={"evidence": [
        e.model_copy(update={"allergen_assessments": []})
        if e.subject_type == "sku" and e.subject_ref.parts[1] == "G-TOM500" else e
        for e in changed.evidence
    ]})
    prior = search_module().Candidate(dishes=dishes, selection=choice)
    request = changed.request.model_copy(update={"allergens": ["PEANUT"]})
    result = invoke(changed, prior, request=request)
    assert result.proposal is None
    assert result.attempts[0].cart.cart_verification_status == "VERIFIED"
    assert result.problem_code == "NO_ALLERGY_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET"


def test_fallback_can_discover_only_curated_new_recipe_with_same_serving_role() -> None:
    old, dishes, choice = golden()
    cheap_side = Recipe(
        recipe_id="R05", version="v1", title="Rau xanh đơn giản",
        base_servings=4, default_serving_role="side",
        ingredients=[RecipeIngredient(component_id="c01", ingredient_id="greens", quantity=100,
                                      unit="g", food_form="fresh_raw")],
        source_ref="fixture:recipe/R05@v1", data_completeness="COMPLETE",
    )
    updated = old.model_copy(update={"recipes": [*old.recipes, cheap_side]})
    req = updated.request.model_copy(update={"budget_vnd": 100000})
    search = search_module()
    result = invoke(updated, search.Candidate(dishes=dishes, selection=choice), request=req)
    assert result.proposal is not None
    assert result.proposal.cart.cart_verification_status == "VERIFIED"
    assert result.proposal.cart.subtotal_vnd == 92000
    assert result.proposal.candidate.dishes != dishes
    assert any(d.recipe_id == "R05" for d in result.proposal.candidate.dishes)
    assert all(d.recipe_id in {"R01", "R02", "R03", "R04", "R05"} for d in result.proposal.candidate.dishes)
    assert result.proposal.cart.user_review_state == "DRAFT"


def test_ac31_refuses_store_switch_when_previous_cart_selected_another_store() -> None:
    old, dishes, choice = golden()
    preferred = search_module().Candidate(
        dishes=dishes, selection=replace(choice, store_id="FG-02"),
    )
    result = invoke(old, preferred)
    assert result.proposal is None
    assert len(result.attempts) == 1
    assert result.attempts[0].cart.cart_verification_status == "DATA_UNAVAILABLE"
    assert "STORE_MISMATCH" in {p["code"] for p in result.attempts[0].cart.problems}


def test_search_never_mutates_an_accepted_cart() -> None:
    old, dishes, choice = golden()
    preferred = search_module().Candidate(
        dishes=dishes, selection=choice, user_review_state="ACCEPTED",
    )
    result = invoke(old, preferred)
    assert result.attempts == []
    assert result.proposal is None
    assert result.problem_code == "ACCEPTED_DRAFT_IMMUTABLE"


def test_zero_evaluation_budget_never_produces_fourth_candidate() -> None:
    old, dishes, choice = golden()
    preferred = search_module().Candidate(dishes=dishes, selection=choice)
    result = invoke(old, preferred, limit=0)
    assert result.attempts == []
    assert result.proposal is None
    assert result.problem_code == "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET"


def test_preferred_candidate_without_any_catalog_snapshot_compatible_sku_fails_closed() -> None:
    old, dishes, choice = golden()
    raw = old.catalog.model_dump()
    raw["skus"] = []
    empty = old.model_copy(update={"catalog": CatalogView.model_validate(raw)})
    result = invoke(empty, search_module().Candidate(dishes=dishes, selection=choice))
    assert result.proposal is None
    assert len(result.attempts) == 1
    assert result.attempts[0].cart.cart_verification_status == "DATA_UNAVAILABLE"


def test_first_verified_candidate_stops_without_evaluating_second() -> None:
    old, dishes, choice = golden()
    result = invoke(old, search_module().Candidate(dishes=dishes, selection=choice))
    assert len(result.attempts) == 1
    assert result.proposal is result.attempts[0]
    assert result.proposal.cart.subtotal_vnd == 116000
    assert result.proposal.cart.revision == 1


def test_no_preferred_uses_curated_main_recipe_from_source() -> None:
    old, _, _ = golden()
    result = invoke(old, None)
    assert result.proposal is not None
    assert len(result.proposal.candidate.dishes) >= 1
    assert all(d.recipe_id in {r.recipe_id for r in old.recipes} for d in result.proposal.candidate.dishes)
    assert all(d.target_servings == old.request.diners for d in result.proposal.candidate.dishes)
    assert result.proposal.cart.cart_verification_status == "VERIFIED"


def test_different_recipe_version_is_not_silently_swapped_by_sku_fallback() -> None:
    old, dishes, choice = golden()
    changed = refreshed(
        old, "S-FG-005", "stock-price-v5", {"G-TOM500": {"price_vnd_per_pack": 50000}},
        extra=[("G-TOM500-ALT", "G-TOM500", {"price_vnd_per_pack": 22000})]
    )
    result = invoke(changed, search_module().Candidate(dishes=dishes, selection=choice))
    assert result.proposal is not None
    assert [(d.recipe_id, d.recipe_version) for d in result.proposal.candidate.dishes] == [
        (d.recipe_id, d.recipe_version) for d in dishes
    ]
    assert result.proposal.cart.request_revision == old.request.conversation_revision


def test_preferred_recipe_filtered_out_by_source_cannot_be_proposed() -> None:
    old, dishes, choice = golden()

    class ExcludedRecipeSource(FixtureSources):
        def list_eligible(self, request, as_of):
            return [r for r in super().list_eligible(request, as_of) if r.recipe_id != "R02"]

    source = ExcludedRecipeSource(old)
    result = invoke(
        old, search_module().Candidate(dishes=dishes, selection=choice),
        source=source,
    )
    assert result.proposal is None
    assert len(result.attempts) >= 1
    assert result.attempts[0].cart.cart_verification_status == "INFEASIBLE"
    assert "RECIPE_NOT_ELIGIBLE" in {p["code"] for p in result.attempts[0].cart.problems}


def test_fallback_never_raises_the_customer_hard_budget() -> None:
    old, dishes, choice = golden()
    req = old.request.model_copy(update={"budget_vnd": 1000})
    result = invoke(old, search_module().Candidate(dishes=dishes, selection=choice), request=req)
    assert result.proposal is None
    assert 1 <= len(result.attempts) <= 3
    assert all(a.cart.budget_vnd == 1000 for a in result.attempts)
    assert all(a.cart.cart_verification_status != "VERIFIED" for a in result.attempts)


@pytest.mark.parametrize(
    "restriction",
    [{"dislikes": ["eggs"]}, {"dietary_restrictions": ["VEGAN"]}],
)
def test_synthetic_recipe_source_must_not_ignore_unverified_food_constraints(restriction) -> None:
    bundle, dishes, choice = golden()
    request = bundle.request.model_copy(update=restriction)
    result = invoke(bundle, search_module().Candidate(dishes=dishes, selection=choice), request=request)
    assert result.proposal is None
    assert result.attempts
    assert result.attempts[0].cart.cart_verification_status == "INFEASIBLE"
    assert "RECIPE_NOT_ELIGIBLE" in {p["code"] for p in result.attempts[0].cart.problems}
