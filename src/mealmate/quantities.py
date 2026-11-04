"""Deterministic meal demand and traceable pantry allocation (no SKU rounding)."""
from dataclasses import dataclass
from decimal import Decimal

from .models.catalog import FoodSubjectRef
from .models.meal import MealRequest, PlannedDish
from .ports import RecipeSource


class RecipeCoverageError(ValueError):
    """The requested versioned curated recipe cannot support a verified cart."""


class UnitConversionMissing(ValueError):
    """A required ingredient needs a food-form or unit conversion without evidence."""


@dataclass(frozen=True)
class IngredientNeed:
    ingredient_id: str
    food_form: str
    unit: str
    required_qty: Decimal
    confirmed_pantry_qty: Decimal
    buy_qty: Decimal


@dataclass(frozen=True)
class RecipeComponentUse:
    recipe_id: str
    recipe_version: str
    component_id: str
    ingredient_id: str
    food_form: str
    unit: str
    quantity: Decimal
    source_ref: str
    subject_ref: FoodSubjectRef


@dataclass(frozen=True)
class PantryAllocation:
    request_id: str
    pantry_item_id: str
    ingredient_id: str
    food_form: str
    unit: str
    quantity: Decimal
    food_evidence_ref: str | None
    subject_ref: FoodSubjectRef


@dataclass(frozen=True)
class NeedsResolution:
    needs: list[IngredientNeed]
    recipe_component_uses: list[RecipeComponentUse]
    pantry_allocations: list[PantryAllocation]


def resolve_needs(request: MealRequest, dishes: list[PlannedDish], recipes: RecipeSource) -> NeedsResolution:
    """Scale sourced ingredients, aggregate first, then deduct each confirmed pantry item.

    Only identity/form/unit-exact matches are supported. Any plausible but
    unapproved conversion is rejected rather than guessing a yield factor.
    """
    totals: dict[tuple[str, str, str], Decimal] = {}
    components: list[RecipeComponentUse] = []
    for dish in dishes:
        recipe = recipes.get(dish.recipe_id, dish.recipe_version)
        if recipe is None or recipe.data_completeness != "COMPLETE":
            raise RecipeCoverageError(f"Missing complete recipe: {dish.recipe_id}@{dish.recipe_version}")
        if dish.serving_role != recipe.default_serving_role:
            raise RecipeCoverageError(f"Unverified serving role: {dish.recipe_id}")
        factor = dish.target_servings / Decimal(recipe.base_servings)
        for ingredient in recipe.ingredients:
            amount = ingredient.quantity * factor
            key = (ingredient.ingredient_id, ingredient.food_form, ingredient.unit)
            totals[key] = totals.get(key, Decimal(0)) + amount
            components.append(RecipeComponentUse(
                recipe_id=recipe.recipe_id, recipe_version=recipe.version,
                component_id=ingredient.component_id, ingredient_id=ingredient.ingredient_id,
                food_form=ingredient.food_form, unit=ingredient.unit, quantity=amount,
                source_ref=recipe.source_ref,
                subject_ref=FoodSubjectRef(kind="recipe_component", parts=(recipe.recipe_id, recipe.version, ingredient.component_id)),
            ))
    remaining = totals.copy()
    allocations: list[PantryAllocation] = []
    for pantry in request.pantry:
        if not pantry.quantity_confirmed:
            continue
        matches = [key for key in totals if key[0] == pantry.ingredient_id]
        if not matches:
            continue
        key = (pantry.ingredient_id, pantry.food_form, pantry.unit)
        if key not in matches:
            raise UnitConversionMissing(f"No sourced conversion for {pantry.ingredient_id}/{pantry.food_form}/{pantry.unit}")
        amount = min(pantry.quantity, remaining[key])
        if amount <= 0:
            continue
        remaining[key] -= amount
        allocations.append(PantryAllocation(
            request_id=request.request_id, pantry_item_id=pantry.pantry_item_id,
            ingredient_id=pantry.ingredient_id, food_form=pantry.food_form, unit=pantry.unit,
            quantity=amount, food_evidence_ref=pantry.food_evidence_ref,
            subject_ref=FoodSubjectRef(kind="pantry_item", parts=(request.request_id, pantry.pantry_item_id)),
        ))
    needs = [IngredientNeed(ingredient_id=key[0], food_form=key[1], unit=key[2],
                             required_qty=total, confirmed_pantry_qty=total - remaining[key],
                             buy_qty=remaining[key]) for key, total in totals.items()]
    return NeedsResolution(needs=needs, recipe_component_uses=components, pantry_allocations=allocations)
