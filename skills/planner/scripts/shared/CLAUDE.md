# shared/

Shared utilities for planner scripts. Compatibility layer re-exports lib.workflow during migration.

## Files

| File           | What                                      | When to read                       |
| -------------- | ----------------------------------------- | ---------------------------------- |
| `__init__.py`  | Re-exports from lib.workflow (compat)     | Understanding import compatibility |
| `domain.py`    | Planner-specific types (FlatCommand, etc) | Adding guidance layer types        |
| `resources.py` | Resource loading (get_resource, etc)      | Injecting resources into prompts   |
