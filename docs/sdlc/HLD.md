# High-Level Design (HLD) — MealMate UC-01

**Version:** 0.1 | **Status:** PROPOSED engineering framing. Existing core Python modules in open PR #8 are not merged; architecture and stack require explicit approval.

## Context and trust boundaries

| Layer | Responsibility | Trust / constraint |
| --- | --- | --- |
| Human browser or API consumer | Natural language / structured input, edit, inspect, accept | User claims/quantities may be incomplete; auth required for public exposure |
| Conversational boundary | Interpret CREATE/APPLY_CHANGE/EXPLAIN/CLARIFY; reject implicit ACCEPT | LLM output is **untrusted structured intent**, not authoritative facts |
| MealService orchestration | Manage request/session, source lookup, candidates, acceptance | Reuse deterministic core; controls revisions and source refresh |
| Recipe and ingredient core | Curated versioned source → portion/need/pantry resolution | Pure deterministic arithmetic; no LLM invention |
| Retail/cart core | Coherent catalog → selected SKU → whole-pack cart verification | Authoritative source only, same-store snapshot |
| Allergen evidence core | Per-subject/per-allergen ingredient & cross-contact checks | Versioned evidence, scope-bound UNKNOWN vs ABSENT |
| Draft repository | Persist session request+draft, local atomic CAS | Local transaction only, does not lock retailer |
| Source adapters | Fixture first; eventually live retailer/provider | Must return provenance, completeness, compatibility proof |
| Optional UI | Chat, menu, cart, warnings and approval action | UI cannot bypass server verification or auto-accept |

## Logical component diagram

~~~mermaid
flowchart TD
  H[Shopper / Future UI] --> API[Typed HTTP API]
  H --> CHAT[Optional LLM Intent Interpreter]
  CHAT --> API
  API --> SVC[MealService]
  SVC --> RECIPE[RecipeSource]
  SVC --> QUANT[Quantities + Pantry Resolver]
  SVC --> CATALOG[CatalogSource / Snapshot Refresh]
  QUANT --> PACK[SKU Selector / Cart Verifier]
  CATALOG --> PACK
  SVC --> EV[EvidenceSource]
  PACK --> ALLERGEN[Allergen Assessor]
  EV --> ALLERGEN
  PACK --> SEARCH[Bounded Candidate Evaluator <= 3]
  ALLERGEN --> SEARCH
  SVC --> DB[DraftRepository: Request + Draft CAS]
  SVC --> APPROVE[Explicit Acceptance Revalidator]
  APPROVE --> RECIPE
  APPROVE --> CATALOG
  APPROVE --> EV
  APPROVE --> DB
~~~

**Interaction truth:** the LLM is not a hidden source of trusted price, SKU, stock, recipe ingredient or allergy clearance. **No multi-agent fleet, LangGraph, MCP, RAG or vector DB required** absent a reviewed concrete need.

## Request-to-draft execution

1. Parse and validate user constraints; clarify essential missing/ambiguous values.
2. Filter complete eligible curated recipes and propose role-specific servings for a shared meal.
3. Scale ingredients and retain versioned component identities; aggregate then allocate confirmed pantry items.
4. Read one coherent selected-store catalog view, propose explicit SKU selection and calculate full-pack economic status.
5. Independently assess scoped FoodEvidence for each declared allergen on actual used components, pantry packages and purchased SKUs.
6. Retry from sourced alternatives at most twice after C01; preserve constraints and record all observed outcomes.
7. Present DRAFT with three separate statuses, provenance, quote exclusions and uncertainty.
8. On real applied change: version request and replace/reverify draft; on explanation: no write.
9. On explicit acceptance: re-read current price/stock, recipe versions and FoodEvidence, then local request+cart CAS. Any source change requires renewed verification and fresh customer confirmation.

## Proposed physical deployment, not yet approved

For the existing first slice, the plan proposes Python 3.12, Pydantic 2, FastAPI, stdlib sqlite3, pytest/httpx, synthetic JSON fixtures. PR #8 currently contains Python models, ports, fixtures and Tasks 2–5 core modules; no API/session/LLM client is present. This is a **continuity recommendation**, not a production deployment decision. A future frontend, remote DB, queue, auth provider and live retailer source are separately gated.

## Key design choices and alternatives

| Decision | Chosen/recommended | Rejected/deferred | Why |
| --- | --- | --- | --- |
| Recipe knowledge | Curated complete versioned records (**approved**) | LLM free-form recipe/amount | Traceability / correctness |
| Retail quotes | Deterministic pack verifier (**approved**) | Model generated prices | Source reliability |
| Source freshness | Independent expiry + coherent attested refresh (**approved**) | Arbitrary 15-minute TTL/mixed snapshots | Prevent stale/incompatible facts |
| Session memory | Explicit current-session state (**approved direction**) | Automatic long-term allergy preference storage | Privacy/control |
| Runtime | Python/FastAPI/SQLite **proposed** | No competing stack chosen | Leverage current tests/code; needs sign-off |
| Orchestration | One testable workflow **proposed** | Unneeded agent swarm | Fewer states and failure modes |
| Retail transport | Source ports now | Mandatory MCP now | Transport choice must follow real provider needs |

## Failure domains and observability

Domain functions return structured typed problems, not only human prose. Log correlation ID, request/cart revision, candidate ID, source revision and elapsed operation; redact allergy/pantry/user text. Retrying stale/failed provider data must not change snapshot identity or accept a cart. External API auth, secrets, rate limits and PII protections become mandatory before public deployment. See [SECURITY_PRIVACY](SECURITY_PRIVACY.md).

## Engineering acceptance / questions still open

- Review PR #4 runtime proposal and Tasks 6–9 interfaces; do not presume plan approval.
- Decide local-only demo vs authenticated external environment before release.
- Resolve stable candidate-exhaustion outcome naming and initial shared-menu composition at HTTP layer before exposing user contracts.
- Test provider compatibility attestation and acceptance races; SQLite cannot guarantee external stock availability.
- Confirm live LLM provider configuration and tests separately; mocks cannot justify live claims.
