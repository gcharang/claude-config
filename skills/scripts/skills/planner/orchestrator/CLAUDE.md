# orchestrator/

Main workflow orchestrators: `planner` (plan creation with one QR block) and `executor` (plan execution with parallel QR + a final verification gate).

## Files

| File           | What                                                                | When to read                                          |
| -------------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| `planner.py`   | Plan workflow: init/verify + plan-design QR block → APPROVED | Adding planning phases, changing QR gate routing      |
| `executor.py`  | Exec workflow: impl + code-QR + docs + docs-QR + final-verify (run + gate) | Debugging executor steps, changing fix-mode/verify-gate detection |
| `__init__.py`  | Package marker                                                      | Never (empty module)                                  |

## Run

Step 1 is anchored on `$CLAUDE_PROJECT_DIR`, then the caller's working directory: run it
from inside the project and do not `cd` into the skills tree. The two entry-point commands live in
`skills/planner/SKILL.md` -- one self-contained line each, form 2b in
`skills/lib/workflow/prompts/README.md`. Duplicating them here is how the two drift.
