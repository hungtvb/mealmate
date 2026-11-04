# MealMate — Product Brief

**Status:** Proposed product scope, 2026-11-04. Not an approved technical architecture.

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

Next: review docs/UC-01.md with realistic catalog and recipe fixtures before choosing runtime architecture.
