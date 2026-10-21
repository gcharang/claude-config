# planner/

Planning and execution workflows with QR gates, TW passes, and Dev execution. State files managed by LLM agents for session continuity.

## Files

| File        | What                                                | When to read                                     |
| ----------- | --------------------------------------------------- | ------------------------------------------------ |
| `README.md` | Architecture, data flow, QR gates, design decisions | Understanding planner architecture, QR workflows |

## Subdirectories

| Directory           | What                                   | When to read                               |
| ------------------- | -------------------------------------- | ------------------------------------------ |
| `orchestrator/`     | Main workflows (planner, executor)     | Creating/executing plans                   |
| `architect/`        | Plan design sub-agent                  | Understanding planning workflow            |
| `cli/`              | RPC commands, argparse mirror, batch dispatch | Modifying plan commands, CLI UX     |
| `developer/`        | Exec-phase implementation              | Dev execution                              |
| `technical_writer/` | Documentation scrubbing and generation | TW passes, temporal cleanup                |
| `quality_reviewer/` | QR modules for all phases              | QR logic, validation, understanding gates  |
| `shared/`           | Shared resources, schemas, conventions | Accessing conventions, resource management |

## State Files

All plan state lives in plan.json. Context captured separately in context.json. See README.md for full schemas.

| File              | What                                    | Mutability          | When to read                   |
| ----------------- | --------------------------------------- | ------------------- | ------------------------------ |
| `plan.json`       | Complete plan state (milestones,        | mutable             | All planning phases            |
|                   | code_intents)                           |                     |                                |
| `context.json`    | User-provided planning context          | frozen after step 2 | Sub-agent context handover     |
| `qr-{phase}.json` | QA items for specific phase (ephemeral) | ephemeral           | QA decomposition, verification |
| `verify.json`     | Final suite/lint/type record (executor step 10) | written by cli/verify.py | Final-verification gate |
| `project_root`    | The project this run belongs to, one    | written when absent; content this planner provably did not write is replaced; anything else, including a marker naming another project, is kept | Terminal docs/plans save       |
|                   | absolute path (`ensure_project_root_recorded`) |                     | (`_save_plan_to_docs`)         |
