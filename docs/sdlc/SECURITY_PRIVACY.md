# Security, Food-Evidence Safety and Privacy Requirements

**Version:** 0.1 | **Status:** DRAFT security design; **not a security certification**. Applicable from local fixtures through a future public product.

## Assets, trust boundaries and high-impact failures

| Asset / trust boundary | Threat or failure | Required control | Negative verification |
| --- | --- | --- | --- |
| Natural-language + LLM output → structured intent | Prompt injection changes budget/allergy, fabricates SKU, calls accept | Whitelisted typed intent, strict validation, **no ACCEPT action via chat** | Malformed output, hidden fields and injection cannot mutate draft |
| Selected catalog/view → cart | Cross-store or cross-snapshot mix, stale price/stock, hidden substitute | Typed source IDs, pinned SKU mapping, independent validity, attested compatible refresh | AC05/09/19/31/33 |
| Recipe and pantry → food evidence | Evidence borrowed from different recipe component/pantry package | Typed composite identity and versioned evidence, no name joins | AC17/18/24/28 |
| Evidence assessment → UI claim | “No warning” misrepresented as safe | Per-allergen ingredient and cross-contact status; UNKNOWN kept; safety wording guard | AC03/15/17/21/22/24 |
| Active session → persisted draft | Cross-session disclosure or deleted allergy history remains | Session ownership, finite TTL/delete, no implicit long-term memory | Session isolation and deletion tests |
| Draft acceptance → current external data | TOCTOU: changed stock, label or recipe; parallel apply_edit and accept | Recheck external revisions, then dual local CAS; stale => reconfirm | AC19/20/28/33 and race tests |
| User auth → draft routes (future public) | IDOR, guessed cart_id, unintended acceptance by another shopper | Authenticated identity and server-scoped authorization on **every** get/edit/accept/delete route | Cross-user request returns forbidden; no data leak |
| LLM/retailer credentials → logs and repo | Secret exposure | Environment/secret manager, no print/log, rotation, least privilege | Secret scanning and sanitized error/log review |
| External provider → availability | Timeout, partial response, retry storm | Bounded timeout/retry, idempotency for writes, circuit/fail-closed state | Inject timeout/partial/malformed source response |
| HTTP surface | Abuse, oversized prompt, automated expensive retries | Input size limits, request rate quotas, per-session bounded candidate work | Malicious sizes and exhaustion tests |

## Food-evidence policy — binding business rules

- A declared allergen applies to **every shared dish** for the union of all diners.
- Each used recipe component, purchased SKU and used pantry package must be assessed for **each declared allergen**; ingredient presence and cross-contact are separate.
- Known ingredient presence / known cross-contact ⇒ known conflict; reject meal candidate.
- Missing/unknown selected SKU or recipe-component assessment ⇒ not eligible for cart acceptance, even if cart-price/stock VERIFIED.
- **Only missing/unknown pantry-only evidence** may allow an independently verified cart to be explicitly accepted with a persistent, item-specific warning; acceptance is **not** confirmation of meal allergen safety.
- With no declared allergens show NOT_ASSESSED, never “allergen-safe”.
- A user acknowledgment never upgrades unknown purchased-SKU evidence to assessed absent.
- Source provenance shows what was checked, not a medical guarantee; kitchen utensils/handling are out of scope.

## Privacy and data lifecycle

UC-01 stores explicit meal constraints, pantry and draft only in the **active session**. Do **not** promote allergies, diagnoses, food restrictions or pantry details to long-term preferences automatically. Future saved preferences need explicit request/consent, review/edit/delete controls and a separately approved policy. Never persist disease diagnosis inferred from conversation.

**Local plan (proposed):** finite session TTL (24 hours proposed in PR #4, not product approved), SQLite session+draft records, explicit delete all relevant session/accepted-cart records as defined by reviewed data policy, and redacted structured logs. Upon expiry/delete, reject stale identifiers; test physical deletion of local rows. For production, define lawful purpose, retention and deletion policy before use with real customers.

## Data classification / logging

| Data | Classification | Storage/logging rule |
| --- | --- | --- |
| Public recipe title and nonpersonal curated quantities | Product reference | Versioned source record; safe to store if licensed |
| Retail SKU/pack/price/stock and source IDs | Business/source data | Scoped versioned metadata; respect vendor contractual restrictions |
| Request text, pantry, allergy and diet constraints | Potentially sensitive personal context | Active session only; redact from logs and traces; no git |
| Session/cart ownership identifiers | Access-controlled | Opaque IDs and authorization; never rely on possession of ID alone |
| LLM API key or retailer token | Secret | Env/vault only; no examples or screenshots of values |

## Authentication/deployment boundary

An unauthenticated local fixture API is acceptable **only as isolated developer tooling**. Before exposing to a network/customer: design and test authn/authz on every session route, CSRF for cookie sessions if applicable, TLS, proper CORS origins, rate limits, audit policy, secret rotation, backup encryption and deletion. These are **release blockers**, not implied current implementations.

## AI-specific controls

- Provider intent adapter returns only CREATE/APPLY_CHANGE/EXPLAIN/CLARIFY with whitelisted fields.
- User-provided product descriptions, notes or web text are untrusted; prompt content cannot override verifier/business rules.
- LLM cannot inject SKU, price, stock, FoodEvidence status or authoritative recipe quantities.
- Timeout, malformed JSON, schema mismatch, tool failure and prompt injection produce typed non-mutating errors.
- Validate that explanations reference actual selected source data; do not hallucinate citations, source timestamps or completed purchases.
- Red-team tests must include conflicting allergy, hidden HTML/system instructions in recipe/title, unknown SKU, stale price and “confirm/purchase for me”.

## Security review completion checklist

Named reviewer acknowledges identified threats; tests for identity/provenance, session isolation, deleted data, concurrency, external adapter failures and injections; run secrets scan; record exceptions and owners. Release readiness cannot be inferred from synthetic core unit tests alone.
