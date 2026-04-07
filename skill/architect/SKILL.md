---
name: architect
description: Use when a feature request must be translated into system design. Best for converting a short requirement into API contracts, data structures, system component topology, integration boundaries, and implementation constraints for downstream engineers.
---

# Architect

## Goal

Turn a product requirement into a buildable system design with stable contracts.

## Inputs

- one-line requirement or feature goal
- `MVP.md`
- `work_now.md`
- current backend/frontend structure

## Workflow

1. Restate the goal in system terms.
2. Define the minimum architecture slice needed for the active MVP.
3. Produce or refine:
   - API design
   - request/response schemas
   - core data structures
   - component topology
   - ownership boundaries between services and UI
4. Identify compatibility risks and migration impact.
5. Keep the design small enough for one MVP increment.

## Output

Provide:
- feature scope
- API endpoints and fields
- schema changes
- service/component responsibilities
- validation strategy

## Rules

- Design for the current MVP only.
- Prefer additive contracts over breaking changes.
- Make backend and frontend contracts explicit before parallel coding starts.
- Include testing impact and README/doc impact in every design output.
