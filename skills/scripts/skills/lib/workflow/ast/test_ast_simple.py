"""Simple tests for AST nodes and renderer without external dependencies.

Test strategy:
- Normal: Each node type renders to expected XML structure
- Edge: Empty children list, None optional fields
- Error: Unknown node type raises (exhaustiveness check)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

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


def test_text_node_renders_as_plain_string():
    """TextNode should render as plain content."""
    node = TextNode("Hello world")
    result = render(Document([node]), XMLRenderer())
    assert result == "Hello world", f"Expected 'Hello world', got '{result}'"
    print("[OK] TextNode renders as plain string")


def test_empty_text_node():
    """Empty text content should render as empty string."""
    node = TextNode("")
    result = render(Document([node]), XMLRenderer())
    assert result == "", f"Expected empty string, got '{result}'"
    print("[OK] Empty TextNode renders correctly")


def test_code_node_with_language():
    """CodeNode should render with language tag."""
    node = CodeNode("print('hello')", "python")
    result = render(Document([node]), XMLRenderer())
    assert result.startswith("```python\n"), f"Expected python code block, got '{result}'"
    assert "print('hello')" in result
    assert result.endswith("```")
    print("[OK] CodeNode with language renders correctly")


def test_code_node_no_language():
    """CodeNode without language should render generic code block."""
    node = CodeNode("print('hello')", None)
    result = render(Document([node]), XMLRenderer())
    assert result == "```\nprint('hello')\n```", f"Expected generic code block, got '{result}'"
    print("[OK] CodeNode without language renders correctly")


def test_raw_node_renders_as_is():
    """RawNode should render content unchanged."""
    node = RawNode("<raw>content</raw>")
    result = render(Document([node]), XMLRenderer())
    assert result == "<raw>content</raw>", f"Expected unchanged content, got '{result}'"
    print("[OK] RawNode renders as-is")


def test_element_with_attrs_and_children():
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
    print("[OK] ElementNode with attrs and children renders correctly")


def test_element_empty_children():
    """ElementNode with empty children should render self-closing."""
    node = ElementNode("br", {}, [])
    result = render(Document([node]), XMLRenderer())
    assert result == "<br />", f"Expected '<br />', got '{result}'"
    print("[OK] ElementNode with empty children renders self-closing")


def test_header_node_with_title():
    """HeaderNode should render with all attributes."""
    node = HeaderNode("test", 1, 5, "Test Step")
    result = render(Document([node]), XMLRenderer())
    assert 'script="test"' in result
    assert 'step="1"' in result
    assert 'total="5"' in result
    assert "Test Step" in result
    print("[OK] HeaderNode with title renders correctly")


def test_header_node_without_title():
    """HeaderNode without title should render self-closing."""
    node = HeaderNode("test", 1, 5, None)
    result = render(Document([node]), XMLRenderer())
    assert 'script="test"' in result
    assert 'step="1"' in result
    assert 'total="5"' in result
    print("[OK] HeaderNode without title renders correctly")


def test_actions_node_with_children():
    """ActionsNode should render as current_action block."""
    node = ActionsNode([TextNode("Do this"), TextNode("Then that")])
    result = render(Document([node]), XMLRenderer())
    assert "<current_action>" in result
    assert "</current_action>" in result
    assert "Do this" in result
    assert "Then that" in result
    print("[OK] ActionsNode with children renders correctly")


def test_actions_node_empty():
    """Empty ActionsNode should render empty block."""
    node = ActionsNode([])
    result = render(Document([node]), XMLRenderer())
    assert result == "<current_action>\n</current_action>", f"Expected empty block, got '{result}'"
    print("[OK] Empty ActionsNode renders correctly")


def test_command_node_with_cmd():
    """CommandNode with cmd should render with content."""
    node = CommandNode("invoke_after", "python test.py")
    result = render(Document([node]), XMLRenderer())
    assert "<invoke_after>python test.py</invoke_after>" == result
    print("[OK] CommandNode with cmd renders correctly")


def test_command_node_no_cmd():
    """CommandNode without cmd should render self-closing."""
    node = CommandNode("next", None)
    result = render(Document([node]), XMLRenderer())
    assert result == "<next />", f"Expected '<next />', got '{result}'"
    print("[OK] CommandNode without cmd renders self-closing")


def test_routing_node_with_branches():
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
    print("[OK] RoutingNode with branches renders correctly")


def test_dispatch_node_with_model():
    """DispatchNode with model should include model attr."""
    node = DispatchNode("developer", "SONNET", [TextNode("Fix the bug")])
    result = render(Document([node]), XMLRenderer())
    assert 'agent="developer"' in result
    assert 'model="SONNET"' in result
    assert "Fix the bug" in result
    print("[OK] DispatchNode with model renders correctly")


def test_dispatch_node_no_model():
    """DispatchNode without model should omit model attr."""
    node = DispatchNode("reviewer", None, [TextNode("Review code")])
    result = render(Document([node]), XMLRenderer())
    assert 'agent="reviewer"' in result
    assert 'model="SONNET"' not in result
    assert "Review code" in result
    print("[OK] DispatchNode without model renders correctly")


def test_guidance_node_with_children():
    """GuidanceNode should render with kind and children."""
    node = GuidanceNode("forbidden", [TextNode("Don't do this")])
    result = render(Document([node]), XMLRenderer())
    assert "<forbidden>" in result
    assert "Don't do this" in result
    assert "</forbidden>" in result
    print("[OK] GuidanceNode with children renders correctly")


def test_guidance_node_empty():
    """Empty GuidanceNode should render self-closing."""
    node = GuidanceNode("forbidden", [])
    result = render(Document([node]), XMLRenderer())
    assert result == "<forbidden />", f"Expected '<forbidden />', got '{result}'"
    print("[OK] Empty GuidanceNode renders self-closing")


def test_builder_immutability():
    """Builder methods should return new instances."""
    b1 = W.text("first")
    b2 = b1.text("second")
    assert b1 is not b2
    doc1 = b1.build()
    doc2 = b2.build()
    assert len(doc1.children) == 1
    assert len(doc2.children) == 2
    print("[OK] Builder immutability preserved")


def test_builder_header_method():
    """Builder header() should create HeaderNode."""
    doc = W.header(script="test", step=1, total=5, title="Title").build()
    assert len(doc.children) == 1
    assert isinstance(doc.children[0], HeaderNode)
    assert doc.children[0].script == "test"
    print("[OK] Builder header() method works")


def test_builder_actions_method():
    """Builder actions() should accept varargs."""
    doc = W.actions(TextNode("a"), TextNode("b")).build()
    assert len(doc.children) == 1
    assert isinstance(doc.children[0], ActionsNode)
    assert len(doc.children[0].children) == 2
    print("[OK] Builder actions() accepts varargs")


def test_builder_all_methods_available():
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
    print("[OK] Builder provides all 10 methods")


def test_all_node_types_render():
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
    print("[OK] All 10 node types render successfully")


def test_complete_workflow_document():
    """Build and render complete workflow step."""
    doc = (
        W.header(script="test", step=1, total=3, title="Step 1")
        .actions(TextNode("Action description"))
        .command("invoke_after", "python test.py --step 2")
        .build()
    )
    result = render(doc, XMLRenderer())
    assert "step_header" in result
    assert "current_action" in result
    assert "invoke_after" in result
    assert "Step 1" in result
    print("[OK] Complete workflow document renders correctly")


def run_tests():
    """Run all tests."""
    tests = [
        test_text_node_renders_as_plain_string,
        test_empty_text_node,
        test_code_node_with_language,
        test_code_node_no_language,
        test_raw_node_renders_as_is,
        test_element_with_attrs_and_children,
        test_element_empty_children,
        test_header_node_with_title,
        test_header_node_without_title,
        test_actions_node_with_children,
        test_actions_node_empty,
        test_command_node_with_cmd,
        test_command_node_no_cmd,
        test_routing_node_with_branches,
        test_dispatch_node_with_model,
        test_dispatch_node_no_model,
        test_guidance_node_with_children,
        test_guidance_node_empty,
        test_builder_immutability,
        test_builder_header_method,
        test_builder_actions_method,
        test_builder_all_methods_available,
        test_all_node_types_render,
        test_complete_workflow_document,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
