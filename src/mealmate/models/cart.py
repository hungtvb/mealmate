"""Typed shopping draft; pack economics are verified before acceptance."""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .meal import SourceModel, PlannedDish


class CartLine(SourceModel):
    ingredient_id: str
    required_qty: Decimal = Field(ge=0)
    confirmed_pantry_qty: Decimal = Field(ge=0)
    buy_qty: Decimal = Field(ge=0)
    unit: Literal["g", "ml", "pcs"]
    unused_qty: Decimal = Field(ge=0)
    sku: str
    packs: int = Field(gt=0)
    price_per_pack_vnd: int = Field(ge=0)
    line_total_vnd: int = Field(ge=0)
    source_refs: list[str]


class DraftCart(SourceModel):
    cart_id: str
    revision: int = Field(ge=1)
    request_revision: int = Field(ge=1)
    planned_dishes: list[PlannedDish]
    lines: list[CartLine]
    subtotal_vnd: int = Field(ge=0)
    budget_vnd: int = Field(gt=0)
    snapshot_id: str
    verified_at: datetime | None
    verification_basis: dict
    cart_verification_status: Literal["VERIFIED", "INFEASIBLE", "DATA_UNAVAILABLE"]
    meal_allergen_status: Literal["NOT_ASSESSED", "ASSESSED_NO_KNOWN_CONFLICT", "REVIEW_REQUIRED", "KNOWN_CONFLICT"]
    problems: list[dict]
    user_review_state: Literal["DRAFT", "ACCEPTED", "REJECTED"]
    accepted_at: datetime | None = None
