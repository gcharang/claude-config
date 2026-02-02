"""Quality Reviewer scripts for QR phases.

This package contains:
- Base classes for decompose and verify workflows
- Phase-specific QR scripts (plan-design, plan-code, plan-docs, impl-code, impl-docs)

Base classes:
- DecomposeBase: Shared logic for QR item generation
- VerifyBase: Shared logic for single-item verification

Scripts extend base classes with phase-specific logic.
"""

from .qr_decompose_base import DecomposeBase, write_qr_state
from .qr_verify_base import VerifyBase

__all__ = [
    "DecomposeBase",
    "write_qr_state",
    "VerifyBase",
]
