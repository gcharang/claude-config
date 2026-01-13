# formatters/

Output formatters for workflow step rendering.

## Files

| File          | What                                | When to read                                         |
| ------------- | ----------------------------------- | ---------------------------------------------------- |
| `__init__.py` | Package exports                     | Checking available formatters                        |
| `builder.py`  | Command string builders             | Generating invoke commands, modifying command format |
| `text.py`     | Plain text step output              | Modifying text output format, adding text sections   |
| `xml.py`      | XML-tagged step output with prompts | Modifying XML structure, adding prompt sections      |
