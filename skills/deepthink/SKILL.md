---
name: deepthink
description: Invoke IMMEDIATELY via script when user requests structured reasoning for open-ended analytical questions. Do NOT explore first - the script orchestrates the thinking workflow.
---

# DeepThink

Run the script before exploring and follow its output; it runs the reasoning workflow.

Invoke:

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.deepthink.think --step 1" />
