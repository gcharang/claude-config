# planner/

Planning and execution workflows with QR gates, TW passes, and Dev execution.

## Files

| File          | What                                                   | When to read                                     |
| ------------- | ------------------------------------------------------ | ------------------------------------------------ |
| `README.md`   | Architecture, data flow, QR gates, design decisions    | Understanding planner architecture, QR workflows |
| `planner.py`  | Main planning workflow (5 QR gates)                    | Creating implementation plans                    |
| `executor.py` | Extended workflow with implementation and post-impl QR | Executing plans, understanding execution flow    |
| `explore.py`  | Codebase exploration for plan context                  | Understanding exploration phase                  |

## Subdirectories

| Directory | What                                          | When to read                                 |
| --------- | --------------------------------------------- | -------------------------------------------- |
| `qr/`     | Quality Review modules (gates and validation) | Modifying QR logic, understanding validation |
| `tw/`     | Technical Writer modules (scrub, fill diffs)  | Modifying TW passes, temporal cleanup        |
| `dev/`    | Developer modules (post-implementation)       | Implementation execution                     |
| `shared/` | Shared resources (conventions, provider)      | Accessing conventions, resource management   |
