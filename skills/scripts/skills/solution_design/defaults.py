#!/usr/bin/env python3
"""
Default evaluation criteria for solution-design skill.

Single source of truth for default criteria when problem/project inference
produces nothing. Used by Calibrate step as fallback.
"""

DEFAULT_CRITERIA = {
    "viability": {
        "criteria": [
            "Addresses root cause through clear mechanism",
            "Respects all hard constraints",
            "Is implementable with reasonable effort",
        ]
    },
    "flaw_severity": {
        "fatal": [
            "Does not address root cause",
            "Violates hard constraint",
            "Creates problem worse than original",
        ],
        "significant": [
            "Substantial soft-constraint violation",
            "Requires unavailable resources",
        ],
        "minor": [
            "Manageable downside with workaround",
            "Acceptable complexity increase",
        ],
    },
    "tradeoff_dimensions": {
        "primary": ["complexity", "risk", "reversibility", "scope"],
        "secondary": ["learning_curve", "dependencies", "testability"],
    },
    "synthesis_threshold": {
        "minimum_solutions": 3,
        "theme_strength": "strong",
        "appetite": "conservative",
    },
}


def format_default_viability() -> str:
    """Format default viability criteria as XML."""
    lines = ['<viability_definition source="default">']
    lines.append("  <criteria>")
    for c in DEFAULT_CRITERIA["viability"]["criteria"]:
        lines.append(f"    <criterion>{c}</criterion>")
    lines.append("  </criteria>")
    lines.append("</viability_definition>")
    return "\n".join(lines)


def format_default_flaw_severity() -> str:
    """Format default flaw severity as XML."""
    fs = DEFAULT_CRITERIA["flaw_severity"]
    lines = ['<flaw_severity source="default">']
    lines.append("  <fatal_conditions>")
    for c in fs["fatal"]:
        lines.append(f"    <condition>{c}</condition>")
    lines.append("  </fatal_conditions>")
    lines.append("  <significant_conditions>")
    for c in fs["significant"]:
        lines.append(f"    <condition>{c}</condition>")
    lines.append("  </significant_conditions>")
    lines.append("  <minor_conditions>")
    for c in fs["minor"]:
        lines.append(f"    <condition>{c}</condition>")
    lines.append("  </minor_conditions>")
    lines.append("</flaw_severity>")
    return "\n".join(lines)


def format_default_tradeoff_dimensions() -> str:
    """Format default trade-off dimensions as XML."""
    td = DEFAULT_CRITERIA["tradeoff_dimensions"]
    lines = ['<tradeoff_dimensions source="default">']
    lines.append("  <primary_dimensions>")
    for d in td["primary"]:
        lines.append(f'    <dimension name="{d}" weight="medium"/>')
    lines.append("  </primary_dimensions>")
    lines.append("  <secondary_dimensions>")
    for d in td["secondary"]:
        lines.append(f'    <dimension name="{d}"/>')
    lines.append("  </secondary_dimensions>")
    lines.append("</tradeoff_dimensions>")
    return "\n".join(lines)


def format_default_synthesis_threshold() -> str:
    """Format default synthesis threshold as XML."""
    st = DEFAULT_CRITERIA["synthesis_threshold"]
    lines = ['<synthesis_threshold source="default">']
    lines.append(f"  <minimum_solutions_for_theme>{st['minimum_solutions']}</minimum_solutions_for_theme>")
    lines.append(f"  <theme_strength_required>{st['theme_strength']}</theme_strength_required>")
    lines.append(f"  <synthesize_appetite>{st['appetite']}</synthesize_appetite>")
    lines.append("</synthesis_threshold>")
    return "\n".join(lines)


def format_all_defaults() -> str:
    """Format all default criteria as XML block."""
    lines = ['<default_evaluation_criteria>']
    lines.append("")
    lines.append(format_default_viability())
    lines.append("")
    lines.append(format_default_flaw_severity())
    lines.append("")
    lines.append(format_default_tradeoff_dimensions())
    lines.append("")
    lines.append(format_default_synthesis_threshold())
    lines.append("")
    lines.append("</default_evaluation_criteria>")
    return "\n".join(lines)
