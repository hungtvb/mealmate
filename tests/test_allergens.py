"""UC-01 Task 4: source-scoped allergy checks, no medical safety claim."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import import_module

from mealmate.cart_builder import build_cart, propose_sku_selections
from mealmate.fixtures import FixtureSources, load_fixture
from mealmate.models.catalog import AllergenAssessment, FoodSubjectRef
from mealmate.models.meal import PlannedDish
from mealmate.quantities import RecipeComponentUse, resolve_needs

AS_OF = datetime(2026, 11, 4, 6, 10, tzinfo=timezone.utc)


def evaluator():
    return import_module("mealmate.allergens").assess_allergens


def scoped_evidence(bundle, allergens=("PEANUT",)):
    """Make every existing synthetic subject independently assessed for each allergen."""
    return bundle.model_copy(update={
        "evidence": [
            e.model_copy(update={"allergen_assessments": [
                AllergenAssessment(
                    allergen_id=a, ingredient_presence="ABSENT",
                    cross_contact_status="ASSESSED_ABSENT",
                    assessment_scope=e.subject_type, source_ref=e.source_ref,
                    assessed_at=e.assessed_at,
                )
                for a in allergens
            ]})
            for e in bundle.evidence
        ]
    })


def with_evidence(bundle, evidence_id, **changes):
    records = [
        e.model_copy(update=changes) if e.evidence_id == evidence_id else e
        for e in bundle.evidence
    ]
    assert any(e.evidence_id == evidence_id for e in bundle.evidence)
    return bundle.model_copy(update={"evidence": records})


def prepare(bundle=None, allergens=("PEANUT",)):
    if bundle is None:
        bundle = scoped_evidence(load_fixture("F-UC01-POS"), allergens)
    request = bundle.request.model_copy(update={"allergens": list(allergens)})
    sources = FixtureSources(bundle)
    dishes = [
        PlannedDish(
            recipe_id=recipe.recipe_id,
            recipe_version=recipe.version,
            target_servings=4,
            serving_role=recipe.default_serving_role,
            portion_rationale="curated four-serving recipe",
        )
        for recipe in bundle.recipes
    ]
    resolution = resolve_needs(request, dishes, sources)
    selected = propose_sku_selections(resolution.needs, bundle.catalog, limit=1)[0]
    cart = build_cart(request, dishes, resolution, selected, bundle.catalog, AS_OF)
    assert cart.cart_verification_status == "VERIFIED"
    return request, resolution, cart, sources


def test_ac17_two_allergens_one_unknown_sku_cross_contact_blocks() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"), ("SHRIMP", "PEANUT"))
    tomato = next(e for e in bundle.evidence if e.evidence_id == "FE-G-TOM500")
    peanut = next(a for a in tomato.allergen_assessments if a.allergen_id == "PEANUT")
    bundle = with_evidence(bundle, "FE-G-TOM500", allergen_assessments=[
        a.model_copy(update={"cross_contact_status": "UNKNOWN"}) if a is peanut else a
        for a in tomato.allergen_assessments
    ])
    request, resolution, cart, sources = prepare(bundle, ("SHRIMP", "PEANUT"))
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    assert any(
        p.code == "ALLERGEN_CROSS_CONTACT_UNKNOWN" and p.allergen_id == "PEANUT"
        and p.subject_ref.parts[1] == "G-TOM500" and p.severity == "BLOCKER"
        for p in result.problems
    )
    assert not any(p.allergen_id == "SHRIMP" for p in result.problems)


def test_ac21_pantry_unknown_is_warning_not_cart_acceptance_blocker() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    bundle = with_evidence(bundle, "FE-P01", allergen_assessments=[])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert cart.cart_verification_status == "VERIFIED"
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert not result.acceptance_blocked
    assert any(
        p.subject_ref.parts == ("REQ-001", "P01")
        and p.code == "ALLERGEN_ASSESSMENT_MISSING" and p.severity == "WARNING"
        for p in result.problems
    )


def test_ac24_unknown_selected_sku_assessment_blocks_even_with_good_price() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    bundle = with_evidence(bundle, "FE-G-TOM500", allergen_assessments=[])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert cart.subtotal_vnd == 116000
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    assert any(
        p.code == "ALLERGEN_ASSESSMENT_MISSING" and p.subject_ref.kind == "sku"
        and p.subject_ref.parts == ("FG-01", "G-TOM500", "S-FG-001")
        for p in result.problems
    )


def test_ac03_known_recipe_conflict_rejects_candidate() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    evidence = next(e for e in bundle.evidence if e.evidence_id == "FE-R02-c03")
    bundle = with_evidence(bundle, "FE-R02-c03", allergen_assessments=[
        a.model_copy(update={"ingredient_presence": "PRESENT"})
        for a in evidence.allergen_assessments
    ])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "KNOWN_CONFLICT"
    assert result.acceptance_blocked
    assert any(
        p.code == "ALLERGEN_KNOWN_CONFLICT"
        and p.subject_ref.parts == ("R02", "v1", "c03")
        for p in result.problems
    )


def test_known_pantry_allergen_conflict_is_not_a_waivable_warning() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    e = next(e for e in bundle.evidence if e.evidence_id == "FE-P01")
    bundle = with_evidence(bundle, "FE-P01", allergen_assessments=[
        a.model_copy(update={"cross_contact_status": "KNOWN_PRESENT"})
        for a in e.allergen_assessments
    ])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "KNOWN_CONFLICT"
    assert result.acceptance_blocked
    assert any(p.subject_ref.kind == "pantry_item" and p.code == "ALLERGEN_KNOWN_CONFLICT" for p in result.problems)


def test_two_pantry_packages_keep_distinct_subject_and_evidence_revisions() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    p01 = bundle.request.pantry[0]
    p04 = p01.model_copy(update={"pantry_item_id": "P04", "quantity": 250, "food_evidence_ref": "FE-P04"})
    req = bundle.request.model_copy(update={
        "pantry": [p01.model_copy(update={"quantity": 250}), *bundle.request.pantry[1:], p04]
    })
    original = next(e for e in bundle.evidence if e.evidence_id == "FE-P01")
    e04 = original.model_copy(update={
        "evidence_id": "FE-P04",
        "subject_ref": FoodSubjectRef(kind="pantry_item", parts=("REQ-001", "P04")),
        "evidence_revision": "request-rev1-P04",
    })
    bundle = bundle.model_copy(update={"request": req, "evidence": [*bundle.evidence, e04]})
    request, resolution, cart, sources = prepare(bundle)
    assert not any(line.ingredient_id == "rice" for line in cart.lines)
    assert {a.pantry_item_id for a in resolution.pantry_allocations if a.ingredient_id == "rice"} == {"P01", "P04"}
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "ASSESSED_NO_KNOWN_CONFLICT"
    assert not result.acceptance_blocked
    pantry = [entry for entry in result.selected_food_evidence_revisions if entry.subject_ref.kind == "pantry_item"]
    assert {entry.evidence_id for entry in pantry} == {"FE-P01", "FE-P02", "FE-P03", "FE-P04"}
    assert {entry.subject_ref.parts[1] for entry in pantry} == {"P01", "P02", "P03", "P04"}


def test_unlisted_recipe_component_cannot_inherit_another_ingredients_assessment() -> None:
    request, resolution, cart, sources = prepare()
    missing = RecipeComponentUse(
        recipe_id="R02", recipe_version="v1", component_id="c99",
        ingredient_id="seasoning", food_form="dry", unit="g", quantity=1,
        source_ref="fixture:recipe/R02@v1",
        subject_ref=FoodSubjectRef(kind="recipe_component", parts=("R02", "v1", "c99")),
    )
    changed = replace(resolution, recipe_component_uses=[*resolution.recipe_component_uses, missing])
    result = evaluator()(request, changed, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    assert any(
        p.code == "FOOD_EVIDENCE_MISSING" and p.subject_ref.parts == ("R02", "v1", "c99")
        for p in result.problems
    )


def test_all_safe_scoped_evidence_still_does_not_claim_medical_safety() -> None:
    request, resolution, cart, sources = prepare()
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "ASSESSED_NO_KNOWN_CONFLICT"
    assert not result.acceptance_blocked
    assert result.problems == []
    assert len(result.selected_food_evidence_revisions) == 18
    assert len({(e.subject_ref.kind, e.subject_ref.parts) for e in result.selected_food_evidence_revisions}) == 18


def test_no_declared_allergens_is_not_assessed_not_allergen_free() -> None:
    bundle = load_fixture("F-UC01-POS")
    request, resolution, cart, sources = prepare(bundle, ())
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "NOT_ASSESSED"
    assert not result.acceptance_blocked
    assert result.selected_food_evidence_revisions == []


def test_newer_label_revision_controls_eligibility_not_older_safe_label() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    tomato = next(e for e in bundle.evidence if e.evidence_id == "FE-G-TOM500")
    newer = tomato.model_copy(update={
        "evidence_id": "FE-G-TOM500-v2", "evidence_revision": "label-v2",
        "assessed_at": AS_OF - timedelta(minutes=1),
        "allergen_assessments": [
            a.model_copy(update={"cross_contact_status": "UNKNOWN", "assessed_at": AS_OF - timedelta(minutes=1)})
            for a in tomato.allergen_assessments
        ],
    })
    bundle = bundle.model_copy(update={"refreshed_evidence": [newer, *bundle.refreshed_evidence]})
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.acceptance_blocked
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    bound = [e for e in result.selected_food_evidence_revisions if e.subject_ref.kind == "sku" and e.subject_ref.parts[1] == "G-TOM500"]
    assert len(bound) == 1 and bound[0].evidence_revision == "label-v2"


def test_future_assessment_cannot_clear_current_allergen_status() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    tomato = next(e for e in bundle.evidence if e.evidence_id == "FE-G-TOM500")
    bundle = with_evidence(bundle, "FE-G-TOM500", allergen_assessments=[
        a.model_copy(update={"assessed_at": AS_OF + timedelta(minutes=5)})
        for a in tomato.allergen_assessments
    ])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    assert any(p.code == "ALLERGEN_ASSESSMENT_NOT_CURRENT" and p.subject_ref.kind == "sku" for p in result.problems)


def test_ambiguous_duplicate_allergen_entries_cannot_clear_a_sku() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    tomato = next(e for e in bundle.evidence if e.evidence_id == "FE-G-TOM500")
    good = tomato.allergen_assessments[0]
    bundle = with_evidence(bundle, "FE-G-TOM500", allergen_assessments=[
        good, good.model_copy(update={"cross_contact_status": "UNKNOWN"}),
    ])
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    assert any(p.code == "ALLERGEN_ASSESSMENT_AMBIGUOUS" for p in result.problems)


def test_evidence_source_cannot_return_label_for_other_subject() -> None:
    request, resolution, cart, source = prepare()
    other = source.current_for_subject(FoodSubjectRef(kind="sku", parts=("FG-01", "G-EGG10", "S-FG-001")), AS_OF)

    class MisboundEvidence:
        def current_for_subject(self, subject_ref, as_of):
            if subject_ref.kind == "sku" and subject_ref.parts[1] == "G-TOM500":
                return other
            return source.current_for_subject(subject_ref, as_of)

    result = evaluator()(request, resolution, cart.lines, MisboundEvidence(), AS_OF)
    assert result.acceptance_blocked
    assert any(p.code == "FOOD_EVIDENCE_SUBJECT_MISMATCH" and p.subject_ref.parts[1] == "G-TOM500" for p in result.problems)


def test_missing_pantry_evidence_warns_but_missing_sku_evidence_blocks() -> None:
    bundle = scoped_evidence(load_fixture("F-UC01-POS"))
    bundle = bundle.model_copy(update={"evidence": [
        e for e in bundle.evidence if e.evidence_id not in {"FE-P01", "FE-G-TOM500"}
    ]})
    request, resolution, cart, sources = prepare(bundle)
    result = evaluator()(request, resolution, cart.lines, sources, AS_OF)
    assert result.meal_allergen_status == "REVIEW_REQUIRED"
    assert result.acceptance_blocked
    relevant = [p for p in result.problems if p.code == "FOOD_EVIDENCE_MISSING"]
    assert any(p.subject_ref.kind == "pantry_item" and p.severity == "WARNING" for p in relevant)
    assert any(p.subject_ref.kind == "sku" and p.severity == "BLOCKER" for p in relevant)
