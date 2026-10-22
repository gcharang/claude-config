"""Renderer for dispatch node types.

Separate from ast/renderer.py because:
1. Substitution scope: Template variable substitution ($var) is dispatch-specific.
   Generic ElementNode rendering should never perform substitution.
2. Expansion semantics: Dispatch rendering EXPANDS N nodes from 1 template.
   Generic rendering operates 1:1 (one node -> one output).
3. Dispatch-only concerns: model selection and the parallel-execution constraint
   are rendered here and stay out of core AST.
"""
from xml.sax.saxutils import quoteattr

from skills.lib.workflow.ast.dispatch import TemplateDispatchNode
from skills.lib.workflow.prompts.step import pin_cwd
from skills.lib.workflow.prompts.subagent import expand_template_pairs, parallel_constraint


def _expand_template_targets(
    template: str, command: str, targets: tuple[dict[str, str], ...]
) -> list[dict[str, str]]:
    """Expand template+command for each target with substituted values.

    Substitution happens here, not in render_template_dispatch, so render
    functions only assemble XML from pre-expanded data. Thin wrapper over the
    shared expand_template_pairs -- see it for the $var contract and the "$$"
    literal-escape rule.
    """
    return expand_template_pairs(template, command, targets)


def _build_execution_constraint(count: int) -> str:
    """Wrap the shared parallel-dispatch instruction in an execution_constraint element."""
    return f"  <execution_constraint>\n{parallel_constraint(count)}\n  </execution_constraint>"


def _build_model_selection(model: str | None) -> str:
    """Build model selection guidance XML.

    Always emits explicit guidance, even when model is None. This prevents
    LLM pattern-matching errors where model selection from a previous step
    (e.g., "use HAIKU for Explore agents") incorrectly propagates to
    subsequent steps that have no explicit model requirement.

    Silent omission (returning "") leaves the LLM to infer from prior context.
    Explicit "use default" provides a counter-signal that breaks the
    pattern-matching chain.
    """
    if model is None:
        lines = [
            "  <model_selection>",
            "    Use DEFAULT model (omit model parameter from Agent tool).",
            "    Do NOT carry forward model selections from previous steps.",
            "  </model_selection>",
        ]
        return "\n".join(lines)
    lines = [
        "  <model_selection>",
        f"    Set model: {model} on every Agent tool call.",
        "  </model_selection>",
    ]
    return "\n".join(lines)


def render_template_dispatch(node: TemplateDispatchNode) -> str:
    """Render template dispatch with SIMD pattern.

    Orchestrates expansion -> assembly pipeline.
    All targets are expanded at render time; LLM sees final prompts.

    Args:
        node: TemplateDispatchNode with template and targets

    Returns:
        XML string with parallel_dispatch structure

    Raises:
        ValueError: If node.targets is empty (cannot dispatch zero agents)
    """
    if not node.targets:
        raise ValueError(
            f"TemplateDispatchNode.targets cannot be empty. Agent type: {node.agent_type}"
        )

    expanded = _expand_template_targets(node.template, node.command, node.targets)
    count = len(expanded)

    lines = [f'<parallel_dispatch agent={quoteattr(node.agent_type)} count="{count}">']

    if node.instruction:
        lines.append("  <instruction>")
        lines.append(f"    {node.instruction}")
        lines.append("  </instruction>")
        lines.append("")

    lines.append(_build_execution_constraint(count))
    lines.append("")
    lines.append(_build_model_selection(node.model))
    lines.append("")

    lines.append("  <agents>")
    for i, e in enumerate(expanded, 1):
        lines.append(f'    <agent index="{i}">')

        if e["prompt"]:
            lines.append("      <prompt>")
            for prompt_line in e["prompt"].split("\n"):
                lines.append(f"        {prompt_line}" if prompt_line else "")
            lines.append("      </prompt>")

        lines.append(f'      <invoke cmd={quoteattr(pin_cwd(e["command"]))} />')
        lines.append("    </agent>")
    lines.append("  </agents>")

    lines.append("</parallel_dispatch>")

    return "\n".join(lines)


__all__ = ["render_template_dispatch"]
