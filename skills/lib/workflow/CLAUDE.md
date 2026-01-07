# workflow/

Workflow orchestration framework: typed domain model, XML/text formatters, CLI utilities.

## Files

| File        | What                                                      | When to read                                       |
| ----------- | --------------------------------------------------------- | -------------------------------------------------- |
| `types.py`  | Domain types: AgentRole, Routing, Dispatch, Step, QRState | Adding workflow, understanding type contracts      |
| `cli.py`    | Argument parsing, mode_main entry point                   | Creating new workflow script, debugging CLI args   |
| `README.md` | Architecture, data flow, design decisions                 | Understanding framework design, migration planning |

## Subdirectories

| Directory     | What                           | When to read                                    |
| ------------- | ------------------------------ | ----------------------------------------------- |
| `formatters/` | XML and text output formatters | Generating step output, debugging format issues |
