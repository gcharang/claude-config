# planner/

Planning and execution workflows with QR gates, TW passes, and Dev execution.

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
| `technical_writer/` | Documentation scrubbing and generation | TW passes, temporal cleanup                |
| `quality_reviewer/` | QR modules for all phases              | QR logic, validation, understanding gates  |
| `shared/`           | Shared resources, schemas, conventions | Accessing conventions, resource management |
