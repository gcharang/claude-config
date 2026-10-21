---
name: prompt-engineer
description: Invoke IMMEDIATELY via script when user requests prompt optimization. Do NOT analyze first - invoke this skill immediately.
---

# Prompt Engineer

Run the script before analyzing and follow its output; it runs the optimization
workflow.

## Invocation

Start with step 1 (triage) to determine scope:

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.prompt_engineer.optimize --step 1" />

Then continue with determined scope:

<invoke working-dir=".claude/skills/scripts" cmd="uv run python -m skills.prompt_engineer.optimize --step 2 --scope <scope>" />

| Argument  | Required | Description                                      |
| --------- | -------- | ------------------------------------------------ |
| `--step`  | Yes      | Current step (1 = triage, 2 onward = workflow)   |
| `--scope` | For 2+   | Required from step 2 on. Determined by step 1.   |

### Scopes

- **single-prompt**: One prompt file, general optimization
- **ecosystem**: Multiple related prompts that interact
- **greenfield**: No existing prompt, designing from requirements
- **problem**: Existing prompt(s) with specific issue to fix
