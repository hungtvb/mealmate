"""Catalog and food-evidence records, without claiming any provider is live."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from .meal import SourceModel


class FoodSubjectRef(SourceModel):
    kind: Literal["recipe_component", "sku", "pantry_item"]
    parts: tuple[str, ...]

    @model_validator(mode="after")
    def parts_match_subject(self):
        expected = 3 if self.kind in ("recipe_component", "sku") else 2
        if len(self.parts) != expected or not all(part for part in self.parts):
            raise ValueError(f"{self.kind} subject requires {expected} nonempty components")
        return self

    @property
    def key(self) -> str:
        return "/".join(self.parts)


class FoodEvidence(SourceModel):
    evidence_id: str = Field(min_length=1)
    subject_type: Literal["recipe_component", "sku", "pantry_item"]
    subject_ref: FoodSubjectRef
    ingredient_statement: str | None
    allergen_assessments: list[dict]
    source_ref: str = Field(min_length=1)
    evidence_revision: str = Field(min_length=1)
    assessed_at: datetime

    @model_validator(mode="after")
    def typed_subject_matches(self):
        if self.subject_type != self.subject_ref.kind:
            raise ValueError("subject type and typed reference disagree")
        return self


class ProductSKU(SourceModel):
    sku: str = Field(min_length=1)
    ingredient_id: str = Field(min_length=1)
    food_form: str = Field(min_length=1)
    pack_quantity: Decimal = Field(gt=0)
    pack_unit: Literal["g", "ml", "pcs"]
    price_vnd_per_pack: int = Field(ge=0)
    stock_packs: int = Field(ge=0)
    catalog_snapshot_id: str = Field(min_length=1)
    food_evidence_ref: FoodSubjectRef
    source_ref: str = Field(min_length=1)
    price_fact_ref: str = Field(min_length=1)
    stock_fact_ref: str = Field(min_length=1)


class CatalogSnapshot(SourceModel):
    snapshot_id: str = Field(min_length=1)
    store_id: str = Field(min_length=1)
    observed_at: datetime
    price_valid_until: datetime
    stock_valid_until: datetime
    source_ref: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_intervals(self):
        dates = (self.observed_at, self.price_valid_until, self.stock_valid_until)
        if any(d.tzinfo is None or d.utcoffset() is None for d in dates):
            raise ValueError("snapshot timestamps must be timezone aware")
        if self.observed_at >= self.price_valid_until or self.observed_at >= self.stock_valid_until:
            raise ValueError("snapshot facts must expire after observation")
        return self


class CatalogView(SourceModel):
    snapshot: CatalogSnapshot
    skus: list[ProductSKU]

    @model_validator(mode="after")
    def consistent_source(self):
        if len({s.sku for s in self.skus}) != len(self.skus):
            raise ValueError("duplicate SKU rows in catalog view")
        if any(s.catalog_snapshot_id != self.snapshot.snapshot_id for s in self.skus):
            raise ValueError("SKU row is not part of catalog snapshot")
        if any(s.food_evidence_ref.parts[:1] != (self.snapshot.store_id,) for s in self.skus):
            raise ValueError("SKU evidence store must match snapshot store")
        return self


class CatalogRefreshResult(SourceModel):
    view: CatalogView | None
    attested_carried_price_refs: dict[str, str]
    attestation_ref: str | None
    problem_code: str | None

    @model_validator(mode="after")
    def coherent_refresh_result(self):
        if self.view is None and self.attested_carried_price_refs:
            raise ValueError("failed refresh cannot attest price facts")
        if self.view is not None:
            if not self.attestation_ref or self.problem_code:
                raise ValueError("refresh needs source attestation and no problem")
            found = {sku.sku for sku in self.view.skus}
            if not set(self.attested_carried_price_refs).issubset(found):
                raise ValueError("attestation refers to absent SKU")
        return self
