# skills/incoherence/

## Overview

Incoherence detection skill using parallel agents for exploration and confirmation.

## Index

| File/Directory           | Contents                                       | Read When                                   |
| ------------------------ | ---------------------------------------------- | ------------------------------------------- |
| `SKILL.md`               | Workflow overview, step guide, quick reference | Using the incoherence skill                 |
| `scripts/incoherence.py` | Step orchestration with guidance output        | Debugging skill behavior, modifying prompts |

## Workflow Summary

6-step process with parallel agent phases:

1. **Dimension Generation**: Generate 3 analysis dimensions
2. **Exploration Dispatch**: Launch 3 haiku agents (parallel)
3. **Synthesis**: Select top 10 candidates
4. **Confirmation Dispatch**: Launch sonnet agents (parallel)
5. **Verdict Analysis**: TRUE_INCOHERENCE vs FALSE_POSITIVE
6. **Report**: Write final report

## Agent Requirements

- Step 2: Launch exactly 3 Task(subagent_type='Explore', model='haiku') in ONE message
- Step 4: Launch N Task(subagent_type='Explore', model='sonnet') in ONE message

## Backtracking

Supported at any step. Common patterns:

- Step 3 empty -> Step 1 with broader dimensions
- Step 5 all false positives -> Step 3 with stricter criteria
