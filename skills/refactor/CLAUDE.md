# skills/refactor/

## Overview

Dimension-parallel refactoring skill. IMMEDIATELY invoke the script - do NOT
explore first.

## Index

| File/Directory        | Contents                    | Read When               |
| --------------------- | --------------------------- | ----------------------- |
| `SKILL.md`            | Invocation                  | Using this skill        |
| `scripts/refactor.py` | Main workflow orchestration | Debugging main workflow |
| `scripts/explore.py`  | Dimension-specific prompts  | Debugging exploration   |

## Key Point

The script IS the workflow (6 steps: dispatch -> triage -> deep-dive -> derive -> validate -> synthesize).
Step 1 launches 8 parallel Explore agents (one per dimension) using Sonnet.
Do NOT explore or analyze before invoking. Run the script and obey its output.
