---
name: incoherence
description: Detect and resolve incoherence in documentation, code, specs vs implementation. Includes reconciliation phase for applying user-provided resolutions.
---

# Incoherence Detector

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Prerequisites

User must specify the report filename (e.g., "output to incoherence-report.md").

## Invocation

```bash
# Detection phase (steps 1-13)
python3 scripts/incoherence.py \
  --step-number 1 \
  --total-steps 22 \
  --thoughts "<context>"

# Reconciliation phase (steps 14-22, after user edits report)
python3 scripts/incoherence.py \
  --step-number 14 \
  --total-steps 22 \
  --thoughts "Reconciling user resolutions from report"
```

| Argument        | Required | Description                               |
| --------------- | -------- | ----------------------------------------- |
| `--step-number` | Yes      | Current step (1-22)                       |
| `--total-steps` | Yes      | Always 22                                 |
| `--thoughts`    | Yes      | Accumulated state from all previous steps |

Do NOT explore or detect first. Run the script and follow its output.
