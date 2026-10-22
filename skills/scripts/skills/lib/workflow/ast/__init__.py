"""AST module for workflow output representation.

Simplified exports: only the node types actually used by skills.
"""

from skills.lib.workflow.ast.builder import ASTBuilder, W
from skills.lib.workflow.ast.dispatch import TemplateDispatchNode
from skills.lib.workflow.ast.dispatch_renderer import render_template_dispatch
from skills.lib.workflow.ast.nodes import (
    CodeNode,
    CurrentActionNode,
    Document,
    ElementNode,
    FileContentNode,
    InvokeAfterNode,
    Node,
    StepHeaderNode,
    TextNode,
)
from skills.lib.workflow.ast.renderer import (
    XMLRenderer,
    render,
    render_current_action,
    render_invoke_after,
    render_step_header,
)

__all__ = [
    # Builder
    "ASTBuilder",
    "CodeNode",
    "CurrentActionNode",
    "Document",
    "ElementNode",
    "FileContentNode",
    "InvokeAfterNode",
    # Core nodes
    "Node",
    # Workflow nodes
    "StepHeaderNode",
    # Dispatch nodes
    "TemplateDispatchNode",
    "TextNode",
    "W",
    # Renderer
    "XMLRenderer",
    "render",
    "render_current_action",
    "render_invoke_after",
    # Workflow renderers
    "render_step_header",
    # Dispatch renderers
    "render_template_dispatch",
]
