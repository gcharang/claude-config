"""Plain-text prompt building blocks for workflows.

Prompts as strings composed via f-strings. No XML, no AST.
"""

from skills.lib.workflow.prompts.subagent import (
    # Building blocks
    task_tool_instruction,
    sub_agent_invoke,
    parallel_constraint,
    # Dispatch templates
    subagent_dispatch,
    template_dispatch,
    roster_dispatch,
)

__all__ = [
    # Building blocks
    "task_tool_instruction",
    "sub_agent_invoke",
    "parallel_constraint",
    # Dispatch templates
    "subagent_dispatch",
    "template_dispatch",
    "roster_dispatch",
]
