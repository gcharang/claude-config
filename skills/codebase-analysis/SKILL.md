---
name: codebase-analysis
description: Invoke IMMEDIATELY via python script when user requests codebase understanding, architecture comprehension, or repository orientation. Do NOT explore first - the script orchestrates exploration.
---

# Codebase Analysis

Understanding-focused skill that builds foundational comprehension of codebase structure, patterns, flows, decisions, and context. Serves as foundation for downstream analysis skills (problem-analysis, refactor, etc.).

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```bash
# First call (no confidence yet)
python3 scripts/analyze.py --step 1 --total-steps 4

# Subsequent calls (with confidence assessment)
python3 scripts/analyze.py --step 2 --total-steps 4 --confidence medium

# DEEPEN step with iteration tracking
python3 scripts/analyze.py --step 3 --total-steps 4 --confidence low --iteration 2
```

## Arguments

| Argument        | Required | Default     | Description                                             |
| --------------- | -------- | ----------- | ------------------------------------------------------- |
| `--step`        | Yes      | -           | Current step (1-4)                                      |
| `--total-steps` | Yes      | -           | Always 4 for this skill                                 |
| `--confidence`  | No       | `exploring` | Current confidence level (exploring/low/medium/certain) |
| `--iteration`   | No       | 1           | Iteration count (DEEPEN step only, max 4)               |

## Workflow

4 steps: Scope -> Survey -> Deepen -> Synthesize

Each step loops until confidence reaches `certain`. DEEPEN step caps at 4 iterations.

## Output

Facts about Structure, Patterns, Flows, Decisions, Context. NO severity ratings, NO issues, NO fixes.

Do NOT explore or analyze first. Run the script and follow its output.
