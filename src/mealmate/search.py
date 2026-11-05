"""Bounded, evidence-backed search of draft UC-01 cart candidates.

The previous draft's exact SKU IDs are reverified first against one new
source snapshot. New SKU/recipe options are separate, unaccepted drafts.
No LLM creates source facts and no accepted cart is ever changed here.
"""
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_CEILING
from typing import Literal

from .allergens import AllergyAssessment, assess_allergens
from .cart_builder import SkuSelection, build_cart, propose_sku_selections
from .models.cart import DraftCart
from .models.catalog import CatalogView
from .models.meal import MealRequest, PlannedDish
from .ports import EvidenceSource, RecipeSource
from .quantities import RecipeCoverageError, UnitConversionMissing, resolve_needs


@dataclass(frozen=True)
class Candidate:
    dishes: list[PlannedDish]
    selection: SkuSelection
    user_review_state: Literal["DRAFT", "ACCEPTED", "REJECTED"] = "DRAFT"


@dataclass(frozen=True)
class CandidateAttempt:
    candidate_id: str
    candidate: Candidate
    cart: DraftCart
    allergy: AllergyAssessment | None


@dataclass(frozen=True)
class SearchResult:
    attempts: list[CandidateAttempt]
    proposal: CandidateAttempt | None
    problem_code: str | None


def _identity(candidate: Candidate) -> tuple:
    """A SKU/recipe identity is separate from the mutable snapshot revision."""
    dishes = tuple(
        (d.recipe_id, d.recipe_version, d.serving_role, d.target_servings)
        for d in candidate.dishes
    )
    skus = tuple(sorted(
        (a.ingredient_id, a.food_form, a.unit, a.sku)
        for a in candidate.selection.selected_skus
    ))
    return dishes, skus


def _price_rank(candidate: Candidate, catalog: CatalogView, request: MealRequest, recipes: RecipeSource) -> int | None:
    """Source-backed whole-pack price for ordering alternatives, not verification."""
    try:
        needs = resolve_needs(request, candidate.dishes, recipes).needs
    except (RecipeCoverageError, UnitConversionMissing):
        return None
    by_key = {
        (n.ingredient_id, n.food_form, n.unit): n
        for n in needs if n.buy_qty > 0
    }
    catalog_skus = {sku.sku: sku for sku in catalog.skus}
    if len(candidate.selection.selected_skus) != len(by_key):
        return None
    cost = 0
    for assignment in candidate.selection.selected_skus:
        key = assignment.need_key
        sku = catalog_skus.get(assignment.sku)
        need = by_key.get(key)
        if (need is None or sku is None
                or (sku.ingredient_id, sku.food_form, sku.pack_unit) != key):
            return None
        packs = int((need.buy_qty / sku.pack_quantity).to_integral_value(rounding=ROUND_CEILING))
        cost += packs * sku.price_vnd_per_pack
    return cost


def _make_menu_candidates(
    request: MealRequest,
    dishes: list[PlannedDish],
    recipes: RecipeSource,
    catalog: CatalogView,
    eligible: list,
) -> list[Candidate]:
    """Swap one sourced recipe within the same serving role; never invent a menu."""
    existing = {(d.recipe_id, d.recipe_version) for d in dishes}
    result: list[Candidate] = []
    for index, old in enumerate(dishes):
        for recipe in eligible:
            if recipe.data_completeness != "COMPLETE":
                continue
            if recipe.default_serving_role != old.serving_role:
                continue
            if (recipe.recipe_id, recipe.version) in existing:
                continue
            replacement = PlannedDish(
                recipe_id=recipe.recipe_id,
                recipe_version=recipe.version,
                target_servings=old.target_servings,
                serving_role=old.serving_role,
                portion_rationale=f"curated {recipe.recipe_id}@{recipe.version} {old.serving_role} yield",
            )
            next_dishes = list(dishes)
            next_dishes[index] = replacement
            try:
                needs = resolve_needs(request, next_dishes, recipes).needs
            except (RecipeCoverageError, UnitConversionMissing):
                continue
            selections = propose_sku_selections(needs, catalog, limit=1)
            if selections:
                result.append(Candidate(dishes=next_dishes, selection=selections[0]))
    return result


def search_candidates(
    request: MealRequest,
    recipe_source: RecipeSource,
    catalog: CatalogView,
    evidence: EvidenceSource,
    preferred: Candidate | None,
    as_of: datetime,
    max_candidates: int = 3,
) -> SearchResult:
    """Evaluate no more than three *total* candidates, starting with C01.

    C01: exact previous SKU IDs/recipe versions, rebound to the coherent
    current snapshot and reverified. C02/C03: new evidenced SKU combinations
    or a same-role curated recipe. A verified *price/stock* cart is proposed
    only if independent allergy evidence does not block acceptance.
    """
    limit = max(0, min(3, max_candidates))
    if preferred is not None and preferred.user_review_state != "DRAFT":
        return SearchResult([], None, "ACCEPTED_DRAFT_IMMUTABLE")
    if limit == 0:
        return SearchResult([], None, "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET")

    # Eligibility is owned by the source. An ineligible or incomplete recipe
    # must never be invented as a replacement.
    eligible = [
        recipe for recipe in recipe_source.list_eligible(request, as_of)
        if recipe.data_completeness == "COMPLETE"
    ]
    if preferred is None:
        first = next((r for r in eligible if r.default_serving_role in ("main", "shared")), None)
        if first is None:
            return SearchResult([], None, "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET")
        dishes = [PlannedDish(
            recipe_id=first.recipe_id,
            recipe_version=first.version,
            target_servings=request.diners,
            serving_role=first.default_serving_role,
            portion_rationale=f"curated {first.recipe_id}@{first.version} yield for {request.diners} diners",
        )]
        try:
            needs = resolve_needs(request, dishes, recipe_source).needs
        except (RecipeCoverageError, UnitConversionMissing):
            return SearchResult([], None, "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET")
        selections = propose_sku_selections(needs, catalog, limit=1)
        if not selections:
            return SearchResult([], None, "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET")
        first_candidate = Candidate(dishes=dishes, selection=selections[0])
    else:
        # Rebinding only changes the source snapshot; never the chosen SKU IDs.
        # A different store never gets rebased or substituted automatically.
        rebased = (
            replace(preferred.selection, snapshot_id=catalog.snapshot.snapshot_id)
            if preferred.selection.store_id == catalog.snapshot.store_id
            else preferred.selection
        )
        first_candidate = Candidate(dishes=list(preferred.dishes), selection=rebased)

    allowed_recipes = {(r.recipe_id, r.version) for r in eligible}
    def has_source_ineligible_recipe(candidate: Candidate) -> bool:
        return any((d.recipe_id, d.recipe_version) not in allowed_recipes for d in candidate.dishes)

    attempts: list[CandidateAttempt] = []
    seen: set[tuple] = set()
    had_economic_verified = False

    def evaluate(candidate: Candidate) -> CandidateAttempt | None:
        nonlocal had_economic_verified
        identity = _identity(candidate)
        if identity in seen or len(attempts) >= limit:
            return None
        seen.add(identity)
        try:
            resolution = resolve_needs(request, candidate.dishes, recipe_source)
        except (RecipeCoverageError, UnitConversionMissing):
            return None
        cart = build_cart(
            request, candidate.dishes, resolution, candidate.selection, catalog, as_of
        )
        if has_source_ineligible_recipe(candidate):
            # A price/stock-valid draft is still disallowed if the recipe source
            # no longer marks its exact version eligible for this request.
            cart = cart.model_copy(update={
                "cart_verification_status": "INFEASIBLE",
                "verified_at": None,
                "problems": [*cart.problems, {"code": "RECIPE_NOT_ELIGIBLE"}],
            })
        revision = len(attempts) + 1
        cart = cart.model_copy(update={
            "revision": revision,
            "verification_basis": {
                **cart.verification_basis,
                "cart_revision": revision,
                "candidate_id": f"C{revision:02d}",
            },
        })
        allergy = None
        if cart.cart_verification_status == "VERIFIED":
            had_economic_verified = True
            allergy = assess_allergens(request, resolution, cart.lines, evidence, as_of)
        attempt = CandidateAttempt(
            candidate_id=f"C{revision:02d}", candidate=candidate,
            cart=cart, allergy=allergy,
        )
        attempts.append(attempt)
        return attempt

    first_result = evaluate(first_candidate)
    if first_result is not None and first_result.allergy is not None and not first_result.allergy.acceptance_blocked:
        return SearchResult(attempts, first_result, None)

    if len(attempts) >= limit or (
        preferred is not None and preferred.selection.store_id != catalog.snapshot.store_id
    ):
        return SearchResult(
            attempts, None,
            "NO_ALLERGY_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET"
            if had_economic_verified else "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET",
        )

    if has_source_ineligible_recipe(first_candidate):
        # Changing SKU IDs cannot cure a recipe no longer eligible for the request.
        replacements = []
    else:
        try:
            fixed_needs = resolve_needs(request, first_candidate.dishes, recipe_source).needs
            replacements = propose_sku_selections(fixed_needs, catalog, limit=limit + 1)
        except (RecipeCoverageError, UnitConversionMissing):
            replacements = []

    for selection in replacements:
        candidate = Candidate(dishes=list(first_candidate.dishes), selection=selection)
        result = evaluate(candidate)
        if result is not None and result.allergy is not None and not result.allergy.acceptance_blocked:
            return SearchResult(attempts, result, None)
        if len(attempts) >= limit:
            break

    if len(attempts) < limit:
        menu_candidates = _make_menu_candidates(
            request, first_candidate.dishes, recipe_source, catalog, eligible
        )
        ranked = []
        for candidate in menu_candidates:
            cost = _price_rank(candidate, catalog, request, recipe_source)
            if cost is not None:
                ranked.append((cost, _identity(candidate), candidate))
        ranked.sort(key=lambda value: (value[0], str(value[1])))
        for _, _, candidate in ranked:
            result = evaluate(candidate)
            if result is not None and result.allergy is not None and not result.allergy.acceptance_blocked:
                return SearchResult(attempts, result, None)
            if len(attempts) >= limit:
                break

    return SearchResult(
        attempts, None,
        "NO_ALLERGY_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET"
        if had_economic_verified else "NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET",
    )
