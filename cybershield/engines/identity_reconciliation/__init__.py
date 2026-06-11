"""Engine 2 — Cyber Identity Reconciliation.

Given an account on one platform, estimate which account(s) on another platform
belong to the same (or a closely related) person.
"""

from cybershield.engines.identity_reconciliation.engine import (
    CyberIdentityReconciliationEngine,
    MatchResult,
)

__all__ = ["CyberIdentityReconciliationEngine", "MatchResult"]
