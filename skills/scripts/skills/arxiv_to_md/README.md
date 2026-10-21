# arxiv_to_md Architecture

## Import Resolution

**Problem**: The sub-agent's preprocess step runs a Python heredoc that imports `skills.arxiv_to_md.tex_utils`. The sub-agent's Bash working directory is not the scripts project, so a bare interpreter cannot import the package, and every command rendered to the LLM must start with `uv run` (`tests/test_uv_run_invariant.py`).

**Solution**: The heredoc runs under `pin_cwd("uv run python - <<'EOF'")`, which renders `uv run --directory <skills/scripts> python -`. uv changes into the scripts project before it runs the interpreter, so the import resolves from any working directory without a `sys.path` entry.

**Rejected alternatives**:
- A `sys.path` entry computed from `__file__` and injected into the heredoc: the bare `python3` call it needs fails the uv-run invariant
- `os.getcwd()`: Sub-agent Bash tool cwd may differ from invoke working-dir, causing fragile runtime failures

## Template System

**STATIC_STEPS structure**: The `STATIC_STEPS` dictionary maps each step to a title and an instruction string printed verbatim as sub-agent workflow instructions. These strings are NOT executed by `sub_agent.py` itself - they're executed by a Claude sub-agent via the Bash tool.

**F-string trap**: The preprocess heredoc contains `print(f'Preprocessed: {result}')`. This is literal Python code within the template string meant for the sub-agent to execute. If `PREPROCESS_INSTRUCTIONS` were an f-string, Python would attempt to evaluate `{result}` at module load time, causing a `NameError`.

**Why string concatenation**: The `pin_cwd(...)` call is joined to the literal strings with `+` instead of being interpolated by an f-string, so the template's literal braces need no escaping.

**Alternative rejected**: `str.format()` would require escaping all literal braces as `{{ }}` throughout the template, making the bash heredoc harder to maintain.

## Invariants

- `STATIC_STEPS` strings are printed verbatim, not executed by sub_agent.py
- The bash heredoc runs in a separate process via Claude Bash tool
- `{result}` in the preprocess heredoc must remain a literal template placeholder, not evaluated at module load
- Every rendered command starts with `uv run`
