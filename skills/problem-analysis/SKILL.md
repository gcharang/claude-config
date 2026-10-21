---
name: problem-analysis
description: Invoke IMMEDIATELY via script when user requests problem analysis or root cause investigation. Do NOT explore first - the script orchestrates the investigation.
---

# Problem Analysis

Root cause identification skill. Identifies WHY a problem occurs, NOT how to fix
it.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.problem_analysis.analyze --step 1" />

Run the script before exploring and follow its output.
