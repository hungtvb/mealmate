"""UC-01 recipe/pantry arithmetic; expected quantities are copied from spec §11."""
from decimal import Decimal

import pytest

from mealmate.fixtures import FixtureSources, load_fixture
from mealmate.models.meal import PantryItem, PlannedDish
from mealmate.quantities import RecipeCoverageError, UnitConversionMissing, resolve_needs


def sample():
    src = FixtureSources(load_fixture("F-UC01-POS"))
    dishes = [PlannedDish(recipe_id=r.recipe_id, recipe_version=r.version, target_servings=4,
                          serving_role=r.default_serving_role, portion_rationale="curated role-specific 4 portions")
              for r in src.bundle.recipes]
    return src, dishes


def find_need(resolution, ingredient):
    return next(n for n in resolution.needs if n.ingredient_id == ingredient)


def test_ac12_aggregate_before_rounding() -> None:
    source, dishes = sample()
    result = resolve_needs(source.request, dishes, source)
    tomato = find_need(result, "tomato")
    assert (tomato.required_qty, tomato.confirmed_pantry_qty, tomato.buy_qty) == (Decimal(500), Decimal(100), Decimal(400))
    assert {(c.recipe_id, c.recipe_version, c.component_id, c.quantity) for c in result.recipe_component_uses if c.ingredient_id == "tomato"} == {
        ("R02", "v1", "c02", Decimal(300)), ("R03", "v1", "c01", Decimal(200))}
    assert len(result.recipe_component_uses) == 10
    assert {n.ingredient_id for n in result.needs if n.buy_qty > 0} == {"eggs", "tomato", "oil", "tofu", "greens"}
    assert (find_need(result, "rice").buy_qty, find_need(result, "water").buy_qty) == (0, 0)


def test_two_pantry_packages_distinct_evidence_trace() -> None:
    source, dishes = sample()
    original = source.request.pantry
    one = original[1].model_copy(update={"quantity": Decimal(250)})
    two = one.model_copy(update={"pantry_item_id": "P04", "food_evidence_ref": "FE-P04"})
    request = source.request.model_copy(update={"pantry": [original[0], one, two, original[2]]})
    result = resolve_needs(request, dishes, source)
    tomato = find_need(result, "tomato")
    assert (tomato.required_qty, tomato.confirmed_pantry_qty, tomato.buy_qty) == (500, 500, 0)
    selected = [a for a in result.pantry_allocations if a.ingredient_id == "tomato"]
    assert [(a.pantry_item_id, a.quantity, a.food_evidence_ref) for a in selected] == [
        ("P02", Decimal(250), "FE-P02"), ("P04", Decimal(250), "FE-P04")]
    assert [a.subject_ref.parts for a in selected] == [("REQ-001", "P02"), ("REQ-001", "P04")]


def test_ac26_side_serving_edit() -> None:
    source, dishes = sample()
    dishes[-1] = dishes[-1].model_copy(update={"target_servings": Decimal(6)})
    result = resolve_needs(source.request, dishes, source)
    assert find_need(result, "greens").required_qty == Decimal(600)
    assert find_need(result, "water").required_qty == Decimal(2600)
    assert find_need(result, "water").confirmed_pantry_qty == Decimal(2600)
    assert find_need(result, "water").buy_qty == 0
    water_allocations = [x for x in result.pantry_allocations if x.ingredient_id == "water"]
    assert [(a.pantry_item_id, a.quantity) for a in water_allocations] == [("P03", Decimal(2600))]


def test_ac11_unknown_raw_cooked_conversion() -> None:
    source, dishes = sample()
    raw_rice = source.request.pantry[0]
    cooked_rice = raw_rice.model_copy(update={"food_form": "cooked"})
    changed = source.request.model_copy(update={"pantry": [cooked_rice, *source.request.pantry[1:]]})
    with pytest.raises(UnitConversionMissing):
        resolve_needs(changed, dishes, source)


def test_unconfirmed_pantry_is_not_deducted() -> None:
    source, dishes = sample()
    unknown = source.request.pantry[1].model_copy(update={"quantity_confirmed": False})
    changed = source.request.model_copy(update={"pantry": [source.request.pantry[0], unknown, source.request.pantry[2]]})
    result = resolve_needs(changed, dishes, source)
    assert find_need(result, "tomato").buy_qty == Decimal(500)
    assert "P02" not in {p.pantry_item_id for p in result.pantry_allocations}


def test_missing_versioned_recipe_cannot_be_invented() -> None:
    source, dishes = sample()
    dishes[0] = dishes[0].model_copy(update={"recipe_version": "v9"})
    with pytest.raises(RecipeCoverageError):
        resolve_needs(source.request, dishes, source)
