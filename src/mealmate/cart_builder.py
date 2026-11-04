"""Deterministic candidate SKU enumeration and explicit cart-data verification.

The proposer may suggest catalog-backed alternatives. The verifier never switches
a shopper's selected SKU, never merges sources, and does not assess allergens.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from heapq import heappop, heappush
from itertools import count
from uuid import uuid4

from .models.cart import CartLine, DraftCart
from .models.catalog import CatalogView, ProductSKU
from .models.meal import MealRequest, PlannedDish
from .quantities import IngredientNeed, NeedsResolution

NeedKey = tuple[str, str, str]


@dataclass(frozen=True)
class SkuAssignment:
    ingredient_id: str
    food_form: str
    unit: str
    sku: str

    @property
    def need_key(self) -> NeedKey:
        return self.ingredient_id, self.food_form, self.unit


@dataclass(frozen=True)
class SkuSelection:
    store_id: str
    snapshot_id: str
    selected_skus: tuple[SkuAssignment, ...]


def _key(need: IngredientNeed) -> NeedKey:
    return need.ingredient_id, need.food_form, need.unit


def _pack_count(quantity: Decimal, pack_quantity: Decimal) -> int:
    return int((quantity / pack_quantity).to_integral_value(rounding=ROUND_CEILING))


def propose_sku_selections(
    needs: list[IngredientNeed], catalog: CatalogView, limit: int
) -> list[SkuSelection]:
    """Enumerate up to limit exact-form same-snapshot combinations by whole-pack cost.

    This enumerates sourced SKU selections, not validated carts. Inventory and
    freshness are independently checked by build_cart; an unavailable original
    selection must remain visible to the later bounded candidate search.
    """
    if limit <= 0:
        return []
    pending = [n for n in needs if n.buy_qty > 0]
    if len({_key(n) for n in pending}) != len(pending):
        return []
    choices: list[list[ProductSKU]] = []
    for need in pending:
        options = [
            sku for sku in catalog.skus
            if (sku.ingredient_id, sku.food_form, sku.pack_unit) == _key(need)
            and sku.catalog_snapshot_id == catalog.snapshot.snapshot_id
        ]
        if not options:
            return []
        choices.append(sorted(
            options,
            key=lambda sku: (
                _pack_count(need.buy_qty, sku.pack_quantity) * sku.price_vnd_per_pack,
                sku.sku,
            ),
        ))

    def cost(indices: tuple[int, ...]) -> int:
        return sum(
            _pack_count(need.buy_qty, choices[i][index].pack_quantity)
            * choices[i][index].price_vnd_per_pack
            for i, (need, index) in enumerate(zip(pending, indices))
        )

    start = (0,) * len(choices)
    pending_heap: list[tuple[int, tuple[int, ...]]] = [(cost(start), start)]
    visited = {start}
    results: list[SkuSelection] = []
    while pending_heap and len(results) < limit:
        _, indices = heappop(pending_heap)
        results.append(SkuSelection(
            store_id=catalog.snapshot.store_id,
            snapshot_id=catalog.snapshot.snapshot_id,
            selected_skus=tuple(
                SkuAssignment(n.ingredient_id, n.food_form, n.unit, choices[i][j].sku)
                for i, (n, j) in enumerate(zip(pending, indices))
            ),
        ))
        for i, j in enumerate(indices):
            if j + 1 >= len(choices[i]):
                continue
            neighbor = indices[:i] + (j + 1,) + indices[i + 1:]
            if neighbor not in visited:
                visited.add(neighbor)
                heappush(pending_heap, (cost(neighbor), neighbor))
    return results


def build_cart(
    request: MealRequest,
    dishes: list[PlannedDish],
    resolution: NeedsResolution,
    selected: SkuSelection,
    catalog: CatalogView,
    as_of: datetime,
) -> DraftCart:
    """Verify exactly selected SKUs against one source-attested catalog view.

    This is economic verification only. Allergy suitability and user acceptance
    are separate, later gates; no checkout, reservation or substitution occurs.
    """
    view = catalog.snapshot
    problems: list[dict[str, str]] = []
    data_codes: set[str] = set()
    lines: list[CartLine] = []
    facts: list[dict] = []

    def issue(code: str, *, category: str = "INFEASIBLE", **fields: str) -> None:
        problems.append({"code": code, **fields})
        if category == "DATA_UNAVAILABLE":
            data_codes.add(code)

    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        issue("INVALID_TIME", category="DATA_UNAVAILABLE")
    if selected.store_id != view.store_id:
        issue("STORE_MISMATCH", category="DATA_UNAVAILABLE")
    if selected.snapshot_id != view.snapshot_id:
        issue("SNAPSHOT_MISMATCH", category="DATA_UNAVAILABLE")
    if as_of.tzinfo is not None and as_of.utcoffset() == timedelta(0):
        if view.observed_at > as_of:
            issue("SNAPSHOT_NOT_YET_OBSERVED", category="DATA_UNAVAILABLE")
        if as_of >= view.price_valid_until:
            issue("PRICE_EXPIRED", category="DATA_UNAVAILABLE")
        if as_of >= view.stock_valid_until:
            issue("STOCK_EXPIRED", category="DATA_UNAVAILABLE")

    if not problems:
        sku_by_id = {sku.sku: sku for sku in catalog.skus}
        needed = [need for need in resolution.needs if need.buy_qty > 0]
        needed_keys = {_key(n) for n in needed}
        mapping: dict[NeedKey, str] = {}
        seen_skus: dict[str, NeedKey] = {}

        if len(needed_keys) != len(needed):
            issue("DUPLICATE_INGREDIENT_NEED")
        for assignment in selected.selected_skus:
            key = assignment.need_key
            if key in mapping:
                issue("DUPLICATE_SKU_SELECTION", ingredient_id=assignment.ingredient_id)
            if key not in needed_keys:
                issue("UNEXPECTED_SKU_SELECTION", ingredient_id=assignment.ingredient_id)
            existing = seen_skus.get(assignment.sku)
            if existing is not None and existing != key:
                issue("SKU_REUSED_FOR_DIFFERENT_INGREDIENT", sku=assignment.sku)
            seen_skus[assignment.sku] = key
            mapping[key] = assignment.sku

        for need in needed:
            key = _key(need)
            if not (
                need.required_qty >= 0
                and need.confirmed_pantry_qty >= 0
                and need.buy_qty > 0
                and need.required_qty == need.confirmed_pantry_qty + need.buy_qty
            ):
                issue("INVALID_QUANTITY_RESOLUTION", ingredient_id=need.ingredient_id)
                continue
            chosen_sku = mapping.get(key)
            if chosen_sku is None:
                issue("MISSING_SKU_SELECTION", category="DATA_UNAVAILABLE", ingredient_id=need.ingredient_id)
                continue
            sku = sku_by_id.get(chosen_sku)
            if sku is None:
                issue("SKU_NOT_FOUND", category="DATA_UNAVAILABLE", sku=chosen_sku)
                continue
            if (
                (sku.ingredient_id, sku.food_form, sku.pack_unit) != key
                or sku.catalog_snapshot_id != view.snapshot_id
                or need.unit not in ("g", "ml", "pcs")
            ):
                issue("SKU_INCOMPATIBLE", sku=chosen_sku, ingredient_id=need.ingredient_id)
                continue
            packs = _pack_count(need.buy_qty, sku.pack_quantity)
            if packs > sku.stock_packs:
                issue("SKU_OUT_OF_STOCK", sku=chosen_sku)
            line_total = packs * sku.price_vnd_per_pack
            lines.append(CartLine(
                ingredient_id=need.ingredient_id,
                required_qty=need.required_qty,
                confirmed_pantry_qty=need.confirmed_pantry_qty,
                buy_qty=need.buy_qty,
                unit=sku.pack_unit,
                unused_qty=Decimal(packs) * sku.pack_quantity - need.buy_qty,
                sku=sku.sku,
                packs=packs,
                price_per_pack_vnd=sku.price_vnd_per_pack,
                line_total_vnd=line_total,
                source_refs=list(dict.fromkeys((
                    view.source_ref, sku.source_ref, sku.price_fact_ref, sku.stock_fact_ref,
                ))),
            ))
            facts.append({
                "sku": sku.sku,
                "price_fact_ref": sku.price_fact_ref,
                "stock_fact_ref": sku.stock_fact_ref,
                "food_subject_ref": sku.food_evidence_ref.model_dump(),
            })

    subtotal = sum(line.line_total_vnd for line in lines)
    if not data_codes and subtotal > request.budget_vnd:
        issue("BUDGET_EXCEEDED")

    status = (
        "DATA_UNAVAILABLE" if data_codes
        else "INFEASIBLE" if problems
        else "VERIFIED"
    )
    revision = 1
    return DraftCart(
        cart_id=f"cart-{uuid4().hex}",
        revision=revision,
        request_revision=request.conversation_revision,
        planned_dishes=list(dishes),
        lines=lines,
        subtotal_vnd=subtotal,
        budget_vnd=request.budget_vnd,
        snapshot_id=view.snapshot_id,
        verified_at=as_of if status == "VERIFIED" else None,
        verification_basis={
            "request_revision": request.conversation_revision,
            "cart_revision": revision,
            "store_id": view.store_id,
            "snapshot_id": view.snapshot_id,
            "catalog_source_revision": view.source_revision,
            "selected_recipe_versions": [
                {"recipe_id": d.recipe_id, "version": d.recipe_version}
                for d in dishes
            ],
            "selected_sku_facts": facts,
            "selected_food_evidence_revisions": [],  # Task 4 populates after assessment
        },
        cart_verification_status=status,
        meal_allergen_status="REVIEW_REQUIRED" if request.allergens else "NOT_ASSESSED",
        problems=problems,
        user_review_state="DRAFT",
        accepted_at=None,
    )
