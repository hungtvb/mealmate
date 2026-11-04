# Architecture Direction (proposed)

**Not yet an implementation specification.** Design choices must be justified by UC-01.

## Logical responsibilities
1. Conversational intake — interpret requests, preserve explicit constraints and manage clarification.
2. Meal planning — propose candidate recipes from sourced recipe data.
3. Ingredient resolver — scale and aggregate recipe quantities.
4. Grocery services — query catalog, price and stock; construct candidate purchasable packs.
5. Deterministic verifier — enforce budget, counts, availability and evidence limitations.
6. Draft cart — show proposed choices; user approves, edits or rejects.

The LLM may explain and propose. It must not manufacture product facts or override deterministic constraints.

## Selective reuse from ShopMate
Evaluate LangGraph orchestration patterns, MCP transport/client patterns, RAG indexing and test fixtures **module by module** for fit, isolation, correctness and reuse cost. Do not copy unreviewed refund/HITL, verifier, A2A or claims about evaluations. Check rights/license before importing code.

## Deferred choices
Runtime framework, DB engine, vector store, UI, deployment, number of agents and MCP service boundaries remain undecided pending UC-01 and data-contract review.

## Engineering gate
First slice must demonstrate an end-to-end **verified draft cart**, with negative scenarios for unsafe/unknown allergens, unavailable SKUs, inconsistent packaging and price, and stale data.
