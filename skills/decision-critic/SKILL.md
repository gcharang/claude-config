---
name: decision-critic
description: Invoke IMMEDIATELY via script to stress-test decisions and reasoning. Do NOT analyze first - the script orchestrates the critique workflow.
---

# Decision Critic

Run the script before analyzing and follow its output; it runs the critique.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.decision_critic.decision_critic --step 1 --decision '<decision text>'" />

| Argument        | Required | Description                             |
| --------------- | -------- | --------------------------------------- |
| `--step`        | Yes      | Current step (1-7)                      |
| `--decision`    | Step 1   | The decision statement being criticized |
