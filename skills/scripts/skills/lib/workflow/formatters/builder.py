"""XML builder utilities for workflow formatters.

Provides a simpler API for building XML strings without manual
list manipulation. Can be adopted incrementally.

Usage:
    # Simple tag wrapping
    xml = wrap_xml("current_action", *actions)

    # With attributes
    xml = wrap_xml("step_header", title, script="planner", step="1")

    # Builder for complex construction
    xml = (XMLBuilder()
        .tag_open("workflow")
        .append(format_current_action(actions))
        .blank()
        .append(format_invoke_after(cmd))
        .tag_close("workflow")
        .build())
"""


def wrap_xml(tag: str, *content: str, **attrs: str) -> str:
    """Wrap content lines in an XML tag.

    Args:
        tag: XML tag name
        *content: Lines to include between tags
        **attrs: Tag attributes (underscores converted to hyphens)

    Returns:
        XML string with opening tag, content lines, and closing tag
    """
    attr_str = ""
    if attrs:
        # Convert foo_bar="x" to foo-bar="x" for XML attribute naming
        formatted = [f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()]
        attr_str = " " + " ".join(formatted)
    lines = [f"<{tag}{attr_str}>"]
    lines.extend(content)
    lines.append(f"</{tag}>")
    return "\n".join(lines)


class XMLBuilder:
    """Fluent builder for XML string construction."""

    def __init__(self):
        self._lines: list[str] = []

    def line(self, text: str) -> "XMLBuilder":
        """Add a line of text."""
        self._lines.append(text)
        return self

    def lines(self, *texts: str) -> "XMLBuilder":
        """Add multiple lines of text."""
        self._lines.extend(texts)
        return self

    def blank(self) -> "XMLBuilder":
        """Add a blank line."""
        self._lines.append("")
        return self

    def append(self, text: str) -> "XMLBuilder":
        """Add pre-formatted text (may contain newlines)."""
        if text:
            self._lines.append(text)
        return self

    def tag_open(self, tag: str, **attrs: str) -> "XMLBuilder":
        """Add an opening XML tag."""
        attr_str = ""
        if attrs:
            formatted = [f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()]
            attr_str = " " + " ".join(formatted)
        self._lines.append(f"<{tag}{attr_str}>")
        return self

    def tag_close(self, tag: str) -> "XMLBuilder":
        """Add a closing XML tag."""
        self._lines.append(f"</{tag}>")
        return self

    def tag(self, tag: str, content: str, **attrs: str) -> "XMLBuilder":
        """Add a complete tag with inline content."""
        attr_str = ""
        if attrs:
            formatted = [f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items()]
            attr_str = " " + " ".join(formatted)
        self._lines.append(f"<{tag}{attr_str}>{content}</{tag}>")
        return self

    def build(self) -> str:
        """Return the assembled XML string."""
        return "\n".join(self._lines)
