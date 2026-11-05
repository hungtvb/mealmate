# Project Charter — MealMate

**Version:** 0.1 | **Status:** DRAFT | **Owner for business decisions:** MealMate product owner | **Repository:** https://github.com/hungtvb/mealmate

## Purpose / business case

A household shopper can describe one home-cooked meal but must otherwise decide suitable dishes, estimate ingredients for several diners, subtract ingredients already available, find matching sellable grocery packs and stay within a real budget. Generic chat answers can be fluent yet unverifiable. MealMate seeks to turn that request into **a traceable, versioned, financially and inventory-verified draft shopping cart**, without pretending to guarantee food safety or complete a purchase.

## Outcome and success boundary

**North-star outcome:** one natural-language or typed shared-meal request → a versioned curated menu → sourced ingredient needs → confirmed pantry allocations → a single-store, full-pack priced draft → independent checks → an explicit user decision.

**Primary actor:** household shopper; secondary source operators (curated recipe/catalog/evidence upstream providers, **not** an admin UI role in UC-01).

| Goal | How assessed | Evidence required |
| --- | --- | --- |
| Accurate shopping costs | Actual whole-pack subtotal in integer VND within hard cap, or honest bounded failure | Pinned fixture math, cross-check tests |
| Verifiable retail facts | Every selected SKU/price/stock tied to authoritative source and coherent snapshot | Typed source references, fixture and adapter tests |
| Respect constraints | Shared-meal allergies/restrictions preserved through follow-ups | AC03/17/21/24/27/32 |
| Avoid hidden mutations | Explanation turns do not modify request or cart; applied edits versioned | AC20/26/27 plus concurrency tests |
| Explicit control | No checkout/payment; accepted draft only after current-version checks | AC08/19/28/33 HTTP E2E |
| Realistic confidence | Clearly separate synthetic, provider integration and live-LLM test evidence | Test report links and review record |

No performance, conversion, usability or quality percentages are asserted before baseline measurements. Post-baseline targets are a product-owner decision.

## Delivery boundaries

**P0:** UC-01 one selected supermarket, one shared meal (multiple dishes), curated complete versioned recipes, source-backed SKUs, pantry, hard whole-pack budget, scoped allergen evidence, bounded 3-candidate fallback, session-scoped draft and explicit approval, API-first and tests.

**P1 proposed, not approved for build:** consumer interface with chat, menu/portions, cart, source warnings and explicit draft acceptance. Requires separate UX and tech sign-off.

**Not in UC-01:** restaurant ordering, paid checkout, stock reservations, multiple-store optimization, individual menus, clinical diet prescriptions, generic multi-agent platform, automatic cross-session allergy memory.

## Constraints, dependencies and critical assumptions

- Local/synthetic source adapters can prove algorithmic behavior, **not** live retail availability or genuine supplier allergen accuracy.
- An external source must attest compatible catalog refresh; SQLite CAS does not lock price/inventory providers.
- Allergy evidence is per allergen and subject. Unknown pantry-only evidence has a different approval policy from unknown purchased SKU or recipe-component evidence.
- Source/tech choices are recommendations until engineering approval; no imported ShopMate code without verified license and fit.
- The first release is an API-first verified vertical slice; a public launch requires separate source, security and release gates.

## Responsibility and approval

| Role | Accountability |
| --- | --- |
| Product owner (human) | Accept business policies, scope, priority, material UX/acceptance changes and merge authorizations |
| Technical reviewer / architect | Approve interface/technical design, security assumptions, migration plan |
| Codex (implementer) | Read current repo rules, deliver planned changes/test evidence in separate PRs, report blockers |
| Independent reviewer | Challenge correctness, source identity, concurrency and tests; not replaced by self-review |
| QA / acceptance owner | Verify against executable AC oracles and classify evidence accurately |

Roles may be filled by the same team, but approvals and independent review must not be falsely claimed.

## Risks and gates

Safety/evidence claims; price/stock TOCTOU; unknown raw/cooked conversions; cross-session private data; hidden fallback constraint relaxation; accidental scope creep; and stacked unmerged PR divergence are explicitly tracked in [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md), [TEST_PLAN.md](TEST_PLAN.md) and [DELIVERY_PLAN.md](DELIVERY_PLAN.md).

**Initiation exit:** product boundary and business decisions reconciled with approved UC-01. **Current limitation:** whole project/architecture is not globally approved merely by this charter.
