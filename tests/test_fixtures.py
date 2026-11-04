"""Task 1 source fidelity tests: every assertion is pinned to UC-01 §11."""
from __future__ import annotations

from datetime import datetime, timezone
import subprocess
import sys

import pytest
from pydantic import ValidationError

from mealmate.fixtures import FixtureSources, load_fixture
from mealmate.models.catalog import ProductSKU

AT = datetime(2026, 11, 4, 6, 10, tzinfo=timezone.utc)
EXPIRED = datetime(2026, 11, 4, 6, 45, tzinfo=timezone.utc)


def test_golden_fixture_is_typed_and_versioned() -> None:
    bundle = load_fixture("F-UC01-POS")
    assert (bundle.request.request_id, bundle.request.conversation_revision) == ("REQ-001", 1)
    assert bundle.request.diners == 4
    assert bundle.request.budget_vnd == 140000
    assert {p.pantry_item_id for p in bundle.request.pantry} == {"P01", "P02", "P03"}
    assert all(p.quantity_confirmed for p in bundle.request.pantry)
    assert {r.recipe_id for r in bundle.recipes} == {"R01", "R02", "R03", "R04"}
    assert all(r.version == "v1" and r.base_servings == 4 and r.data_completeness == "COMPLETE" for r in bundle.recipes)
    assert next(r for r in bundle.recipes if r.recipe_id == "R02").default_serving_role == "main"
    assert len(bundle.catalog.skus) == 6
    assert bundle.catalog.snapshot.store_id == "FG-01"
    assert bundle.catalog.snapshot.snapshot_id == "S-FG-001"
    assert bundle.catalog.snapshot.observed_at == datetime(2026, 11, 4, 6, tzinfo=timezone.utc)
    assert bundle.catalog.snapshot.price_valid_until == datetime(2026, 11, 4, 8, tzinfo=timezone.utc)
    assert bundle.catalog.snapshot.stock_valid_until == datetime(2026, 11, 4, 6, 30, tzinfo=timezone.utc)
    assert sum(p.price_vnd_per_pack for p in bundle.catalog.skus) == 130000
    assert len(bundle.evidence) == 19
    assert len({(e.subject_type, e.subject_ref.key) for e in bundle.evidence}) == 19
    assert all(e.source_ref and e.evidence_revision for e in bundle.evidence)

    data = bundle.catalog.skus[0].model_dump()
    with pytest.raises(ValidationError):
        ProductSKU.model_validate({**data, "price_vnd_per_pack": -1})
    with pytest.raises(ValidationError):
        ProductSKU.model_validate({**data, "source_ref": ""})


def test_sourced_recipe_and_sku_discovery() -> None:
    sources = FixtureSources(load_fixture("F-UC01-POS"))
    recipes = sources.list_eligible(sources.request, AT)
    assert {(r.recipe_id, r.version) for r in recipes} == {("R01", "v1"), ("R02", "v1"), ("R03", "v1"), ("R04", "v1")}
    assert sources.get("R02", "v1").source_ref == "fixture:recipe/R02@v1"
    assert sources.get("nonexistent", "v1") is None
    assert sources.current_version("R02", AT) == "v1"
    view = sources.get_view("FG-01", AT)
    assert len(view.skus) == 6
    assert {x.sku for x in view.skus} == {"G-RICE1000", "G-EGG10", "G-TOM500", "G-OIL500", "G-TOFU200", "G-GREEN500"}
    assert all(x.catalog_snapshot_id == view.snapshot.snapshot_id for x in view.skus)
    assert all(x.price_fact_ref and x.stock_fact_ref for x in view.skus)
    assert sources.get_view("FG-02", AT) is None
    selected = next(x for x in view.skus if x.sku == "G-TOM500")
    assert sources.current_for_subject(selected.food_evidence_ref, AT).evidence_id == "FE-G-TOM500"


def test_catalog_refresh_attestation_fixture() -> None:
    source = FixtureSources(load_fixture("F-UC01-POS"))
    original = source.get_view("FG-01", AT)
    assert original.snapshot.stock_valid_until < EXPIRED < original.snapshot.price_valid_until
    refreshed = source.refresh_view("FG-01", original, "STOCK", EXPIRED)
    assert refreshed.view is not None
    assert refreshed.view.snapshot.snapshot_id == "S-FG-003"
    assert refreshed.view.snapshot.stock_valid_until > EXPIRED
    assert refreshed.view.snapshot.source_revision != original.snapshot.source_revision
    assert refreshed.attestation_ref == "fixture:attestation/AC33-compatible"
    assert set(refreshed.attested_carried_price_refs) == {x.sku for x in original.skus}
    for sku in original.skus:
        assert refreshed.attested_carried_price_refs[sku.sku] == sku.price_fact_ref
    source_incompatible = FixtureSources(load_fixture("F-UC01-AC33-INCOMPATIBLE"))
    rejected = source_incompatible.refresh_view("FG-01", source_incompatible.get_view("FG-01", AT), "STOCK", EXPIRED)
    assert rejected.view is None
    assert rejected.attested_carried_price_refs == {}
    assert rejected.problem_code == "INCOMPATIBLE_PRICE_PROVENANCE"


def test_clean_src_editable_install(tmp_path) -> None:
    result = subprocess.run([sys.executable, "-c", "import mealmate; from importlib.metadata import version; print(version('mealmate'))"], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("0.1.")

def test_sku_cannot_reference_food_evidence_from_other_snapshot() -> None:
    from mealmate.models.catalog import CatalogView
    bundle = load_fixture("F-UC01-POS")
    raw = bundle.catalog.model_dump()
    raw["skus"][0]["food_evidence_ref"]["parts"] = ("FG-01", "G-RICE1000", "S-FG-OTHER")
    with pytest.raises(ValidationError):
        CatalogView.model_validate(raw)


def test_price_expired_cannot_be_reused_by_stock_only_refresh() -> None:
    source = FixtureSources(load_fixture("F-UC01-POS"))
    after_price_deadline = datetime(2026, 11, 4, 8, 1, tzinfo=timezone.utc)
    original = source.get_view("FG-01", AT)
    invalid = source.refresh_view("FG-01", original, "STOCK", after_price_deadline)
    assert invalid.view is None
    assert invalid.problem_code in {"STALE_REFRESH", "PRICE_EXPIRED"}
