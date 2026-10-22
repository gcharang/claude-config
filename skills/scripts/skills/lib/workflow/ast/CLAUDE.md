# ast/

AST nodes, builder and renderers for workflow XML step output.

## Files

| File                    | What                                                                  | When to read                           |
| ----------------------- | --------------------------------------------------------------------- | -------------------------------------- |
| `README.md`             | Architecture, design decisions, invariants, extension guide           | Understanding why flat union + builder |
| `nodes.py`              | Base and specialized node types                                       | Adding/understanding node types        |
| `builder.py`            | `W.el(...)` fluent builder API                                        | Constructing AST nodes                 |
| `renderer.py`           | `XMLRenderer`, `render()`, `render_invoke_after()`                    | Rendering AST to XML output            |
| `dispatch.py`           | `TemplateDispatchNode`                                                | Parallel sub-agent dispatch            |
| `dispatch_renderer.py`  | `render_template_dispatch()`                                          | Rendering dispatch XML                 |
| `__init__.py`           | Public API exports                                                    | Importing AST types and renderers      |
