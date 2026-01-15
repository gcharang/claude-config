# tests/

Test suite for skills workflow framework.

## Files

| File                         | What                                                 | When to read                               |
| ---------------------------- | ---------------------------------------------------- | ------------------------------------------ |
| `README.md`                  | Test framework architecture, design decisions        | Understanding test design, modifying tests |
| `conftest.py`                | Pytest configuration, fixtures, shared utilities     | Modifying test setup, adding fixtures      |
| `test_workflow_import.py`    | Skill module import tests                            | Debugging import failures                  |
| `test_workflow_structure.py` | Workflow structural validation tests                 | Debugging validation failures              |
| `test_workflow_steps.py`     | Exhaustive parametrized tests for all workflow steps | Running workflow tests, debugging failures |
| `test_domain_types.py`       | Unit tests for BoundedInt, ChoiceSet, Constant       | Testing domain type behavior               |
| `test_generation.py`         | Schema extraction and input generation for tests     | Modifying test case generation             |

## Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_workflow_steps.py -v

# Run tests for specific workflow
pytest tests/ -k deepthink -v

# Run import tests only
pytest tests/test_workflow_import.py -v

# Run structure validation tests only
pytest tests/test_workflow_structure.py -v
```
