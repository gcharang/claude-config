"""Skill registration and manifest generation.

Generates JSON manifest from registered workflows.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_manifest() -> dict[str, Any]:
    """Generate JSON manifest from workflow registry."""
    from .core import get_workflow_registry

    workflows = {name: w.to_manifest() for name, w in get_workflow_registry().items()}

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills": workflows,
    }


def write_manifest(path: Path | str) -> None:
    """Write manifest to file."""
    manifest = generate_manifest()
    Path(path).write_text(json.dumps(manifest, indent=2) + "\n")


def check_manifest(path: Path | str) -> tuple[bool, str]:
    """Compare existing manifest to registry.

    Returns:
        (True, "OK") if in sync
        (False, error_message) if mismatch
    """
    try:
        existing = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return False, f"Manifest not found: {path}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in manifest: {e}"

    current = generate_manifest()

    # Compare skills only (ignore generated_at)
    if existing.get("skills") != current.get("skills"):
        existing_skills = set(existing.get("skills", {}).keys())
        current_skills = set(current.get("skills", {}).keys())

        added = current_skills - existing_skills
        removed = existing_skills - current_skills
        changed = []

        for name in existing_skills & current_skills:
            if existing["skills"][name] != current["skills"][name]:
                changed.append(name)

        parts = []
        if added:
            parts.append(f"added: {', '.join(sorted(added))}")
        if removed:
            parts.append(f"removed: {', '.join(sorted(removed))}")
        if changed:
            parts.append(f"changed: {', '.join(sorted(changed))}")

        return False, f"Manifest out of sync ({'; '.join(parts)})"

    return True, "OK"


