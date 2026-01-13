"""Convention loading utilities.

Conventions are universal rules used by agents and skills. They live in
.claude/conventions/ (not skill-specific resources directories).

Available conventions:
- documentation.md: CLAUDE.md/README.md format specification
- structural.md: Code quality conventions (god object, testing, etc.)
- temporal.md: Comment hygiene (timeless present rule)
- severity.md: MUST/SHOULD/COULD severity definitions
- intent-markers.md: :PERF:/:UNSAFE: marker format
"""
from pathlib import Path

from skills.lib.io import read_text_or_exit


def get_convention(name: str) -> str:
    """Load convention from centralized store.

    Args:
        name: Convention filename (e.g., "temporal.md", "structural.md")

    Returns:
        Full content of the convention file

    Exits:
        With contextual error message if convention doesn't exist
    """
    # parents[4]: lib -> skills -> scripts -> skills -> .claude
    convention_path = Path(__file__).resolve().parents[4] / "conventions" / name
    return read_text_or_exit(convention_path, "loading convention")
