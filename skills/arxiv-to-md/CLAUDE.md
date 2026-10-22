# arxiv-to-md/

Convert arXiv papers to LLM-consumable markdown.

## Files

| File        | What                              | When to read                 |
| ----------- | --------------------------------- | ---------------------------- |
| `SKILL.md`  | Skill invocation                  | Using this skill             |
| `README.md` | Architecture, invisible knowledge | Understanding design choices |

Python code in `../scripts/skills/arxiv_to_md/`:

| File           | What                                    |
| -------------- | --------------------------------------- |
| `main.py`      | Orchestrator steps                      |
| `convert.py`   | Converter (one paper, no model)         |
| `sub_agent.py` | Review sub-agent brief (residual LaTeX) |
| `tex_utils.py` | TeX preprocessing utilities             |
