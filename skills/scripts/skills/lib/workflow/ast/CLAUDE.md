# ast/

AST module for workflow output representation with builder API and pluggable renderers.

## Files

| File          | What                                               | When to read                                    |
| ------------- | -------------------------------------------------- | ----------------------------------------------- |
| `README.md`   | Architecture, data flow, invariants, tradeoffs     | Understanding AST design, extending renderers   |
| `nodes.py`    | Node type definitions (11 frozen dataclasses)      | Adding node types, understanding node structure |
| `builder.py`  | Fluent builder API (W.header(), W.actions(), etc.) | Constructing AST nodes, building workflows      |
| `renderer.py` | XMLRenderer and render() function                  | Implementing new renderers, debugging output    |
| `__init__.py` | Public API exports                                 | Importing AST types, checking available exports |

## Usage

```python
from skills.lib.workflow.ast import W, XMLRenderer, render

# Build AST using fluent API
doc = W.header(script="x", step=1, total=5).actions(
    W.text("Action text"),
    W.code("code_example()", language="python")
).build()

# Render to XML
output = render(doc, XMLRenderer())
```

## Node Types

| Type             | Purpose                                  |
| ---------------- | ---------------------------------------- |
| `TextNode`       | Plain text content                       |
| `CodeNode`       | Code block with optional language        |
| `RawNode`        | Escape hatch for unstructured output     |
| `ElementNode`    | Generic XML element                      |
| `HeaderNode`     | Step header with script metadata         |
| `ActionsNode`    | Container for current action content     |
| `CommandNode`    | Workflow command directive               |
| `RoutingNode`    | Conditional routing with branches        |
| `DispatchNode`   | Sub-agent dispatch instruction           |
| `GuidanceNode`   | Guidance block (forbidden, etc.)         |
| `TextOutputNode` | Plain text step output (no XML wrapping) |
