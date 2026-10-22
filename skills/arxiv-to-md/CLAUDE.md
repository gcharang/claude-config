# arxiv-to-md/

Convert arXiv papers to LLM-consumable markdown.

## Files

| File        | What                              | When to read                 |
| ----------- | --------------------------------- | ---------------------------- |
| `SKILL.md`  | Skill invocation                  | Using this skill             |
| `README.md` | Architecture, invisible knowledge | Understanding design choices |

Python code: `../scripts/skills/arxiv_to_md/` (indexed by its own CLAUDE.md).

The review step dispatches the `arxiv-latex-reviewer` agent (`../../agents/arxiv-latex-reviewer.md`).
