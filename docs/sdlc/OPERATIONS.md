# Operations, Deployment and Support Runbook (UC-01)

**Version:** 0.1 | **Status:** PROPOSED checklist, not evidence of deployed service. Until Task 8 there is no runnable HTTP product in the reviewed PR #8 stack.

## Environments and configuration

| Environment | Purpose | Approved sources / caveats |
| --- | --- | --- |
| Developer local (initial) | Core deterministic tests, fixture API development | Versioned synthetic recipes/catalog/evidence, in-memory or local SQLite only |
| CI | Clean-install/package/test verification | Python 3.12, reproducible synthetic fixtures, no real personal data |
| Live LLM test (optional gated lane) | Validate real provider structured intent | Secrets only; test uses synthetic non-sensitive user requests |
| Preproduction (future) | Auth, privacy, real retailer contract, E2E | Separate infrastructure review |
| Production (future) | Customer facing | **Not authorized by UC-01 docs** |

## Proposed developer bootstrap (after required app dependencies land)

~~~bash
python3.12 -m venv .venv
# activate .venv as appropriate on your OS
python -m pip install -e '.[dev]'
python -m pytest -q -m 'not live_llm'
python -m compileall -q src/mealmate
~~~

The FastAPI ASGI app entry point and run command **must be finalized in Task 8**; do not advertise an executable server command before the module exists. Default CI must run without LLM keys. Keep synthetic fixture packaged with the wheel (already in Task 1 code branch).

### Environment variables (Task 9 only, names proposed in plan)

- MEALMATE_LLM_BASE_URL
- MEALMATE_LLM_API_KEY
- MEALMATE_LLM_MODEL

Never place values in source, sample screenshots, trace payloads or committed .env. Confirm provider transport/version semantics in Task 9. Storage path, session TTL, server bind address and allowed origins remain app configuration decisions with review; do not silently expose 0.0.0.0 or public access.

## Health/readiness and observability (implementation requirements)

Track status of configured source adapters, DB connection, app version/commit, source freshness problems, request/cart version conflicts and rejection codes. A health endpoint must **not** leak secrets or private session details. Logs should contain opaque correlation ID, candidate ID, reason code, major stage timings and source revision; do not log user allergies, pantry list, raw prompts or tokens. Establish alert thresholds from measured baseline rather than inventing operational SLO.

## Failure playbooks

| Symptom | Containment | Recovery criterion |
| --- | --- | --- |
| Catalog price/stock expires | Block accept; request coherent source refresh | New attested snapshot and explicit renewed approval |
| Price carry-forward incompatibility | Refresh both source facts or DATA_UNAVAILABLE | Every selected SKU has compatible source provenance |
| Recipe or FoodEvidence revision changes | Block old approval; re-evaluate recipe/label | New draft and explicit confirmation |
| Provider timeout/malformed response | Return non-mutating typed error; bounded retry | Valid typed source or safe fallback to clarification |
| SQLite busy/conflicting revision | Respect CAS; no last-write-wins | Client re-reads current request/cart and reapplies deliberate edit |
| No sourced eligible candidate | Report bounded evaluated blockers | User changes request or sources improve; no fabricated cart |
| Customer reports unsafe/misleading allergy claim | Disable affected recommendation/source route, preserve non-sensitive audit facts | Reviewed evidence contract and tested correction |
| Suspected session-data exposure | Restrict access, rotate secrets if relevant, investigate logs without spreading sensitive data | Security owner sign-off before re-enabling |

## Backup, recovery, and retention

For local synthetic dev, DB is disposable; do not treat it as customer records. For any real-user deployment, specify DB encryption, backups, retention periods, restoration tests and deletion completeness in a separate approved operations design. Never restore a session in a way that silently reactivates stale VERIFIED carts or acceptance eligibility; all external data must be revalidated.

## Release / rollback

**Before release:** approved PR chain, deterministic + HTTP E2E at exact SHA, versioned deployment artifacts, security/privacy gate and explicit owner approval. **Rollback:** revert deployment to last known working artifact, disable accept endpoint if source integrity is compromised, preserve immutable accepted drafts where lawful, and invalidate verification basis on restart/restore if authority cannot be proven. Document migration/restore instructions **when schema exists in Task 6**, not as speculative SQL now.

## Release handover package

Release note with known limitations, environment/commit, migrations (if any), configuration names, synthetic/live evidence distinction, test and CI links, monitoring owner and rollback decision. No “production ready” without public auth/authorization and live-source proof.
