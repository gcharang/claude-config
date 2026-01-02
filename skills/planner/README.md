# Planner

The planner skill handles both planning and execution. Two distinct workflows,
one coherent system.

## Planning Workflow

```
  Planning ----+
      |        |
      v        |
     QR -------+  [fail: restart planning]
      |
      v
     TW -------+
      |        |
      v        |
   QR-Docs ----+  [fail: restart TW]
      |
      v
   APPROVED
```

| Step                    | Actions                                                                    |
| ----------------------- | -------------------------------------------------------------------------- |
| Context & Scope         | Confirm path, define scope, identify approaches, list constraints          |
| Decision & Architecture | Evaluate approaches, select with reasoning, diagram, break into milestones |
| Refinement              | Document risks, add uncertainty flags, specify paths and criteria          |
| Final Verification      | Verify completeness, check specs, write to file                            |
| QR-Completeness         | Verify Decision Log complete, policy defaults confirmed, plan structure    |
| QR-Code                 | Read codebase, verify diff context, apply RULE 0/1/2 to proposed code      |
| Technical Writer        | Scrub temporal comments, add WHY comments, enrich rationale                |
| QR-Docs                 | Verify no temporal contamination, comments explain WHY not WHAT            |

Why the feedback loop? LLM-generated plans have gaps. Missing error handling.
Incomplete acceptance criteria. Ambiguous specs. QR-Completeness and QR-Code run
before TW to catch structural issues early. QR-Docs runs after TW to validate
documentation quality. Doc issues restart only TW; structure issues restart
planning. This is not overhead -- it catches mistakes before they become code.

## Execution Workflow

```
  Plan --> Milestones --> QR --> Docs --> Retrospective
               ^          |
               +- [fail] -+

  * Reconciliation phase precedes Milestones when resuming partial work
```

After planning completes and you clear context (`/clear`), execution proceeds:

| Step                   | Purpose                                                         |
| ---------------------- | --------------------------------------------------------------- |
| Execution Planning     | Analyze plan, detect reconciliation signals, output strategy    |
| Reconciliation         | (conditional) Validate existing code against plan               |
| Milestone Execution    | Delegate to agents, run tests; repeat until all complete        |
| Post-Implementation QR | Quality review of implemented code                              |
| Issue Resolution       | (conditional) Present issues, collect decisions, delegate fixes |
| Documentation          | Technical writer updates CLAUDE.md/README.md                    |
| Retrospective          | Present execution summary                                       |

The coordinator never writes code directly -- it delegates to developers. I
designed it this way intentionally. Separating coordination from implementation
produces cleaner results. The coordinator:

- Parallelizes independent work across up to 4 developers per milestone
- Runs quality review after all milestones complete
- Loops through issue resolution until QR passes
- Invokes technical writer only after QR passes

**Reconciliation** handles resume scenarios. If the user request contains
signals like "already implemented", "resume", or "partially complete", the
workflow validates existing code against plan requirements before executing
remaining milestones. Otherwise you are building on unknown foundation.

**Issue Resolution** presents each QR finding individually with options (Fix /
Skip / Alternative). Fixes are delegated to developers or technical writers,
then QR runs again. This cycle repeats until QR passes.
