# skills/planner/

## Overview

Planning skill with resources that must stay synced with agent prompts.

## Index

| File/Directory                        | Contents                                      | Read When                                    |
| ------------------------------------- | --------------------------------------------- | -------------------------------------------- |
| `SKILL.md`                            | Planning workflow activation                  | Using the planner skill                      |
| `scripts/planner.py`                  | 12-step planning orchestration                | Debugging planner behavior                   |
| `scripts/executor.py`                 | Plan execution orchestration (9 steps)        | Debugging executor behavior                  |
| `scripts/qr/plan-completeness.py`     | QR-Completeness workflow                      | Debugging QR-Completeness validation         |
| `scripts/qr/plan-code.py`             | QR-Code workflow                              | Debugging QR-Code validation                 |
| `scripts/qr/plan-docs.py`             | QR-Docs workflow                              | Debugging QR-Docs validation                 |
| `scripts/qr/post-impl-code.py`        | QR code quality review (RULE 0/1/2)           | Debugging QR code review                     |
| `scripts/qr/post-impl-doc.py`         | QR documentation quality review               | Debugging QR doc review                      |
| `scripts/qr/reconciliation.py`        | QR reconciliation workflow                    | Debugging QR reconciliation verification     |
| `scripts/dev/fill-diffs.py`           | Developer diff creation workflow              | Debugging Developer diff creation            |
| `scripts/tw/plan-scrub.py`            | TW plan scrub workflow                        | Debugging TW documentation scrub             |
| `scripts/tw/post-impl.py`             | TW post-implementation workflow               | Debugging TW post-implementation docs        |
| `scripts/shared/`                     | Shared utilities (domain, formatting, cli)    | Modifying QR verification loop behavior      |
| `resources/plan-format.md`            | Plan template (injected by script)            | Editing plan structure                       |
| `resources/temporal-contamination.md` | Detection heuristic for contaminated comments | Updating TW/QR temporal contamination logic  |
| `resources/diff-format.md`            | Unified diff spec for code changes            | Updating Developer diff consumption logic    |
| `resources/default-conventions.md`    | Default structural conventions (4-tier)       | Updating QR RULE 2 or planner decision audit |

## Script Organization

Scripts are organized by the agent that invokes them:

```
scripts/
  planner.py              # Main agent - 12-step unified workflow
  executor.py             # Main agent - 9-step execution orchestration
  qr/                     # quality-reviewer agent
    plan-completeness.py
    plan-code.py
    plan-docs.py
    post-impl-code.py     # Code quality review (RULE 0/1/2)
    post-impl-doc.py      # Documentation quality review
    reconciliation.py
  dev/                    # developer agent
    fill-diffs.py
  tw/                     # technical-writer agent
    plan-scrub.py
    post-impl.py
  shared/                 # Shared utilities
    domain.py
    formatting.py
    cli.py
    resources.py
```

## Resource Sync Requirements

Resources are **authoritative sources**. Mode scripts inject resources at
runtime via `get_resource()` -- no manual sync required for most resources.

### Script-Injected Resources (No Manual Sync)

| Resource                    | Injected By                           |
| --------------------------- | ------------------------------------- |
| `plan-format.md`            | `planner.py` at step 4                |
| `temporal-contamination.md` | `tw/plan-scrub.py`, `qr/plan-docs.py` |
| `diff-format.md`            | `dev/fill-diffs.py`                   |

**When updating**: Edit the resource file. Changes take effect immediately --
scripts read resources at runtime.

### Agent-Embedded Resources (Manual Sync Required)

These resources are embedded in agent prompts because they're used in free-form
mode (no script invocation):

| Resource                 | Synced To                    | Embedded Section        |
| ------------------------ | ---------------------------- | ----------------------- |
| `default-conventions.md` | `agents/quality-reviewer.md` | `<default_conventions>` |

**When updating**: Modify `resources/default-conventions.md` first, then copy
full content verbatim into `<default_conventions>` section in QR.

## Three Pillars Pattern (QR Verification Loops)

The planner skill uses a consistent pattern for all QR verification checkpoints
to ensure fixes are always re-verified. This pattern is implemented in
`scripts/shared/formatting.py`.

### The Pattern

Every QR checkpoint has three mandatory elements:

| Pillar             | Purpose                              | Implementation           |
| ------------------ | ------------------------------------ | ------------------------ |
| **STATE BANNER**   | Visual header showing loop iteration | `format_qr_banner()`     |
| **STOP CONDITION** | Explicit blocker preventing skip     | `format_gate_step()`     |
| **RE-VERIFY MODE** | Different prompts when fixing issues | `--qr-iteration` + flags |

### CLI Flags

All scripts use consistent flags for QR verification loops:

| Flag             | Type    | Default | Purpose                              |
| ---------------- | ------- | ------- | ------------------------------------ |
| `--qr-iteration` | integer | 1       | Loop count (1=initial, 2+=re-verify) |
| `--qr-fail`      | boolean | false   | Indicates re-work after failed QR    |
| `--qr-status`    | string  | none    | Gate input: "pass" or "fail"         |

### QR Checkpoints

The pattern is applied at these checkpoints:

1. **planner.py step 5-6**: QR-Completeness + Gate
2. **planner.py step 8-9**: QR-Code + Gate
3. **planner.py step 11-12**: QR-Docs + Gate
4. **executor.py step 4-5**: Code QR + Gate (defers to developer)
5. **executor.py step 7-8**: Doc QR + Gate (defers to technical-writer)
