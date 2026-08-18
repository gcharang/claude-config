# shared/

Shared utilities consumed by planner and executor orchestrators plus the developer/TW/QR sub-agent scripts.

## Files

| File                    | What                                                        | When to read                                        |
| ----------------------- | ----------------------------------------------------------- | --------------------------------------------------- |
| `builders.py`           | String builders for common prompt fragments (banners, constraints) | Adding a constraint or banner used in multiple steps |
| `constants.py`          | Workflow step counts, gate-step sets, QR iteration limits   | Changing total step counts, iteration thresholds    |
| `constraints.py`        | Orchestrator/state-banner reusable prompt strings           | Modifying enforcement wording                       |
| `domain.py`             | Planner-wide enums and value types                          | Adding new planner-level domain concepts            |
| `gates.py`              | `build_gate_output()` — unified QR gate formatter           | Changing QR gate pass/fail routing                  |
| `resources.py`          | Convention loading, script path resolution, state dir validation AND placement (`resolve_state_dir`, `resolve_project_root`, the project-identity marker `ensure_project_root_recorded` / `load_project_root`, `.gitignore` gating incl. the tracked-files refusal and the post-creation ignore re-check, run-dir retention, the per-session temp fallback) | Adding a conventions file, changing resource paths, changing where state dirs live, how the project root is found or recorded, where the temp fallback lands, or how old run dirs are pruned |
| `routing.py`            | Centralized routing between work phases                     | Modifying phase transitions                         |
| `schema.py`             | Pydantic schemas + defaults for plan.json / context.json / qr state | Adding fields to state files                        |
| `temporal_detection.py` | Regex criteria for temporal contamination in comments       | Changing the temporal-contamination rules           |
| `__init__.py`           | Package marker                                              | Never (empty module)                                |

## Subdirectories

| Directory | What                                                                | When to read                             |
| --------- | ------------------------------------------------------------------- | ---------------------------------------- |
| `qr/`     | QR-specific CLI args, phase configs, state types, query predicates | Working with qr-{phase}.json state files |
