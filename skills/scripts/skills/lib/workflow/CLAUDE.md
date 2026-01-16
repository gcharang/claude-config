# workflow/

Workflow orchestration framework: types, formatters, and registration.

## Files

| File           | What                                                     | When to read                                           |
| -------------- | -------------------------------------------------------- | ------------------------------------------------------ |
| `README.md`    | Architecture, design decisions, patterns                 | Understanding workflow design, common patterns         |
| `core.py`      | Workflow, StepDef, StepContext, Outcome, Arg             | Defining new skills, understanding workflow data model |
| `discovery.py` | Workflow discovery via importlib scanning                | Understanding pull-based discovery, troubleshooting    |
| `__init__.py`  | Public API exports                                       | Importing workflow types, checking available exports   |
| `cli.py`       | CLI helpers for workflow entry points                    | Adding CLI arguments, modifying step output            |
| `constants.py` | Shared constants                                         | Adding new constants, modifying defaults               |
| `types.py`     | Domain types: Dispatch, AgentRole, BoundedInt, ChoiceSet | QR gates, sub-agent dispatch, test domains             |

## Subdirectories

| Directory     | What                         | When to read                                    |
| ------------- | ---------------------------- | ----------------------------------------------- |
| `formatters/` | Output formatting (XML/text) | Modifying step output format, adding formatters |

## Test

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_workflow_steps.py -v

# Run tests for specific workflow
pytest tests/ -k deepthink -v
```
