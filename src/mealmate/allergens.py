"""Source-scoped food allergen eligibility for UC-01, independent of cart cost.

This is a review of supplier/recipe/user-provided *data*, not clinical risk
assessment. A clear result does not cover home handling or guarantee safety.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from .models.catalog import FoodSubjectRef
from .models.cart import CartLine
from .models.meal import MealRequest
from .ports import EvidenceSource
from .quantities import NeedsResolution

Severity = Literal["BLOCKER", "WARNING"]
MealAllergenStatus = Literal[
    "NOT_ASSESSED", "ASSESSED_NO_KNOWN_CONFLICT", "REVIEW_REQUIRED", "KNOWN_CONFLICT"
]

# Scope labels are adapter-normalized values, not free-text health assurances.
_ALLOWED_SCOPES = {
    "recipe_component": frozenset({"recipe_component", "recipe_ingredient"}),
    "sku": frozenset({"sku", "supplier_label", "product_label", "package_label"}),
    "pantry_item": frozenset({"pantry_item", "user_reported", "user_confirmed"}),
}


@dataclass(frozen=True)
class AllergyProblem:
    code: str
    subject_ref: FoodSubjectRef
    allergen_id: str | None
    severity: Severity
    detail: str


@dataclass(frozen=True)
class EvidenceRevision:
    subject_ref: FoodSubjectRef
    evidence_id: str
    evidence_revision: str
    source_ref: str
    assessed_at: datetime


@dataclass(frozen=True)
class AllergyAssessment:
    meal_allergen_status: MealAllergenStatus
    acceptance_blocked: bool
    problems: list[AllergyProblem]
    selected_food_evidence_revisions: list[EvidenceRevision]


@dataclass(frozen=True)
class _SubjectUse:
    subject_ref: FoodSubjectRef
    expected_source_ref: str | None = None
    expected_evidence_id: str | None = None


def assess_allergens(
    request: MealRequest,
    resolution: NeedsResolution,
    lines: list[CartLine],
    evidence: EvidenceSource,
    as_of: datetime,
) -> AllergyAssessment:
    """Review each declared allergen against every *used* recipe, pantry and SKU subject.

    Missing/unscoped/ambiguous evidence is uncertain, never assessed-absent.
    Pantry-only uncertainty is a visible warning; any uncertain recipe or
    purchased SKU blocks cart acceptance. A known conflict anywhere blocks.
    """
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("allergen evidence must be assessed at a UTC-aware instant")
    allergens = tuple(dict.fromkeys(request.allergens))
    if not allergens:
        return AllergyAssessment("NOT_ASSESSED", False, [], [])

    subjects = [
        _SubjectUse(component.subject_ref, expected_source_ref=component.source_ref)
        for component in resolution.recipe_component_uses
    ]
    subjects.extend(
        _SubjectUse(alloc.subject_ref, expected_evidence_id=alloc.food_evidence_ref)
        for alloc in resolution.pantry_allocations
    )
    subjects.extend(_SubjectUse(line.food_subject_ref) for line in lines)

    problems: list[AllergyProblem] = []
    revisions: list[EvidenceRevision] = []
    examined: dict[tuple[str, tuple[str, ...]], _SubjectUse] = {}
    known_conflict = False

    def add_issue(
        code: str, subject: FoodSubjectRef, allergen_id: str | None,
        detail: str, *, force_block: bool = False,
    ) -> None:
        severity: Severity = "BLOCKER" if force_block or subject.kind != "pantry_item" else "WARNING"
        problems.append(AllergyProblem(
            code=code, subject_ref=subject, allergen_id=allergen_id,
            severity=severity, detail=detail,
        ))

    for use in subjects:
        subject = use.subject_ref
        key = subject.kind, subject.parts
        if key in examined:
            if examined[key] != use:
                for allergen in allergens:
                    add_issue("FOOD_EVIDENCE_BINDING_CONFLICT", subject, allergen,
                              "Conflicting source bindings for the same food subject", force_block=True)
            continue
        examined[key] = use

        # A cart line must carry its exact source-scoped SKU subject, not a
        # product name or an unscoped SKU identifier.
        if subject.kind == "sku":
            selected_sku = subject.parts[1]
            if not any(line.sku == selected_sku and line.food_subject_ref == subject for line in lines):
                for allergen in allergens:
                    add_issue("FOOD_EVIDENCE_SUBJECT_MISMATCH", subject, allergen,
                              "Purchased SKU and evidence subject disagree", force_block=True)
                continue
        latest = evidence.current_for_subject(subject, as_of)
        if latest is None:
            for allergen in allergens:
                add_issue("FOOD_EVIDENCE_MISSING", subject, allergen,
                          "No current evidence for this exact food subject")
            continue
        if latest.subject_type != subject.kind or latest.subject_ref != subject:
            for allergen in allergens:
                add_issue("FOOD_EVIDENCE_SUBJECT_MISMATCH", subject, allergen,
                          "Source supplied another food subject's evidence")
            continue
        if latest.assessed_at > as_of:
            for allergen in allergens:
                add_issue("FOOD_EVIDENCE_NOT_CURRENT", subject, allergen,
                          "Food evidence was assessed after the verification instant")
            continue
        if use.expected_source_ref is not None and latest.source_ref != use.expected_source_ref:
            for allergen in allergens:
                add_issue("FOOD_EVIDENCE_PROVENANCE_MISMATCH", subject, allergen,
                          "Recipe evidence is not bound to the selected recipe source")
            continue
        if use.expected_evidence_id is not None and latest.evidence_id != use.expected_evidence_id:
            for allergen in allergens:
                add_issue("FOOD_EVIDENCE_ID_MISMATCH", subject, allergen,
                          "Pantry package's declared evidence ID is not current")
            continue

        revisions.append(EvidenceRevision(
            subject_ref=subject,
            evidence_id=latest.evidence_id,
            evidence_revision=latest.evidence_revision,
            source_ref=latest.source_ref,
            assessed_at=latest.assessed_at,
        ))
        for allergen in allergens:
            assessments = [
                a for a in latest.allergen_assessments if a.allergen_id == allergen
            ]
            if len(assessments) == 0:
                add_issue("ALLERGEN_ASSESSMENT_MISSING", subject, allergen,
                          "No ingredient-presence and cross-contact evidence for this allergen")
                continue
            if len(assessments) != 1:
                add_issue("ALLERGEN_ASSESSMENT_AMBIGUOUS", subject, allergen,
                          "Multiple potentially conflicting assessments for the same allergen")
                continue
            assessment = assessments[0]
            if assessment.assessed_at > as_of:
                add_issue("ALLERGEN_ASSESSMENT_NOT_CURRENT", subject, allergen,
                          "Allergen assessment was made after this verification instant")
                continue
            if assessment.assessment_scope not in _ALLOWED_SCOPES[subject.kind]:
                add_issue("ALLERGEN_SCOPE_MISMATCH", subject, allergen,
                          "Allergen assessment is scoped to a different food subject")
                continue
            if (
                assessment.ingredient_presence == "PRESENT"
                or assessment.cross_contact_status == "KNOWN_PRESENT"
            ):
                known_conflict = True
                add_issue("ALLERGEN_KNOWN_CONFLICT", subject, allergen,
                          "Declared allergen present in ingredient or known cross-contact",
                          force_block=True)
            elif (
                assessment.ingredient_presence == "UNKNOWN"
                or assessment.cross_contact_status == "UNKNOWN"
            ):
                code = (
                    "ALLERGEN_INGREDIENT_UNKNOWN"
                    if assessment.ingredient_presence == "UNKNOWN"
                    else "ALLERGEN_CROSS_CONTACT_UNKNOWN"
                )
                add_issue(code, subject, allergen,
                          "No affirmative evidence of absent ingredient and cross-contact")
            # The only other accepted pair is ABSENT / ASSESSED_ABSENT.

    status: MealAllergenStatus = (
        "KNOWN_CONFLICT" if known_conflict
        else "REVIEW_REQUIRED" if problems
        else "ASSESSED_NO_KNOWN_CONFLICT"
    )
    return AllergyAssessment(
        meal_allergen_status=status,
        acceptance_blocked=any(p.severity == "BLOCKER" for p in problems),
        problems=problems,
        selected_food_evidence_revisions=revisions,
    )
