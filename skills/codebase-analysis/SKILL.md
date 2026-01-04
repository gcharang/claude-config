---
name: codebase-analysis
description: Invoke IMMEDIATELY via python script when user requests codebase analysis, architecture review, security assessment, or quality evaluation. Do NOT explore first - the script orchestrates exploration.
---

# Codebase Analysis

When this skill activates, IMMEDIATELY invoke the script. The script IS the
workflow.

## Invocation

```bash
python3 scripts/analyze.py --step 1 --total-steps 4
```

| Argument        | Required | Description                 |
| --------------- | -------- | --------------------------- |
| `--step`        | Yes      | Current step (starts at 1)  |
| `--total-steps` | Yes      | Minimum 4; adjust if needed |

Do NOT explore or analyze first. Run the script and follow its output.
