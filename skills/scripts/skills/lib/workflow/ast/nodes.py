"""AST node types for workflow output representation.

WHY FROZEN DATACLASSES:
Immutability aligns with FP style, prevents accidental mutation, and enables
safe sharing of nodes between renders and caching.

WHY FLAT UNION:
Workflow output is sequential composition (Header + Actions + Command), not
nested prose. Flat union with children: list[Node] matches actual patterns
better than layered inline/block distinction.

WHY SEPARATE DATACLASS PER TYPE:
Type-safe field access with IDE autocomplete. More explicit than shared attrs
dict. Standard Python pattern for discriminated unions.
"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TextNode:
    """Plain text content node."""
    content: str


@dataclass(frozen=True)
class CodeNode:
    """Code block with optional language tag."""
    content: str
    language: str | None = None


@dataclass(frozen=True)
class RawNode:
    """Escape hatch for content that couldn't be structured.

    WHY RAWNODE EXISTS:
    Distinguishes "couldn't structure this" from intentional text (TextNode).
    Tracking raw_nodes/total_nodes ratio identifies when AST needs extension.
    """
    content: str


@dataclass(frozen=True)
class ElementNode:
    """Generic XML element with attributes and children."""
    tag: str
    attrs: dict[str, str]
    children: list['Node']


@dataclass(frozen=True)
class HeaderNode:
    """Step header with script metadata."""
    script: str
    step: int
    total: int
    title: str | None = None


@dataclass(frozen=True)
class ActionsNode:
    """Container for current action content."""
    children: list['Node']


@dataclass(frozen=True)
class CommandNode:
    """Workflow command directive."""
    directive: str
    cmd: str | None = None


@dataclass(frozen=True)
class RoutingNode:
    """Conditional routing with multiple branches."""
    branches: list[tuple[str, list['Node']]]


@dataclass(frozen=True)
class DispatchNode:
    """Sub-agent dispatch instruction."""
    agent: str
    model: str | None
    instruction: list['Node']


@dataclass(frozen=True)
class GuidanceNode:
    """Guidance block (forbidden, constraints, principles)."""
    kind: str
    children: list['Node']


@dataclass(frozen=True)
class TextOutputNode:
    """Plain text step output (no XML wrapping).

    WHY TEXTOUTPUTNODE EXISTS:
    Escape hatch for workflows that output plain text instead of XML.
    Captures semantic structure while rendering as human-readable text.
    Enables introspection while preserving text-mode workflows.
    """
    step: int
    total: int
    title: str
    actions: list[str]
    brief: str | None = None
    next_title: str | None = None
    invoke_after: str | None = None


Node = Union[
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
]


@dataclass(frozen=True)
class Document:
    """Container for rendered output.

    WHY SEPARATE FROM NODE:
    Document is return type from build(), not a renderable node.
    Mixing container and content types in same union would require
    special-case matching. Separate types keep renderer logic clean.
    """
    children: list[Node]
