# workflow/

Workflow orchestration framework: types, formatters, registration, and testing.

## Files

| File           | What                                         | When to read                                           |
| -------------- | -------------------------------------------- | ------------------------------------------------------ |
| `README.md`    | Architecture, design decisions, patterns     | Understanding workflow design, common patterns         |
| `core.py`      | Workflow, StepDef, StepContext, Outcome, Arg | Defining new skills, understanding workflow data model |
| `__init__.py`  | Public API exports                           | Importing workflow types, checking available exports   |
| `cli.py`       | CLI helpers for workflow entry points        | Adding CLI arguments, modifying step output            |
| `constants.py` | Shared constants                             | Adding new constants, modifying defaults               |
| `testing.py`   | L0-L2 test harness, boundary input gen       | Running skill tests, adding test coverage              |
| `types.py`     | Domain types: Dispatch, AgentRole, etc       | QR gates, sub-agent dispatch                           |

## Subdirectories

| Directory     | What                         | When to read                                    |
| ------------- | ---------------------------- | ----------------------------------------------- |
| `formatters/` | Output formatting (XML/text) | Modifying step output format, adding formatters |

## Test

```bash
# Run all skill tests (L0-L2)
python -m skills.lib.workflow.testing --level 2

# Test specific skill
python -m skills.lib.workflow.testing --skill decision-critic --level 2
```
