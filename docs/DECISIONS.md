# Decision Log

Record consequential choices here or in a focused ADR; link the issue/PR and evidence. Do not backfill unmade decisions as approved.

| Date | Status | Decision | Rationale |
| --- | --- | --- | --- |
| 2026-11-04 | Agreed direction | MealMate starts with ingredients for a home-cooked meal | Narrow, understandable customer journey |
| 2026-11-04 | Agreed direction | Selective reuse from ShopMate, not full fork | Reduce inherited domain coupling and correctness risk |
| 2026-11-04 | Proposed | Single-store local catalog for first vertical slice | Enables verifiable price, packs and availability |
| 2026-11-04 | Proposed | Docs-first agent repository bootstrap | Avoid choosing runtime stack before UC-01 review |
| 2026-11-04 | Proposed — review needed | Recipe-first planning using structured recipes | Deterministic quantities and traceable recipe evidence; see [UC-01 spec](superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) |
| 2026-11-04 | Proposed — review needed | Budget applies to purchasable pack subtotal | Avoid understating actual cart cost; tax/shipping not in UC-01 |
| 2026-11-04 | Proposed — review needed | Unknown allergy evidence blocks verified status | Unverified labels/cross-contact cannot be called safe |
| 2026-11-04 | Proposed — review needed | FoodEvidence supports recipe/SKU/pantry; unresolved allergy evidence blocks draft acceptance | Avoid unsubstantiated allergen clearance; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — review needed | CatalogSnapshot carries price/stock validity windows; no global TTL assumed | Prevent stale mixed-source cart totals; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — review needed | Per-allergen ingredient and cross-contact assessments with versioned recipe/SKU/pantry references | A single global status could silently clear an unassessed allergen; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — review needed | Acceptance rechecks snapshot, evidence and revision atomically | Avoid approving a stale cart and confusing acceptance with checkout; see [Data Contract](DATA_CONTRACT.md) |
| 2026-11-04 | Proposed — product sign-off needed | Display provisional shopping list but block whole-meal VERIFIED while pantry allergy evidence is unresolved | Preserve useful prices without claiming home food safety; see [Data Contract](DATA_CONTRACT.md) |
