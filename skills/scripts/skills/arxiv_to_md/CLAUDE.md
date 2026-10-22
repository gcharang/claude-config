# arxiv_to_md/

arXiv paper to markdown conversion workflows.

## Files

| File           | What                                                        | When to read                                                    |
| -------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| `main.py`      | Orchestrator steps and their arguments                      | Debugging orchestration flow, changing step arguments           |
| `convert.py`   | One-paper converter: fetch, unpack, preprocess, pandoc, clean, write | Debugging a conversion, changing limits or the output lines |
| `sub_agent.py` | Review sub-agent brief and the flagged lines of one file    | Changing the residual-LaTeX review                              |
| `tex_utils.py` | TeX preprocessing, input expansion inside the source tree, encoding normalization | Debugging preprocessing, modifying TeX handling |
| `__init__.py`  | Package marker                                              | Never (empty module)                                            |
| `README.md`    | Working directory, untrusted-source handling                | Changing paths, extraction, pandoc flags or destination writes  |
