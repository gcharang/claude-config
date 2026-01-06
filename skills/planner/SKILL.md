---
name: planner
description: Interactive planning and execution for complex tasks. Use when user asks to use or invoke planner skill.
---

# Planner Skill

Two workflows: **planning** (12-step plan creation + review) and **execution**
(implement plans).

## Activation

When this skill activates, IMMEDIATELY invoke the corresponding script. The
script IS the workflow.

| Mode      | Intent                             | Command                                                |
| --------- | ---------------------------------- | ------------------------------------------------------ |
| planning  | "plan", "design", "architect"      | `python3 scripts/planner.py --step 1 --total-steps 12` |
| execution | "execute", "implement", "run plan" | `python3 scripts/executor.py --step 1 --total-steps 7` |

## When to Use

Use when task has:

- Multiple milestones with dependencies
- Architectural decisions requiring documentation
- Complexity benefiting from forced reflection pauses

Skip when task is:

- Single-step with obvious implementation
- Quick fix or minor change
- Already well-specified by user

## Resources

| Resource                              | Contents                   | Read When                                       |
| ------------------------------------- | -------------------------- | ----------------------------------------------- |
| `resources/diff-format.md`            | Unified diff specification | Writing code changes in milestones              |
| `resources/temporal-contamination.md` | Comment hygiene heuristics | Writing comments in code snippets               |
| `resources/default-conventions.md`    | Structural conventions     | Making decisions without explicit user guidance |
| `resources/plan-format.md`            | Plan template structure    | Completing planning phase (injected by script)  |

## Planning Workflow (12 steps)

**Steps 1-4: Planning**

1. Context Discovery - explore, gather requirements
2. Approach Generation - generate options with tradeoffs
3. Assumption Surfacing - user confirmation of choices
4. Approach Selection & Milestones - decide, write milestones + Code Intent

**Steps 5-12: Review**

5. QR-Completeness - validate plan structure
6. Gate - route based on QR result
7. Developer Fills Diffs - convert Code Intent to diffs
8. QR-Code - validate diffs and code quality
9. Gate - route based on QR result
10. TW Documentation Scrub - clean comments, inject WHY
11. QR-Docs - validate comment hygiene
12. Gate - PLAN APPROVED

## Execution Workflow (7 steps)

1. Execution planning - wave analysis
2. Reconciliation (conditional) - validate existing code
3. Milestone execution via wave-executor.py
4. Post-implementation QR - holistic review
5. QR Gate - route based on result
6. Documentation - create CLAUDE.md/README.md
7. Retrospective - summary presentation

Scripts inject step-specific guidance. Invoke and follow output.
