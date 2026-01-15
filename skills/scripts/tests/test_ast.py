"""Property-based tests for AST nodes and renderer.

Test strategy:
- Normal: Each node type renders to expected XML structure
- Edge: Empty children list, None optional fields
- Error: Unknown node type raises (exhaustiveness check)
- Use hypothesis for generative testing
"""

import pytest
from hypothesis import given, strategies as st

from skills.lib.workflow.ast import (
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
    ASTBuilder,
    XMLRenderer,
    render,
    W,
)


# Strategy builders for generative testing
@st.composite
def text_node(draw):
    """Generate TextNode with arbitrary content."""
    content = draw(st.text(min_size=0, max_size=100))
    return TextNode(content)


@st.composite
def code_node(draw):
    """Generate CodeNode with optional language."""
    content = draw(st.text(min_size=0, max_size=100))
    language = draw(st.one_of(st.none(), st.sampled_from(["python", "bash", "js"])))
    return CodeNode(content, language)


@st.composite
def raw_node(draw):
    """Generate RawNode with arbitrary content."""
    content = draw(st.text(min_size=1, max_size=100))  # RawNode.content never empty
    return RawNode(content)


@st.composite
def header_node(draw):
    """Generate HeaderNode with optional title."""
    script = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll", "Lu"))))
    step = draw(st.integers(min_value=1, max_value=100))
    total = draw(st.integers(min_value=step, max_value=100))
    title = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    return HeaderNode(script, step, total, title)


@st.composite
def actions_node(draw):
    """Generate ActionsNode with variable children."""
    num_children = draw(st.integers(min_value=0, max_value=3))
    children = [draw(text_node()) for _ in range(num_children)]
    return ActionsNode(children)


@st.composite
def command_node(draw):
    """Generate CommandNode with optional cmd."""
    directive = draw(st.sampled_from(["invoke_after", "next", "execute"]))
    cmd = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    return CommandNode(directive, cmd)


@st.composite
def guidance_node(draw):
    """Generate GuidanceNode with variable children."""
    kind = draw(st.sampled_from(["forbidden", "constraint", "principle"]))
    num_children = draw(st.integers(min_value=0, max_value=3))
    children = [draw(text_node()) for _ in range(num_children)]
    return GuidanceNode(kind, children)


# Tests for individual node types
class TestTextNode:
    """Test TextNode rendering."""

    @given(text_node())
    def test_text_node_renders_as_plain_string(self, node):
        """TextNode should render as plain content."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert result == node.content

    def test_empty_text_node(self):
        """Empty text content should render as empty string."""
        node = TextNode("")
        result = render(Document([node]), XMLRenderer())
        assert result == ""


class TestCodeNode:
    """Test CodeNode rendering."""

    @given(code_node())
    def test_code_node_with_language(self, node):
        """CodeNode should render with language tag if present."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        if node.language:
            assert result.startswith(f"```{node.language}\n")
            assert result.endswith("```")
            assert node.content in result
        else:
            assert result.startswith("```\n")
            assert result.endswith("```")

    def test_code_node_no_language(self):
        """CodeNode without language should render generic code block."""
        node = CodeNode("print('hello')", None)
        result = render(Document([node]), XMLRenderer())
        assert result == "```\nprint('hello')\n```"


class TestRawNode:
    """Test RawNode rendering."""

    @given(raw_node())
    def test_raw_node_renders_as_is(self, node):
        """RawNode should render content unchanged."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert result == node.content


class TestElementNode:
    """Test ElementNode rendering."""

    def test_element_with_attrs_and_children(self):
        """ElementNode with attrs and children should render properly."""
        node = ElementNode(
            "div",
            {"class": "container", "id": "main"},
            [TextNode("content")]
        )
        result = render(Document([node]), XMLRenderer())
        assert '<div class="container" id="main">' in result
        assert "content" in result
        assert "</div>" in result

    def test_element_empty_children(self):
        """ElementNode with empty children should render self-closing."""
        node = ElementNode("br", {}, [])
        result = render(Document([node]), XMLRenderer())
        assert result == "<br />"

    def test_element_no_attrs(self):
        """ElementNode without attrs should render tag only."""
        node = ElementNode("p", {}, [TextNode("text")])
        result = render(Document([node]), XMLRenderer())
        assert result.startswith("<p>\n")
        assert "</p>" in result


class TestHeaderNode:
    """Test HeaderNode rendering."""

    @given(header_node())
    def test_header_node_with_optional_title(self, node):
        """HeaderNode should render with all attributes."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert f'script="{node.script}"' in result
        assert f'step="{node.step}"' in result
        assert f'total="{node.total}"' in result
        if node.title:
            assert node.title in result

    def test_header_node_without_title(self):
        """HeaderNode without title should render self-closing."""
        node = HeaderNode("test", 1, 5, None)
        result = render(Document([node]), XMLRenderer())
        assert 'script="test"' in result
        assert 'step="1"' in result
        assert 'total="5"' in result


class TestActionsNode:
    """Test ActionsNode rendering."""

    @given(actions_node())
    def test_actions_node_with_children(self, node):
        """ActionsNode should render as current_action block."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert "<current_action>" in result
        assert "</current_action>" in result

    def test_actions_node_empty(self):
        """Empty ActionsNode should render empty block."""
        node = ActionsNode([])
        result = render(Document([node]), XMLRenderer())
        assert result == "<current_action>\n</current_action>"


class TestCommandNode:
    """Test CommandNode rendering."""

    @given(command_node())
    def test_command_node_with_optional_cmd(self, node):
        """CommandNode should render directive with optional content."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert node.directive in result
        if node.cmd:
            assert node.cmd in result

    def test_command_node_no_cmd(self):
        """CommandNode without cmd should render self-closing."""
        node = CommandNode("next", None)
        result = render(Document([node]), XMLRenderer())
        assert result == "<next />"


class TestRoutingNode:
    """Test RoutingNode rendering."""

    def test_routing_node_with_branches(self):
        """RoutingNode should render branches with labels."""
        node = RoutingNode([
            ("pass", [TextNode("continue")]),
            ("fail", [TextNode("retry")])
        ])
        result = render(Document([node]), XMLRenderer())
        assert "<routing>" in result
        assert "</routing>" in result
        assert 'label="pass"' in result
        assert 'label="fail"' in result
        assert "continue" in result
        assert "retry" in result

    def test_routing_node_empty_branches(self):
        """RoutingNode with empty branches should render empty routing."""
        node = RoutingNode([])
        result = render(Document([node]), XMLRenderer())
        assert result == "<routing>\n</routing>"


class TestDispatchNode:
    """Test DispatchNode rendering."""

    def test_dispatch_node_with_model(self):
        """DispatchNode with model should include model attr."""
        node = DispatchNode(
            "developer",
            "SONNET",
            [TextNode("Fix the bug")]
        )
        result = render(Document([node]), XMLRenderer())
        assert 'agent="developer"' in result
        assert 'model="SONNET"' in result
        assert "Fix the bug" in result

    def test_dispatch_node_no_model(self):
        """DispatchNode without model should omit model attr."""
        node = DispatchNode(
            "reviewer",
            None,
            [TextNode("Review code")]
        )
        result = render(Document([node]), XMLRenderer())
        assert 'agent="reviewer"' in result
        assert 'model=' not in result
        assert "Review code" in result


class TestGuidanceNode:
    """Test GuidanceNode rendering."""

    @given(guidance_node())
    def test_guidance_node_with_children(self, node):
        """GuidanceNode should render with kind and children."""
        renderer = XMLRenderer()
        result = render(Document([node]), renderer)
        assert f"<{node.kind}>" in result or f"<{node.kind} />" in result

    def test_guidance_node_empty(self):
        """Empty GuidanceNode should render self-closing."""
        node = GuidanceNode("forbidden", [])
        result = render(Document([node]), XMLRenderer())
        assert result == "<forbidden />"


class TestBuilder:
    """Test ASTBuilder fluent API."""

    def test_builder_immutability(self):
        """Builder methods should return new instances."""
        b1 = W.text("first")
        b2 = b1.text("second")
        assert b1 is not b2
        doc1 = b1.build()
        doc2 = b2.build()
        assert len(doc1.children) == 1
        assert len(doc2.children) == 2

    def test_builder_header_method(self):
        """Builder header() should create HeaderNode."""
        doc = W.header(script="test", step=1, total=5, title="Title").build()
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], HeaderNode)
        assert doc.children[0].script == "test"
        assert doc.children[0].step == 1
        assert doc.children[0].total == 5
        assert doc.children[0].title == "Title"

    def test_builder_actions_method(self):
        """Builder actions() should accept varargs."""
        doc = W.actions(TextNode("a"), TextNode("b")).build()
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], ActionsNode)
        assert len(doc.children[0].children) == 2

    def test_builder_guidance_method(self):
        """Builder guidance() should accept kind and varargs."""
        doc = W.guidance("forbidden", TextNode("x"), TextNode("y")).build()
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], GuidanceNode)
        assert doc.children[0].kind == "forbidden"
        assert len(doc.children[0].children) == 2

    def test_builder_all_methods_available(self):
        """Builder should provide all 10 node type methods."""
        b = ASTBuilder()
        assert hasattr(b, "text")
        assert hasattr(b, "code")
        assert hasattr(b, "raw")
        assert hasattr(b, "el")
        assert hasattr(b, "header")
        assert hasattr(b, "actions")
        assert hasattr(b, "command")
        assert hasattr(b, "routing")
        assert hasattr(b, "dispatch")
        assert hasattr(b, "guidance")


class TestExhaustiveness:
    """Test exhaustiveness checking."""

    def test_all_node_types_render(self):
        """All 10 node types should render without error."""
        nodes = [
            TextNode("text"),
            CodeNode("code", "py"),
            RawNode("raw"),
            ElementNode("div", {}, []),
            HeaderNode("test", 1, 5),
            ActionsNode([]),
            CommandNode("next"),
            RoutingNode([]),
            DispatchNode("agent", None, []),
            GuidanceNode("forbidden", []),
        ]
        renderer = XMLRenderer()
        for node in nodes:
            result = render(Document([node]), renderer)
            assert isinstance(result, str)


class TestIntegration:
    """Integration tests for complex documents."""

    def test_complete_workflow_document(self):
        """Build and render complete workflow step."""
        doc = (
            W.header(script="test", step=1, total=3, title="Step 1")
            .actions(
                TextNode("Action description"),
                W.guidance("forbidden", TextNode("Don't do this")).build().children[0]
            )
            .command("invoke_after", "python test.py --step 2")
            .build()
        )
        result = render(doc, XMLRenderer())
        assert "step_header" in result
        assert "current_action" in result
        assert "invoke_after" in result
        assert "Step 1" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
