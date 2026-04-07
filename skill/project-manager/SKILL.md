---
name: project-manager
description: Use when work needs to be decomposed into sequenced, non-conflicting tasks for multi-agent delivery. Best for turning MVP goals, sequence diagrams, and architecture plans into execution-ready task slices, dependency order, ownership boundaries, and delivery checkpoints.
---

# Project Manager

## Goal

Convert architecture and roadmap inputs into an executable task plan that multiple agents can deliver without stepping on each other.

## Inputs

- `MVP.md`
- `work_now.md`
- sequence diagram or architecture flow
- current repo state

## Workflow

1. Identify the active MVP stage.
2. Break the stage into the smallest meaningful deliverables.
3. Build a dependency order:
   - contract first
   - backend and frontend in parallel when write sets do not overlap
   - tests and docs after interfaces stabilize
4. Assign ownership by file/module boundary.
5. Define merge gates:
   - contract gate
   - quality gate
   - docs gate
   - release gate
6. Require README sync and Git sync at each MVP closeout.

## Output

Return a compact plan with:
- target MVP stage
- task list
- owner per task
- dependency order
- validation checklist
- handoff notes

## Rules

- Do not assign overlapping write scopes unless explicitly needed.
- Prefer parallelism only when the interface boundary is already clear.
- If a task lacks a stable contract, create the contract task first.
- At MVP completion, require `README.md` update and Git commit/push.
