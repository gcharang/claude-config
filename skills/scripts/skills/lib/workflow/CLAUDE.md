# workflow/

Workflow orchestration framework: metadata types, discovery, XML AST, prompt helpers, and constants.

## Files

| File              | What                                                            | When to read                                        |
| ----------------- | --------------------------------------------------------------- | --------------------------------------------------- |
| `README.md`       | Framework architecture, testing domain types, invariants        | Understanding the workflow model, adding new skills |
| `core.py`         | `Workflow`, `StepDef`, `Arg` (metadata containers)              | Defining a new skill, adding `_params` metadata     |
| `discovery.py`    | `discover_workflows()` via importlib scanning                   | Debugging registry, understanding pull-based discovery |
| `cli.py`          | `mode_main()` and step-output CLI helpers                       | Adding CLI args to a skill entry point              |
| `constants.py`    | Shared constants, QR constants re-exports                       | Adding shared constants                             |
| `types.py`        | Domain types: `AgentRole`, `Dispatch`, `BoundedInt`, `ChoiceSet`, `Constant`, `QuestionOption`, `ResourceProvider` | QR gates, sub-agent dispatch, test domain generation |
| `__init__.py`     | Public API exports                                              | Importing workflow types                            |

## Subdirectories

| Directory     | What                                                       | When to read                   |
| ------------- | ---------------------------------------------------------- | ------------------------------ |
| `ast/`        | AST nodes, builder, renderer for XML step output           | XML generation for step output |
| `prompts/`    | Plain-text prompt builders (step, subagent dispatch, file) | Writing step formatters        |

## Test

`<scripts>` is the absolute path of the `skills/scripts` install you are working on.

```bash
uv run --project "<scripts>" --extra dev python -m pytest "<scripts>" -v
uv run --project "<scripts>" --extra dev python -m pytest "<scripts>" -k deepthink -v
```
