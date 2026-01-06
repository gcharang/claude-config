---
name: refactor
description: Invoke IMMEDIATELY via python script when user requests refactoring analysis, technical debt review, or code quality improvement. Do NOT explore first - the script orchestrates exploration.
---

# Refactor

When this skill activates, IMMEDIATELY invoke the script. The script IS the
workflow.

## Invocation

```bash
python3 scripts/refactor.py --step 1 --total-steps 6
```

| Argument        | Required | Description                 |
| --------------- | -------- | --------------------------- |
| `--step`        | Yes      | Current step (starts at 1)  |
| `--total-steps` | Yes      | Minimum 6; adjust if needed |

Do NOT explore or analyze first. Run the script and follow its output.
