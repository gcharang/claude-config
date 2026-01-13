---
name: arxiv-to-md
description: Convert arXiv papers to LLM-consumable markdown. Invoke when user provides an arXiv ID or URL.
---

# arXiv to Markdown

Convert arXiv papers (TeX source) to clean markdown for LLM consumption.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.arxiv_to_md.main --step 1" />

Run the script and follow its output. The orchestrator discovers arXiv IDs, dispatches sub-agents for conversion, and renames successful outputs.
