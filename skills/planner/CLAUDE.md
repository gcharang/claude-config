# skills/planner/

## Overview

Planning skill with authoritative resources referenced by agents and scripts.

## Index

| File/Directory                        | Contents                                      | Read When                                    |
| ------------------------------------- | --------------------------------------------- | -------------------------------------------- |
| `SKILL.md`                            | Planning workflow activation                  | Using the planner skill                      |
| `scripts/planner.py`                  | 13-step planning orchestration                | Debugging planner behavior                   |
| `scripts/executor.py`                 | Plan execution orchestration (9 steps)        | Debugging executor behavior                  |
| `scripts/qr/plan-completeness.py`     | QR-Completeness workflow                      | Debugging QR-Completeness validation         |
| `scripts/qr/plan-code.py`             | QR-Code workflow                              | Debugging QR-Code validation                 |
| `scripts/qr/plan-docs.py`             | QR-Docs workflow                              | Debugging QR-Docs validation                 |
| `scripts/qr/post-impl-code.py`        | QR code quality review                        | Debugging QR code review                     |
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
| `resources/severity-taxonomy.md`      | MUST/SHOULD/COULD definitions                 | Understanding QR severity                    |
| `resources/intent-markers.md`         | :PERF:/:UNSAFE: marker spec                   | Understanding intent markers                 |
| `scripts/qr/README.md`                | QR invisible knowledge                        | Understanding QR iteration bias              |

## Script Organization

Scripts are organized by the agent that invokes them:

```
scripts/
  planner.py              # Main agent - 13-step unified workflow
  executor.py             # Main agent - 9-step execution orchestration
  qr/                     # quality-reviewer agent
    plan-completeness.py
    plan-code.py
    plan-docs.py
    post-impl-code.py     # Code quality review
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

Resources are **authoritative sources**. No manual sync required.

### How Resources Are Accessed

| Access Method    | When Used                        | How It Works                                           |
| ---------------- | -------------------------------- | ------------------------------------------------------ |
| Script injection | During planner/executor workflow | Scripts call `get_resource()` at runtime               |
| Agent reference  | Free-form mode (no script)       | Agent prompts use `<file working-dir=".claude" ... />` |

### Script-Injected Resources

| Resource                    | Injected By                           |
| --------------------------- | ------------------------------------- |
| `plan-format.md`            | `planner.py` at step 4                |
| `temporal-contamination.md` | `tw/plan-scrub.py`, `qr/plan-docs.py` |
| `diff-format.md`            | `dev/fill-diffs.py`                   |

### Agent-Referenced Resources

Agent prompts reference resources using `<file working-dir=".claude" uri="..." />`
tags. This eliminates manual sync -- agents read authoritative files directly.

| Resource                    | Referenced By                                    |
| --------------------------- | ------------------------------------------------ |
| `default-conventions.md`    | `agents/quality-reviewer.md` (Convention Refs)   |
| `temporal-contamination.md` | `agents/quality-reviewer.md`, `technical-writer` |
| `doc-sync/SKILL.md`         | `agents/technical-writer.md` (Convention Refs)   |

**When updating**: Edit the resource file. Changes take effect immediately.

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

1. **planner.py step 6-7**: QR-Completeness + Gate
2. **planner.py step 9-10**: QR-Code + Gate
3. **planner.py step 12-13**: QR-Docs + Gate
4. **executor.py step 4-5**: Code QR + Gate (defers to developer)
5. **executor.py step 7-8**: Doc QR + Gate (defers to technical-writer)
