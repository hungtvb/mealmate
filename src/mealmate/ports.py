"""Minimal provider boundaries, backed by synthetic adapters in Task 1."""
from datetime import datetime
from typing import Literal, Protocol

from .models.catalog import CatalogRefreshResult, CatalogView, FoodEvidence, FoodSubjectRef
from .models.meal import MealRequest, Recipe


class RecipeSource(Protocol):
    def get(self, recipe_id: str, version: str) -> Recipe | None: ...
    def list_eligible(self, request: MealRequest, as_of: datetime) -> list[Recipe]: ...
    def current_version(self, recipe_id: str, as_of: datetime) -> str | None: ...


class CatalogSource(Protocol):
    def get_view(self, store_id: str, as_of: datetime) -> CatalogView | None: ...
    def refresh_view(self, store_id: str, previous: CatalogView, expired_facts: Literal["PRICE", "STOCK", "BOTH"], as_of: datetime) -> CatalogRefreshResult: ...


class EvidenceSource(Protocol):
    def current_for_subject(self, subject_ref: FoodSubjectRef, as_of: datetime) -> FoodEvidence | None: ...
