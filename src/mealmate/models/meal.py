"""Curated recipes and the current explicit customer request."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PantryItem(SourceModel):
    pantry_item_id: str = Field(min_length=1)
    ingredient_id: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit: Literal["g", "ml", "pcs"]
    food_form: str = Field(min_length=1)
    quantity_confirmed: bool
    food_evidence_ref: str | None = None


class MealRequest(SourceModel):
    request_id: str = Field(min_length=1)
    conversation_revision: int = Field(ge=1)
    diners: int = Field(gt=0)
    meal_type: str = Field(min_length=1)
    budget_vnd: int = Field(gt=0)
    dislikes: list[str]
    allergens: list[str]
    dietary_restrictions: list[str]
    pantry: list[PantryItem]

    @model_validator(mode="after")
    def unique_pantry_items(self):
        ids = [item.pantry_item_id for item in self.pantry]
        if len(set(ids)) != len(ids):
            raise ValueError("pantry_item_id must be unique per request")
        return self


class RecipeIngredient(SourceModel):
    component_id: str = Field(min_length=1)
    ingredient_id: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit: Literal["g", "ml", "pcs"]
    food_form: str = Field(min_length=1)


class Recipe(SourceModel):
    recipe_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    base_servings: int = Field(gt=0)
    default_serving_role: Literal["main", "side", "shared"]
    ingredients: list[RecipeIngredient] = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    data_completeness: Literal["COMPLETE", "INCOMPLETE"]

    @model_validator(mode="after")
    def unique_components(self):
        ids = [ingredient.component_id for ingredient in self.ingredients]
        if len(set(ids)) != len(ids):
            raise ValueError("component_id must be unique within recipe version")
        return self


class PlannedDish(SourceModel):
    recipe_id: str = Field(min_length=1)
    recipe_version: str = Field(min_length=1)
    target_servings: Decimal = Field(gt=0)
    serving_role: Literal["main", "side", "shared"]
    portion_rationale: str = Field(min_length=1)
