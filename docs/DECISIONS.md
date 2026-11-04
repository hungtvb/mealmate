# Decision Log

Record consequential choices here or in a focused ADR; link the issue/PR and evidence. Do not backfill unmade decisions as approved.

| Date | Status | Decision | Rationale |
| --- | --- | --- | --- |
| 2026-11-04 | Agreed direction | MealMate starts with ingredients for a home-cooked meal | Narrow, understandable customer journey |
| 2026-11-04 | Agreed direction | Selective reuse from ShopMate, not full fork | Reduce inherited domain coupling and correctness risk |
| 2026-11-04 | Proposed | Single-store local catalog for first vertical slice | Enables verifiable price, packs and availability |
| 2026-11-04 | Proposed | Docs-first agent repository bootstrap | Avoid choosing runtime stack before UC-01 review |
| 2026-11-04 | Proposed — review needed | Recipe-first planning using structured recipes | Deterministic quantities and traceable recipe evidence; see [UC-01 spec](superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) |
| 2026-11-04 | Approved by product owner (Option A) | Budget is a hard cap on the **actual total cost of sellable packs purchased**, not the proportional cost of ingredients consumed | Example: 600 g required with only 500 g packs must be priced as **2 whole packs**, including the unused remainder. Taxes, shipping, coupons and discounts remain outside the proposed UC-01 subtotal unless separately reviewed; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Superseded by approved Option B | Unknown allergy evidence blocks all verification | Cart purchase-data checks are distinct from a meal's allergen assessment; see approved policy below |
| 2026-11-04 | Revised by approved Option B | FoodEvidence covers recipe/SKU/pantry; unknown allergen evidence blocks all acceptance | **Pantry** unknowns no longer prevent acceptance of an otherwise verified shopping cart; warnings persist |
| 2026-11-04 | Proposed — review needed | CatalogSnapshot carries price/stock validity windows; no global TTL assumed | Prevent stale mixed-source cart totals; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — review needed | Per-allergen ingredient and cross-contact assessments with versioned recipe/SKU/pantry references | A single global status could silently clear an unassessed allergen; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — review needed | Acceptance rechecks snapshot, evidence and revision atomically | Avoid approving a stale cart and confusing acceptance with checkout; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Approved by product owner (Option B) | Separate cart verification from meal-allergen assessment; allow cart acceptance when **only pantry** allergen evidence is unresolved | Verified purchase facts remain useful; warning persists, no medical suitability claim or payment; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Approved by product owner (Option A) | **Block acceptance of a purchased SKU with unknown evidence for a declared allergen**; request better evidence or independently evidenced substitute | Unlike pantry Option B, MealMate selects which retail products it recommends; avoid actively adding unassessed SKUs to an acceptable cart, without asserting medical safety; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Approved by product owner (Option A) | Auto-propose a shared family meal's **per-dish portions** using curated recipe yields, serving roles and meal composition; do not require upfront portion confirmation | Keep meal planning easy for the shopper while ingredient amounts remain traceable; diner may adjust portions, triggering full deterministic cart revalidation; see [UC-01 spec](superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) |
