# tests/

Test suite for skills workflow framework.

## Rules

All tests must live in `tests/` and run through pytest (via `uv run`). No test files elsewhere in the codebase.

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
| `test_ast.py`                | Property-based AST node and renderer tests           | Testing AST construction and rendering     |
| `test_state_dir_placement.py` | Repo discovery, project anchor and marker, `.gitignore` gating, placement, run-dir retention | Changing where state dirs live or how old runs are pruned |
| `leak_guard.py`              | Session guard: snapshots the projects the suite can reach, fails on any write into them | Adding a test that mints a state dir or archives a plan |
| `test_leak_guard.py`         | Sensitivity of that guard, plus the hook that refuses an all-skipped session | Changing the guard's dimensions or its no-project behaviour |

## Test Execution

```bash
SCRIPTS="${CLAUDE_PROJECT_DIR:-$HOME}/.claude/skills/scripts"

# Run all tests
uv run --project "$SCRIPTS" pytest "$SCRIPTS" -v

# Run specific test file
uv run --project "$SCRIPTS" pytest "$SCRIPTS/tests/test_workflow_steps.py" -v

# Run tests for specific workflow
uv run --project "$SCRIPTS" pytest "$SCRIPTS" -k deepthink -v

# Run import tests only
uv run --project "$SCRIPTS" pytest "$SCRIPTS/tests/test_workflow_import.py" -v

# Run structure validation tests only
uv run --project "$SCRIPTS" pytest "$SCRIPTS/tests/test_workflow_structure.py" -v
```
