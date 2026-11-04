"""Strict read-only synthetic sources for UC-01 test scenarios.

This module does not connect to an authoritative retailer. Synthetic fixture
refresh attestation is meaningful only for deterministic tests.
"""
from datetime import datetime
import json
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models.catalog import CatalogRefreshResult, CatalogView, FoodEvidence, FoodSubjectRef
from .models.meal import MealRequest, Recipe


class FixtureBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: str = Field(min_length=1)
    request: MealRequest
    recipes: list[Recipe]
    catalog: CatalogView
    evidence: list[FoodEvidence]
    refresh_result: CatalogRefreshResult
    refreshed_evidence: list[FoodEvidence]

    @model_validator(mode="after")
    def validate_fixture_cohesion(self):
        refs = [(e.subject_type,e.subject_ref.key) for e in self.evidence]
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate FoodEvidence subject references")
        if self.refresh_result.view is not None:
            new = self.refresh_result.view
            if new.snapshot.store_id != self.catalog.snapshot.store_id:
                raise ValueError("refresh must stay in selected store")
            if new.snapshot.snapshot_id == self.catalog.snapshot.snapshot_id:
                raise ValueError("refresh must emit new snapshot ID")
        return self


def load_fixture(fixture_id: str) -> FixtureBundle:
    fixture_path = files("mealmate").joinpath("data", "uc01_golden.json")
    source = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture_id == source["base"]["fixture_id"]:
        return FixtureBundle.model_validate(source["base"])
    variant = source["variants"].get(fixture_id)
    if variant is None:
        raise ValueError(f"Unknown synthetic UC-01 fixture: {fixture_id}")
    return FixtureBundle.model_validate({**source["base"], **variant, "fixture_id": fixture_id})


class FixtureSources:
    """Combine three source protocols for one explicitly synthetic fixture."""
    def __init__(self, bundle: FixtureBundle):
        self.bundle = bundle
        self.request = bundle.request

    def get(self, recipe_id: str, version: str) -> Recipe | None:
        return next((r for r in self.bundle.recipes if r.recipe_id == recipe_id and r.version == version), None)

    def list_eligible(self, request: MealRequest, as_of: datetime) -> list[Recipe]:
        return [r for r in self.bundle.recipes if r.data_completeness == "COMPLETE"]

    def current_version(self, recipe_id: str, as_of: datetime) -> str | None:
        return next((r.version for r in self.bundle.recipes if r.recipe_id == recipe_id), None)

    def get_view(self, store_id: str, as_of: datetime) -> CatalogView | None:
        return self.bundle.catalog if self.bundle.catalog.snapshot.store_id == store_id else None

    def refresh_view(self, store_id: str, previous: CatalogView, expired_facts: Literal["PRICE", "STOCK", "BOTH"], as_of: datetime) -> CatalogRefreshResult:
        if previous.snapshot.store_id != store_id or previous.snapshot.snapshot_id != self.bundle.catalog.snapshot.snapshot_id:
            return CatalogRefreshResult(view=None, attested_carried_price_refs={}, attestation_ref=None, problem_code="SOURCE_MISMATCH")
        result = self.bundle.refresh_result
        if result.view is None:
            return result
        if result.view.snapshot.observed_at > as_of or result.view.snapshot.stock_valid_until <= as_of or result.view.snapshot.price_valid_until <= as_of:
            return CatalogRefreshResult(view=None, attested_carried_price_refs={}, attestation_ref=None, problem_code="STALE_REFRESH")
        if expired_facts == "STOCK":
            # A carried price must retain the source fact, value, and deadline.
            if (previous.snapshot.price_valid_until <= as_of
                    or result.view.snapshot.price_valid_until > previous.snapshot.price_valid_until):
                return CatalogRefreshResult(view=None, attested_carried_price_refs={}, attestation_ref=None, problem_code="INCOMPATIBLE_PRICE_PROVENANCE")
            old = {sku.sku: sku for sku in previous.skus}
            for sku in result.view.skus:
                prior = old.get(sku.sku)
                if (prior is None
                        or result.attested_carried_price_refs.get(sku.sku) != prior.price_fact_ref
                        or sku.price_fact_ref != prior.price_fact_ref
                        or sku.price_vnd_per_pack != prior.price_vnd_per_pack):
                    return CatalogRefreshResult(view=None, attested_carried_price_refs={}, attestation_ref=None, problem_code="INCOMPATIBLE_PRICE_PROVENANCE")
        return result

    def current_for_subject(self, subject_ref: FoodSubjectRef, as_of: datetime) -> FoodEvidence | None:
        eligible = [e for e in (*self.bundle.evidence, *self.bundle.refreshed_evidence)
                    if e.subject_type == subject_ref.kind and e.subject_ref == subject_ref and e.assessed_at <= as_of]
        if not eligible:
            return None
        latest_time = max(e.assessed_at for e in eligible)
        latest = [e for e in eligible if e.assessed_at == latest_time]
        # Conflicting equally-current records cannot be safely ranked by revision strings.
        if len({e.model_dump_json() for e in latest}) != 1:
            return None
        return latest[0]
