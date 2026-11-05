# Software Requirements Specification (SRS) — UC-01

**Version 0.1 | Status: DRAFT.** This document makes functional/non-functional requirements testable. It does **not** override [UC-01](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) or [DATA_CONTRACT](../DATA_CONTRACT.md).

## System boundary and actors

- Human: household shopper in one active session. Only one selected supermarket and one shared family meal per request.
- Trusted input sources: curated RecipeSource, authoritative single-store CatalogSource and scoped FoodEvidence source. Synthetic adapters are **test doubles**, not live retailer evidence.
- Untrusted input: natural-language user/LLM text, external free-form descriptions, unknown labels, stale source facts.
- Outputs: typed request, candidate attempts, sourced versioned draft, warnings/problems, explicit draft acceptance result. **Never order/payment/reservation**.

## Functional requirements (binding to PRD FR IDs)

**SRS-01 Request:** enforce positive diners/budget_vnd, VND only, meal type, explicit restrictions and pantry quantity confirmation; ambiguous allergy alias or ungrounded dietary threshold → clarification, not invented restriction. Malformed input is typed validation failure. Trace FR-01, AC04/32.

**SRS-02 Source eligibility:** complete curated recipe version with known role, base_servings and every component including condiments; source must attest preferences/dislikes/restrictions for eligible selection. Unsupported eligibility filters fail closed. Trace FR-03/04, AC02/11/13.

**SRS-03 Quantity arithmetic:** use Decimal/rational intermediate amounts; normalize only sourced compatible units and food form; scale per role, aggregate same canonical ingredient/form before pantry/pack rounding; unconfirmed pantry not deducted; each used recipe component and allocated pantry_item_id remains traceable. Trace FR-05, AC04/06/11/12/18/26.

**SRS-04 Catalog matching:** all selected SKU records in one coherent selected-store snapshot; identity ingredient_id/form/dimension must match; one SKU per canonical need; pack ceil and unused remainder exact; no cross-store reuse or invalid combination. Trace FR-06, AC01/06/14/31.

**SRS-05 Financial and inventory verifier:** subtotal = sum(packs × integer price per pack) and <= budget. Insufficient known stock => INFEASIBLE; unknown/missing authoritative fact or expired relevant validity => DATA_UNAVAILABLE. Distinct price_valid_until and stock_valid_until, no implicit global TTL. Trace FR-06/07, AC05/09/16/19/33.

**SRS-06 Evidence assessor:** for every declared allergen, check ingredient presence and cross-contact separately on every used recipe component, selected SKU and allocated pantry item; typed revisioned source identity required. Known conflict rejects candidate. Unknown recipe or purchased-SKU evidence blocks acceptance. Unknown pantry-only evidence may warn without blocking purchase-data acceptance; do not claim allergy safety. Trace FR-08, AC03/15/17/18/21/22/24/25.

**SRS-07 Bounded fallback:** up to 3 complete evaluated candidates (C01 initial included) for budget/stock failure or source-eligible evidence substitution; fixed store, restrictions, diners, pantry and budget, immutable accepted cart. Exhaustion outcome distinguishes missing economic verification from economic-verified/evidence-ineligible. Trace FR-09, AC23/29/30/31.

**SRS-08 Conversation:** active effective request with conversation_revision (material applied changes only). Explain/hypothetical read-only. Updating only a named field retains all unnamed constraints; real edit creates new draft and invalidates prior verification/approval; accepted cart stays immutable. Trace FR-02/11/15, AC07/20/26/27.

**SRS-09 Acceptance:** only explicit dedicated action against expected cart revision; persisted request+draft dual CAS; fetch current recipe version, catalog facts and all FoodEvidence revisions. Expiry/source change => RECONFIRM_REQUIRED and newly verified DRAFT when feasible; no direct accept of refreshed values. BLOCKED for unacceptable evidence or economic failures. No payment/order/reservation. Trace FR-12, AC08/19/21/28/33.

**SRS-10 External interface:** typed create/read/change/accept/chat API; chat interpreter allowed actions CREATE/APPLY_CHANGE/EXPLAIN/CLARIFY, not ACCEPT; typed bounded provider errors; no invented response bodies. Trace FR-13/14, API proposal in [LLD_API](LLD_API.md).

**SRS-11 Session lifecycle:** finite expiry, explicit deletion of persisted request/cart and sensitive session state; no default cross-session dietary/allergy memory. Access isolation required for any exposed environment. Trace FR-02/15.

**SRS-12 UI:** future P1 UI presents current selected store, portions, required/at-home/to-buy, SKU packs, unused remainder, source timestamps, all blockers and separate statuses; explicit accept CTA only for eligible draft. Trace FR-10/16 and [UX spec](UX_SPEC.md). UI implementation requires separate design approval.

## Error and state semantics

| Domain | Allowed state / outcome | Invariant |
| --- | --- | --- |
| Cart data | VERIFIED / INFEASIBLE / DATA_UNAVAILABLE | VERIFIED means **purchase-data only** |
| Meal allergen | NOT_ASSESSED / ASSESSED_NO_KNOWN_CONFLICT / REVIEW_REQUIRED / KNOWN_CONFLICT | No status means medical safety |
| User review | DRAFT / ACCEPTED / REJECTED | Only explicit acceptance can produce ACCEPTED |
| Acceptance request | ACCEPTED / RECONFIRM_REQUIRED / BLOCKED | Source/evidence revision change never silently ACCEPTED |
| Search | NO_VERIFIED_CANDIDATE_IN_EVALUATED_SET / NO_ACCEPTABLE_CART_IN_EVALUATED_SET | Not a proof of global infeasibility |

**Observed implementation discrepancy to triage:** PR #8 search.py returns NO_ALLERGY_ELIGIBLE_CANDIDATE_IN_EVALUATED_SET where canonical UC-01 names NO_ACCEPTABLE_CART_IN_EVALUATED_SET. Determine intended stable contract with engineering review before API exposure; write a regression test before changing code.

## Non-functional and quality requirements

| ID | Requirement | Verification / release gate |
| --- | --- | --- |
| NFR-01 Correctness | No fabricated recipe amount, price, stock, identity or allergen clearance; strict type/decimal/unit validation | Negative deterministic scenarios and source-port contract tests |
| NFR-02 Consistency | One snapshot per cart, independent price/stock expiry, no incompatible carry-forward; acceptance dual CAS | AC19/20/28/33 and concurrency simulations |
| NFR-03 Privacy | No personal allergies/diagnoses in logs or cross-session memory by default; expire/delete session | Log scan + expiry/delete test |
| NFR-04 Security | Input allowlist, provider timeout, bounded retries, secret env, least privilege, session authorization before public access | Threat review and adverse-input tests |
| NFR-05 Reproducibility | Python 3.12 clean install and deterministic fixture dataset with frozen time; wheel loads packaged fixture | CI exact execution report |
| NFR-06 Observability | Structured correlation IDs and typed reasons without sensitive payloads | Inspect sample redacted log and failure event |
| NFR-07 Failure handling | Missing provider, malformed LLM, catalog mismatch, stale evidence are explicit non-success states; no unhandled response-to-success fallbacks | Inject failures and assert draft immutability |
| NFR-08 Performance | Each search bounded to 3 complete candidate evaluations; model/provider calls have bounded timeouts | Instrument and test bound; any latency SLO remains TBD with measured baseline |
| NFR-09 Maintainability | Separate deterministic domain from source adapters, HTTP, optional intent LLM; no speculative frameworks | Code-review responsibility/DI check |
| NFR-10 Accessibility (P1) | Semantic form controls, keyboard actions, readable statuses not conveyed by color only | Accessibility walkthrough after UX approval |

**Intentionally TBD:** production SLO, data retention duration outside local session, traffic volume, customer auth provider, deployment infrastructure, retailer API SLAs. Do not encode arbitrary defaults as business-approved facts.

## Requirements verification and change management

Each SRS-ID must map to a product FR, canonical AC, source of truth, test and named owner in [TRACEABILITY.md](TRACEABILITY.md). Before approving implementation, record any identified inconsistency as an issue/PR review finding and obtain relevant sign-off. A passed unit test does not establish an external-provider E2E. 
