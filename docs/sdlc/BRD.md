# Business Requirements Document (BRD) — UC-01

**Version:** 0.1 | **Status:** DRAFT organizing approved UC-01 choices. Normative business logic remains in the [canonical UC-01 spec](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) and [Data Contract](../DATA_CONTRACT.md).

## Problem-to-capability mapping

| Business need | Actor job | Required business outcome | Policy / acceptance |
| --- | --- | --- | --- |
| BN-01 Meal planning | “Tối nay 4 người ăn gì?” | Multiple shared dishes only from eligible complete curated recipes | Recipe-first B, AC01/13/32 |
| BN-02 Quantity confidence | “Mỗi món mua bao nhiêu?” | Correct role-specific servings, aggregated ingredients, approved conversions | Portions A, AC06/11/12/26 |
| BN-03 Avoid duplicate shopping | “Nhà có gạo rồi” | Deduct only confirmed, traceable pantry quantities | AC04/18 |
| BN-04 Budget confidence | “Không quá 140.000đ” | Hard cap applies to full sellable packages in VND | Budget A, AC01/06/09 |
| BN-05 Retail feasibility | “Mua được tại siêu thị này không?” | One coherent store/snapshot, no invented stock/price | AC05/19/31/33 |
| BN-06 Dietary uncertainty | “Có người dị ứng tôm/đậu phộng” | Distinguish known conflicts and UNKNOWN across recipe, SKU and pantry | Pantry B, SKU A, AC03/17/21/24 |
| BN-07 Feasible substitutions | “Hết hàng hoặc vượt tiền” | Try at most three complete evidenced candidates; no silent relaxation | Fallback A, AC23/29/30 |
| BN-08 Conversational control | “Đổi món / giải thích / thử tăng rau” | Only explicit applied changes mutate effective constraints | Explicit Memory A, AC20/26/27 |
| BN-09 Human control | “Tôi đồng ý giỏ nháp này” | Revalidate and accept draft only, never order/pay | AC08/19/21/28/33 |

## Current business process / future process

**As-is:** shopper manually selects menu, retrieves recipes, scales quantities, checks pantry, searches supermarket catalog and availability, estimates packs and price, handles uncertainties and revises.

**To-be (UC-01):** request → typed constraints or clarification → eligible curated recipe set → role-aware servings → aggregate/deduct confirmed pantry → same-store versioned SKU matching → deterministic economic and allergen evidence checks → up to three sourced candidates → explainable draft → explicit revision-safe draft acceptance.

## Decision constraints that must survive every task

1. Exactly one **selected** store and one shared family meal per request. Shared dishes respect the **union** of diners' restrictions.
2. Recipe version, yield and ingredient amounts must come from curated source; model may not invent authoritative facts.
3. Charge for **whole** sellable packs. Taxes, delivery and promotions are excluded from the displayed UC-01 subtotal.
4. Unit conversion between raw/cooked or incompatible dimensions needs sourced factor.
5. Known recipe/SKU/pantry allergen conflict rejects the meal; unknown purchased-SKU or recipe-component evidence blocks acceptance; **unknown pantry-only evidence can leave a purchase-data VERIFIED draft eligible for explicit acceptance with warning**. No medical safety claim.
6. Price/stock independently expire. Refresh requires new coherent source-attested view and explicit reconfirmation.
7. Three evaluated proposals **total**, preserving all hard constraints. Exhaustion is not proof of global impossibility.
8. Material edits invalidate the old verification and update request revision; explanations/hypotheticals do not.
9. Accepted draft is a reviewed shopping list, not an order, charge or inventory reservation.

## Business acceptance and exceptions

- **Success:** one sourced candidate meets all purchase-data constraints and non-pantry allergy evidence requirements; the user sees ingredient amounts, packs, subtotal, caveats and has an explicit approve action.
- **Clarification:** missing essential diners/budget, unconfirmed pantry quantities needed for accurate deduction, ambiguous restriction or ingredient mapping.
- **No acceptable candidate:** report evaluated set, all observed blockers, known evidence limitations and user-controlled next steps. Do not fabricate an alternative or relabel the outcome as a guaranteed infeasible meal.
- **Changed sources at acceptance:** invalidate old draft and require reviewed replacement.

## Prioritization / decision log

UC-01 is P0. UI P1, live retailer P1+/future integration and paid checkout deferred. Requirements changes must update [PRD](PRD.md), [SRS](SRS.md), [TRACEABILITY](TRACEABILITY.md), affected AC and the central [DECISIONS.md](../DECISIONS.md), with owner sign-off if policy changes. 
