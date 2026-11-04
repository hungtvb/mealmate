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
