# Verification, Validation and Test Plan — UC-01

**Version:** 0.1 | **Status:** DRAFT. Canonical full expected results: [UC-01 §8 AC01–AC33](../superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md). Tests and proof are **not** created merely by this plan.

## Strategy

Prioritize scenario-driven correctness and security, not raw unit test count. Maintain five independent lanes:

1. **Pure domain:** scaling/rounding, source identities, allergen logic, pinned selector, candidate count.
2. **Source-contract/integration (synthetic):** typed recipes/catalog/evidence, compatible refresh, local persistent repository and concurrency.
3. **Real app E2E against fixture adapters:** HTTP → interpreter/service → source → verifier → SQLite → API response; both success and failure.
4. **Live LLM integration:** actual provider-backed structured-intent calls with strict collected and executed proof; never conflate mocks with live.
5. **Live retail supplier:** only once a real approved source adapter exists; source contract and price/stock authenticity separately verified.

## Fixed deterministic oracles (synthetic)

| Test | Fixture / as-of | Required result |
| --- | --- | --- |
| AC01 golden | 4 diners, 140,000 VND, original S-FG-001 | 5 SKU lines, 6 whole packs, **116,000 VND**, economic VERIFIED and NOT_ASSESSED |
| AC06 pack sizing | Need 600g; 500g/75,000 VND pack | 2 packs, 150,000 VND, 400g leftover |
| AC09 reprice | G-TOM500 at 50,000 VND in S-FG-002 | Original pinned candidate fails with 148,000 VND; no silent auto-substitution |
| AC12 aggregation | Tomatoes 300+200g; confirmed pantry 100g | Buy 400g **after** aggregation |
| AC17 two allergens | Selected SKU SHRIMP assessed absent but PEANUT UNKNOWN | Economic VERIFIED possible, meal REVIEW_REQUIRED, acceptance BLOCKED |
| AC21 pantry unknown | Unknown pantry only; sourced SKUs assessed | Cart VERIFIED, meal REVIEW_REQUIRED, explicit draft accept allowed **with warning** |
| AC23 candidate bound | C01 budget, C02 stock, C03 stale price | Exactly 3 evaluated, no C04; bounded no-verified outcome |
| AC24 purchased SKU unknown | Missing PEANUT cross-contact evidence | Cart data may verify; cannot accept |
| AC25 tomato ALT | S-FG-003, evidenced substitute | 120,000 VND, 5 lines, 6 packs; explicit accept only after full recheck |
| AC26 portion edit | R04 4→6 portions | Greens 600g; water total 2600ml; 5 lines, 7 packs, **132,000 VND** |
| AC27 explanation | Still-current draft, “Vì sao?” or hypothetical | No request/cart revision or verification change |
| AC28 revision race | Recipe R02 v1→v2 OR label v1→v2 | Old draft must not accept; new verification + reconfirm |
| AC29 budget fallback | Original pinned reprice to 148,000 VND | C02 evidenced tomato ALT 120,000 VND, still DRAFT |
| AC30 stock fallback | Original tofu only 1 of 2 packs | C02 400g ALT → 119,000 VND, 5 lines/5 packs |
| AC31 two stores | Eggs FG-01, tofu FG-02 | Never verified blended cart |
| AC33 independent freshness | 06:45Z; price until 08:00Z, stock expired 06:30Z | Old draft blocked; source-attested new snapshot or fail; renewed confirmation |

## Full AC01–AC33 coverage planning

| Batch / scenarios | Intended test layer and priority | Evidence state at SDLC drafting |
| --- | --- | --- |
| AC01–06 | Source, quantity, economic, allergy and HTTP paths (P0) | Some domain coverage reported PR #5–#8; HTTP not yet |
| AC07–12 | Follow-up/accept, price reversion, unit and aggregation (P0) | Some deterministic coverage; session/API not yet |
| AC13–18 | Portions, mixed bundles, allergen dual-source, version identity (P0) | Need full E2E case mapping |
| AC19–24 | Freshness race, revision CAS, pantry warning, candidate exhaustion, SKU unknown (P0) | Persistence/acceptance E2E not yet |
| AC25–30 | Substitution, portions, read-only turn, label race, two fallbacks (P0) | Domain fallback reported; HTTP and acceptance not yet |
| AC31–33 | Selected-store scope, shared-meal boundary, source-specific selective refresh (P0) | Domain scope partially reported; HTTP acceptance not yet |

**Do not assert 33/33 passing.** The 33 are scenario definitions. Build a machine-readable coverage report with each AC ID → test function → executed job/commit → PASS/FAIL/NOT_RUN and source classification. Tests for overlapping AC IDs count separately only where behavior differs.

## Negative/failure injection (mandatory)

- Source: missing SKU, missing price, stock unknown, price expired, stock expired, mismatched snapshot, incompatible per-SKU price attestation, duplicate conflicting label assessment.
- Quantities: negative/zero, unconfirmed pantry, different pantry package identities, unsupported raw↔cooked conversion, conflicting ingredient form and reused mixed bundle.
- Allergies: two allergens on same item; known ingredient conflict; missing seasoning component evidence; pantry-only unknown; purchased-SKU unknown; recipe version/subject substitutions.
- Conversation: explanation vs applied edit; stale request revision; duplicated/double accept; accepted draft edit creates new ID; restart and deleted/expired session.
- AI/API: malformed output, hallucinated SKU/price, implicit “accept”, unsupported custom individual meal, provider timeout, prompt injection, HTTP wrong revision and cross-session access.
- Candidate search: no more than C01/C02/C03, no repeated candidates, original SKU preserved as C01 before alternatives, no false global-infeasible claim.

## Additional contract and adversarial acceptance tests (design gates)

Before Task 6–8 is declared ready, add precise scenario or contract tests for:
- **Forged identity/revisions:** create/patch cannot set arbitrary `request_id`, `cart_id`, `conversation_revision`, `verification_basis`, source revisions or ACCEPTED state. Trusted service owns these fields and enforces schema allowlisting.
- **Forged time:** client-supplied `as_of`, old source timestamps or time-zone offsets cannot bypass expiry; deterministic test clock is internal, not an API input.
- **Store change:** store selection persists with the effective request; omitted field in a follow-up retains current store; explicit store change invalidates old draft and requires same-store re-verification; no mixed-store lines.
- **Cross-session data isolation:** another owner cannot GET/PATCH/ACCEPT/DELETE the first owner's draft; for local-only mode ensure no unauthenticated network exposure. Authentication design remains a separate pre-public-release gate.
- **Duplicate/concurrent accept:** two simultaneous requests with the same revision never produce two accepted transitions or checkout side effects; old request revision cannot race a material edit.
- **Stale read:** GET itself stays read-only yet exposes that price/stock are no longer current; accept at the same instant blocks/refreshes even if UI previously displayed VERIFIED.
- **Release boundary:** no order/payment/stock reservation endpoint or “medically safe” claim emerges from success path.

Do not claim these pass without real test identifiers, command output and execution records.

## Executable CI gates (proposed stack)

~~~bash
python3.12 -m venv .venv
# activate virtual environment as appropriate
python -m pip install -e '.[dev]'
python -c 'import mealmate'
python -m pytest -q -m 'not live_llm'
python -m compileall -q src/mealmate
~~~

Run in clean GitHub Actions and install a built wheel in an **isolated** directory outside repo to prove packaged fixture loading. Inspect actual run/commit/results. PR #8 reports 70 synthetic passing at its recorded head as of 2026-11-05; this is **not** API E2E and has not been independently reexecuted as part of this document task.

**Real LLM lane:** require MEALMATE_LLM_BASE_URL, MEALMATE_LLM_API_KEY and MEALMATE_LLM_MODEL from secrets; verify marker live_llm with **>0 collected**, then **>0 executed, 0 skipped, 0 failures/errors** with real provider calls and sanitized CI records. Zero collected/all skipped/missing credentials = NOT_RUN, never PASS. Isolate this lane from deterministic CI. Live retailer lane remains NOT_RUN until source exists.

## Scenario-based exit criteria

- Exact synthetic oracle matches for selected P0 cases through actual service and HTTP boundary.
- Security/evidence failure cases do not yield eligible ACCEPTED cart.
- Accept-time source and request/cart revision races demonstrably fail closed.
- Snapshot integrity and whole-pack accounting show source provenance, warning scopes and correct statuses.
- Documentation, traceability and issue/PR evidence updated. Independent review and owner release approval required.
- Report actual coverage with test run references and limitations; not an estimated percentage.
