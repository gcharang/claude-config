---
name: planner
description: Interactive planning and execution for complex tasks. Use when user asks to use or invoke planner skill.
---

# Planner Skill

Two-phase workflow: **planning** (create plans) and **execution** (implement
plans).

## Invocation Routing

| User Intent                                 | Script      | Invocation                                                                         |
| ------------------------------------------- | ----------- | ---------------------------------------------------------------------------------- |
| "plan", "design", "architect", "break down" | planner.py  | `python3 scripts/planner.py --step-number 1 --total-steps 5 --thoughts "..."`      |
| "review plan" (after plan written)          | planner.py  | `python3 scripts/planner.py --phase review --step-number 1 --total-steps 3 ...`    |
| "execute", "implement", "run plan"          | executor.py | `python3 scripts/executor.py --plan-file PATH --step-number 1 --total-steps 7 ...` |

Scripts inject step-specific guidance via JIT prompt injection. Invoke the
script and follow its REQUIRED ACTIONS output.

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

| Resource                              | Contents                                   | Read When                                       |
| ------------------------------------- | ------------------------------------------ | ----------------------------------------------- |
| `resources/diff-format.md`            | Unified diff specification for plans       | Writing code changes in milestones              |
| `resources/temporal-contamination.md` | Comment hygiene detection heuristics       | Writing comments in code snippets               |
| `resources/default-conventions.md`    | Priority hierarchy, structural conventions | Making decisions without explicit user guidance |
| `resources/plan-format.md`            | Plan template structure                    | Completing planning phase (injected by script)  |

**Resource loading rule**: Scripts will prompt you to read specific resources at
decision points. When prompted, read the full resource before proceeding.

## Workflow Summary

**Planning phase**: 5+ steps with focused concerns per step:

1. Context & Scope Discovery -- understand before proposing
2. Approach Generation -- generate options, not select
3. Assumption Surfacing -- user confirmation of architectural choices
4. Approach Evaluation & Selection -- evaluate and decide
5. Risks, Milestones & Verification -- document risks, refine milestones
6. (optional) Gap analysis and developer walkthrough

Final step writes plan to file.

**Review phase**: 3 steps -- (1) parallel QR for completeness + code, (2) TW
scrub, (3) QR-Docs validation. Step 1 MUST spawn both QR agents in parallel.

**Execution phase**: 7 steps -- analyze plan, reconcile existing code, delegate
milestones to agents, QR validation, issue resolution, documentation,
retrospective.

All procedural details are injected by the scripts. Invoke the appropriate
script and follow its output.
