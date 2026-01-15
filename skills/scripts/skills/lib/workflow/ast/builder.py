"""Fluent builder API for constructing AST nodes.

WHY BUILDER EXISTS:
Direct construction requires knowing field names and types. Builder provides
fluent API with autocomplete, reducing cognitive load for skill authors.

WHY IMMUTABLE PATTERN:
Each builder method returns NEW builder with accumulated node. No mutable
state shared between calls. Functional style aligns with user preference.

WHY VARARGS:
W.guidance("forbidden", W.text("X"), W.text("Y")) reads naturally without
list literal syntax. Builder collects varargs into children list internally.
"""

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


class ASTBuilder:
    """Immutable builder for constructing AST documents.

    Each method returns a NEW builder instance with the accumulated node.
    Call .build() at the end to collect accumulated nodes into Document.

    Example:
        W.header(script="x", step=1, total=5).text("Action").build()
        -> Document(children=[HeaderNode(...), TextNode("Action")])
    """

    def __init__(self, nodes: list[Node] | None = None):
        """Initialize builder with optional accumulated nodes."""
        self._nodes = nodes if nodes is not None else []

    def text(self, content: str) -> 'ASTBuilder':
        """Add text node and return new builder."""
        return ASTBuilder(self._nodes + [TextNode(content)])

    def code(self, content: str, language: str | None = None) -> 'ASTBuilder':
        """Add code node and return new builder."""
        return ASTBuilder(self._nodes + [CodeNode(content, language)])

    def raw(self, content: str) -> 'ASTBuilder':
        """Add raw node and return new builder."""
        return ASTBuilder(self._nodes + [RawNode(content)])

    def el(self, tag: str, *children: Node, **attrs: str) -> 'ASTBuilder':
        """Add element node and return new builder.

        Args:
            tag: XML tag name
            *children: Child nodes (varargs)
            **attrs: Element attributes (kwargs)
        """
        return ASTBuilder(self._nodes + [ElementNode(tag, attrs, list(children))])

    def header(
        self,
        script: str,
        step: int,
        total: int,
        title: str | None = None
    ) -> 'ASTBuilder':
        """Add header node and return new builder."""
        return ASTBuilder(self._nodes + [HeaderNode(script, step, total, title)])

    def actions(self, *children: Node) -> 'ASTBuilder':
        """Add actions node and return new builder."""
        return ASTBuilder(self._nodes + [ActionsNode(list(children))])

    def command(self, directive: str, cmd: str | None = None) -> 'ASTBuilder':
        """Add command node and return new builder."""
        return ASTBuilder(self._nodes + [CommandNode(directive, cmd)])

    def routing(self, *branches: tuple[str, list[Node]]) -> 'ASTBuilder':
        """Add routing node and return new builder."""
        return ASTBuilder(self._nodes + [RoutingNode(list(branches))])

    def dispatch(
        self,
        agent: str,
        *instruction: Node,
        model: str | None = None
    ) -> 'ASTBuilder':
        """Add dispatch node and return new builder."""
        return ASTBuilder(
            self._nodes + [DispatchNode(agent, model, list(instruction))]
        )

    def guidance(self, kind: str, *children: Node) -> 'ASTBuilder':
        """Add guidance node and return new builder."""
        return ASTBuilder(self._nodes + [GuidanceNode(kind, list(children))])

    def text_output(
        self,
        step: int,
        total: int,
        title: str,
        actions: list[str],
        brief: str | None = None,
        next_title: str | None = None,
        invoke_after: str | None = None,
    ) -> 'ASTBuilder':
        """Add text output node for plain text workflows."""
        return ASTBuilder(self._nodes + [TextOutputNode(step, total, title, actions, brief, next_title, invoke_after)])

    def build(self) -> Document:
        """Collect accumulated nodes into Document."""
        return Document(children=self._nodes)


W = ASTBuilder()
