"""Bootstrap pattern for skills imports.

Standard sys.path setup for workflow scripts:

    import sys
    from pathlib import Path

    # Add .claude/ to path for skills.* imports
    _claude_dir = Path(__file__).resolve().parents[N]  # Adjust N for depth
    if str(_claude_dir) not in sys.path:
        sys.path.insert(0, str(_claude_dir))

    from skills.lib.workflow import ...

Depth guide:
- skills/*/scripts/*.py: .parents[3] (script -> scripts -> skill -> skills -> .claude)
- skills/*/scripts/*/*.py: .parents[4] (script -> subdir -> scripts -> skill -> skills -> .claude)

This 4-line pattern replaces the old 6-line pattern using repetitive .parent.parent...
"""
