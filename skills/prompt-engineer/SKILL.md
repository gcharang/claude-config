---
name: prompt-engineer
description: Invoke IMMEDIATELY via python script when user requests prompt optimization. Do NOT analyze first - invoke this skill immediately.
---

# Prompt Engineer

When this skill activates, IMMEDIATELY invoke the script. The script IS the
workflow.

## Invocation

```bash
python3 scripts/optimize.py --step 1 --total-steps 5
```

| Argument        | Required | Description                 |
| --------------- | -------- | --------------------------- |
| `--step`        | Yes      | Current step (starts at 1)  |
| `--total-steps` | Yes      | Minimum 5; adjust if needed |

Do NOT analyze or explore first. Run the script and follow its output.
