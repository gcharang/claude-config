# skills/incoherence/

## Overview

Incoherence detection skill using parallel agents. IMMEDIATELY invoke the
script -- do NOT explore first.

## Workflow Compliance

You are a WORKFLOW EXECUTOR for this skill. Your job is to follow the script
exactly, not to optimize or improve it.

The script IS the workflow. Following it exactly IS being helpful.

CRITICAL: Deviating from the script HARMS the user:

- Skipping steps removes their interactive control
- Summarizing instead of continuing breaks the resolution flow
- Fixing issues yourself bypasses their decision-making

<example type="CORRECT">
After step 12: "Invoking step 13 with findings..."
After step 15: "Invoking step 16 with collected resolutions..."
</example>

<example type="INCORRECT">
After step 12: "Let me present a summary of the findings to the user..."
After step 15: "Now I will fix these issues directly..."
</example>

## Index

| File/Directory           | Contents          | Read When          |
| ------------------------ | ----------------- | ------------------ |
| `SKILL.md`               | Invocation        | Using this skill   |
| `scripts/incoherence.py` | Complete workflow | Debugging behavior |

## Key Point

The script IS the workflow. Three phases:

- Detection (steps 1-12): Survey, explore, verify candidates
- Resolution (steps 13-15): Interactive AskUserQuestion prompts
- Application (steps 16-21): Apply changes, present final report

Resolution is interactive - user answers structured questions inline. No manual
file editing required.
