"""Renderer for converting AST to string output.

WHY EXTERNAL FUNCTION:
External render(doc, renderer) pattern allows multiple dispatch without
coupling nodes to renderer interface. Easier to add new renderers.

WHY MATCH STATEMENT:
Python 3.10 match with type narrowing. Adding new node type causes runtime
error if case missing. assertNever pattern catches exhaustiveness at test time.

WHY RENDERER PROTOCOL:
Abstract interface for renderers. Multiple implementations (XML, plain text,
JSON) can implement same interface.
"""

from typing import Protocol, Never
from skills.lib.workflow.ast.nodes import (
    Node,
    Document,
    TextNode,
    CodeNode,
    RawNode,
    ElementNode,
    HeaderNode,
    ActionsNode,
    CommandNode,
    RoutingNode,
    DispatchNode,
    GuidanceNode,
    TextOutputNode,
)


def assertNever(value: Never) -> Never:
    """Exhaustiveness check for match statements.

    If this function is reached, it means a case was not handled in the
    match statement. Used to ensure all node types are covered.
    """
    raise AssertionError(f"Unhandled node type: {type(value).__name__}")


class Renderer(Protocol):
    """Abstract renderer interface."""

    def render_text(self, node: TextNode) -> str: ...
    def render_code(self, node: CodeNode) -> str: ...
    def render_raw(self, node: RawNode) -> str: ...
    def render_element(self, node: ElementNode) -> str: ...
    def render_header(self, node: HeaderNode) -> str: ...
    def render_actions(self, node: ActionsNode) -> str: ...
    def render_command(self, node: CommandNode) -> str: ...
    def render_routing(self, node: RoutingNode) -> str: ...
    def render_dispatch(self, node: DispatchNode) -> str: ...
    def render_guidance(self, node: GuidanceNode) -> str: ...
    def render_text_output(self, node: TextOutputNode) -> str: ...


class XMLRenderer:
    """Renders AST nodes to XML format matching existing formatter output."""

    def render_text(self, node: TextNode) -> str:
        """Render text node as plain string."""
        return node.content

    def render_code(self, node: CodeNode) -> str:
        """Render code node as code block."""
        if node.language:
            return f"```{node.language}\n{node.content}\n```"
        return f"```\n{node.content}\n```"

    def render_raw(self, node: RawNode) -> str:
        """Render raw node as-is."""
        return node.content

    def render_element(self, node: ElementNode) -> str:
        """Render generic element with attributes and children."""
        attrs_str = ""
        if node.attrs:
            attrs_str = " " + " ".join(f'{k}="{v}"' for k, v in node.attrs.items())

        if not node.children:
            return f"<{node.tag}{attrs_str} />"

        children_str = "\n".join(self._render_node(child) for child in node.children)
        return f"<{node.tag}{attrs_str}>\n{children_str}\n</{node.tag}>"

    def render_header(self, node: HeaderNode) -> str:
        """Render step header matching format_step_header output."""
        attrs = [f'script="{node.script}"', f'step="{node.step}"', f'total="{node.total}"']
        attrs_str = " ".join(attrs)

        if node.title:
            return f'<step_header {attrs_str}>{node.title}</step_header>'
        return f'<step_header {attrs_str} />'

    def render_actions(self, node: ActionsNode) -> str:
        """Render actions block matching format_current_action output."""
        if not node.children:
            return "<current_action>\n</current_action>"

        children_str = "\n".join(self._render_node(child) for child in node.children)
        return f"<current_action>\n{children_str}\n</current_action>"

    def render_command(self, node: CommandNode) -> str:
        """Render command directive."""
        if node.cmd:
            return f"<{node.directive}>{node.cmd}</{node.directive}>"
        return f"<{node.directive} />"

    def render_routing(self, node: RoutingNode) -> str:
        """Render routing block with branches."""
        parts = ["<routing>"]
        for label, children in node.branches:
            children_str = "\n".join(self._render_node(child) for child in children)
            parts.append(f'  <branch label="{label}">')
            parts.append(f"    {children_str}")
            parts.append("  </branch>")
        parts.append("</routing>")
        return "\n".join(parts)

    def render_dispatch(self, node: DispatchNode) -> str:
        """Render dispatch block."""
        attrs = f'agent="{node.agent}"'
        if node.model:
            attrs += f' model="{node.model}"'

        parts = [f"<dispatch {attrs}>"]
        for child in node.instruction:
            parts.append(f"  {self._render_node(child)}")
        parts.append("</dispatch>")
        return "\n".join(parts)

    def render_guidance(self, node: GuidanceNode) -> str:
        """Render guidance block (forbidden, constraints, etc)."""
        if not node.children:
            return f"<{node.kind} />"

        parts = [f"<{node.kind}>"]
        for child in node.children:
            parts.append(f"  {self._render_node(child)}")
        parts.append(f"</{node.kind}>")
        return "\n".join(parts)

    def render_text_output(self, node: TextOutputNode) -> str:
        """Render text output node for plain text workflows.

        FOOTER PRECEDENCE: invoke_after > next_title > completion message.
        If multiple are provided, only the highest precedence renders.
        Callers should provide exactly one of: invoke_after, next_title, or neither.
        """
        parts = [f"STEP {node.step}/{node.total}: {node.title}"]

        if node.brief:
            parts.append(node.brief)

        parts.append("")
        parts.append("DO:")
        for action in node.actions:
            parts.append(f"  {action}")

        parts.append("")
        if node.invoke_after:
            parts.append(f"INVOKE AFTER: {node.invoke_after}")
        elif node.next_title:
            parts.append(f"NEXT: Step {node.step + 1} - {node.next_title}")
        else:
            parts.append("WORKFLOW COMPLETE")

        return "\n".join(parts)

    def _render_node(self, node: Node) -> str:
        """Dispatch node to appropriate render method."""
        match node:
            case TextNode():
                return self.render_text(node)
            case CodeNode():
                return self.render_code(node)
            case RawNode():
                return self.render_raw(node)
            case ElementNode():
                return self.render_element(node)
            case HeaderNode():
                return self.render_header(node)
            case ActionsNode():
                return self.render_actions(node)
            case CommandNode():
                return self.render_command(node)
            case RoutingNode():
                return self.render_routing(node)
            case DispatchNode():
                return self.render_dispatch(node)
            case GuidanceNode():
                return self.render_guidance(node)
            case TextOutputNode():
                return self.render_text_output(node)
            case _:
                assertNever(node)


def render(doc: Document, renderer: Renderer) -> str:
    """Render document using provided renderer.

    WHY EXTERNAL FUNCTION:
    Separation of concerns - Document doesn't need to know about renderers.
    Easier to add new renderers without modifying Document class.

    Args:
        doc: Document to render
        renderer: Renderer implementation (XMLRenderer, etc)

    Returns:
        Rendered string output
    """
    if isinstance(renderer, XMLRenderer):
        parts = [renderer._render_node(child) for child in doc.children]
        return "\n".join(parts)

    raise NotImplementedError(f"Renderer {type(renderer).__name__} not implemented")
