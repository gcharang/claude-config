---
name: solution-design
description: Invoke IMMEDIATELY via python script when user has a defined problem or root cause and needs solution options. Generates diverse solutions from multiple reasoning perspectives. Do NOT explore first - the script orchestrates the solution generation workflow.
---

# Solution Design

When this skill activates, IMMEDIATELY invoke the script. The script IS the
workflow.

This skill generates solutions for a defined problem or root cause. It does NOT
identify problems or perform root cause analysis--use problem-analysis for that.

## Invocation

```bash
python3 scripts/design.py --step 1 --total-steps 7
```

| Argument        | Required | Description                 |
| --------------- | -------- | --------------------------- |
| `--step`        | Yes      | Current step (starts at 1)  |
| `--total-steps` | Yes      | Minimum 7; adjust if needed |

Do NOT explore or analyze first. Run the script and follow its output.
