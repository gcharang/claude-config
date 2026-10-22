# orchestrator/

Main workflow orchestrators: `planner` (plan creation with one QR block) and `executor` (plan execution with parallel QR + a final verification gate).

## Files

| File           | What                                                                | When to read                                          |
| -------------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| `planner.py`   | Plan workflow: init/verify + plan-design QR block → APPROVED | Adding planning phases, changing QR gate routing      |
| `executor.py`  | Exec workflow: impl + code-QR + docs + docs-QR + final-verify (run + gate) | Debugging executor steps, changing fix-mode/verify-gate detection |
| `__init__.py`  | Package marker                                                      | Never (empty module)                                  |

## Run

Entry-point commands: `skills/planner/SKILL.md`; why they keep the caller's working directory:
`skills/lib/workflow/prompts/README.md` (form 2b).
