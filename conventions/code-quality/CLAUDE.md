# code-quality/

Code quality checks for LLM-assisted development, organized by detection scope.

## Files

| File           | What                                              | When to read                                             |
| -------------- | ------------------------------------------------- | -------------------------------------------------------- |
| `baseline.md`  | Atomic smells detectable in isolation             | QR baseline audit, planner pre-implementation checks     |
| `coherence.md` | Repetition/consistency patterns (file + codebase) | QR consistency review, refactoring at any scope          |
| `drift.md`     | Codebase-wide architectural issues                | Periodic architecture review, detecting accumulated debt |

## Conceptual Model

1. **Baseline** - Single code unit (function, class). Detectable from snippet alone.
2. **Coherence** - Same concept appearing N times. Threshold varies by scope (file vs codebase).
3. **Drift** - Architectural relationships. Only visible with full codebase view.
