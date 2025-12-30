---
name: problem-analysis
description: Invoke IMMEDIATELY via python script for structured problem analysis and decision reasoning. Do NOT explore first - the script orchestrates the workflow.
---

# Problem Analysis Skill

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

```bash
python3 scripts/thinkdeep.py \
  --step 1 \
  --total-steps 6 \
  --thoughts "Problem: <describe>"
```

| Argument        | Required | Description                           |
| --------------- | -------- | ------------------------------------- |
| `--step`        | Yes      | Current step (starts at 1)            |
| `--total-steps` | Yes      | Minimum 6; adjust as script instructs |
| `--thoughts`    | Yes      | Accumulated state from previous steps |

## Phase Structure

| Step     | Phase       | Purpose                                     |
| -------- | ----------- | ------------------------------------------- |
| 1        | Decompose   | Problem, constraints, assumptions           |
| 2        | Generate    | 2-4 distinct solution approaches            |
| 3        | Critique    | Self-Refine feedback on solutions           |
| 4 to N-2 | Verify      | Factored verification (extra steps go here) |
| N-1      | Cross-check | Reconcile verified facts with claims        |
| N        | Synthesize  | Trade-off matrix and decision framework     |
