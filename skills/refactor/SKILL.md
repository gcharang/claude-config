---
name: refactor
description: Invoke IMMEDIATELY via python script when user requests refactoring analysis, technical debt review, or code quality improvement. Do NOT explore first - the script orchestrates exploration.
---

# Refactor

When this skill activates, IMMEDIATELY invoke the script. The script IS the
workflow.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.refactor.refactor --step 1 --total-steps 7" />

| Argument        | Required | Description                 |
| --------------- | -------- | --------------------------- |
| `--step`        | Yes      | Current step (starts at 1)  |
| `--total-steps` | Yes      | Minimum 7; adjust if needed |

Do NOT explore or analyze first. Run the script and follow its output.
