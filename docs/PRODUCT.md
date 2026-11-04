# MealMate — Product Brief

**Status:** UC-01 first-slice business scope approved 2026-11-04; technical implementation architecture and merge remain subject to design review. Canonical details: [UC-01 design](superpowers/specs/2026-11-04-uc01-meal-to-cart-design.md) and [Data Contract](DATA_CONTRACT.md).

## Problem
Customers know the occasion, number of diners, budget and food constraints, but spend time deciding dishes, calculating ingredients and locating buyable products.

## First target user
A household shopper planning one home-cooked meal and buying ingredients from one grocery store.

## First outcome
Convert a natural-language meal request into (1) a proposed menu with serving quantities, (2) ingredient requirements, and (3) a **verifiable draft grocery cart** based on real catalog records. Customer can revise or accept the cart.

## In scope for first vertical slice
- Diners, meal occasion, budget, preferences, dislikes, already-owned pantry items
- Explicit allergens and user-specified dietary restrictions
- Recipes with ingredient amounts and servings
- Ingredient-to-SKU matching, pack conversions, availability and price
- Follow-up changes that re-evaluate the plan and cart
- Draft cart review and confirmation

## Approved UC-01 business policies

Recipe-first: use curated, versioned, complete recipe amounts; choose role-aware portions, deduct confirmed pantry and match one store's SKU packs. The hard VND budget covers **whole packs actually purchased**, excluding disclosed taxes/shipping/promotions in the first slice. Proactively evaluate at most **three complete candidates including the first** when budget or stock fails, without relaxing constraints or auto-accepting any cart. A cart may be accepted with unresolved **pantry-only** allergen evidence if warned; unresolved **purchased-SKU or recipe-component** allergen evidence blocks acceptance, and no meal is medically certified. Price and stock have **independent source-defined expiry deadlines**; refresh expired facts into a coherent sourced store snapshot, failing closed if compatibility is not proven. Draft-cart acceptance requires the customer's explicit action, current source/evidence checks and does not create an order.

## Explicit non-goals
- Restaurant meals and food delivery marketplaces
- Placing paid orders, live checkout or payments
- Clinical meal plans or assurances about allergen safety without adequate evidence
- Comparing multiple retailers or optimizing shipping fees
- A generic agent platform, A2A or Deep Agents without demonstrated need

## Success criteria (to baseline and measure)
- Verified cart subtotal meets the stated budget, or the system transparently says no feasible solution was found
- Quantities cover the selected recipes at requested serving counts and purchasable pack sizes
- No invented prices, stock or SKU properties
- Safety constraints are preserved across re-planning and alternatives
- A shopper can review and modify the cart before any consequential action

Next: complete UC-01 design verification with synthetic acceptance fixtures; then prepare a reviewed implementation plan before choosing a runtime architecture. No application code is approved by this brief alone.
