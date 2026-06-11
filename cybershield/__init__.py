"""CyberShield — a three-engine platform for social-media intelligence and abuse detection.

The package is organised around three cooperating engines:

1. ``SocialDataAnalyticsEngine`` (engines.social_analytics)
   Collects and normalises data from social-media platforms. Twitter/X is the
   first supported connector; the connector architecture is pluggable so other
   platforms can be added without touching the rest of the system.

2. ``CyberIdentityReconciliationEngine`` (engines.identity_reconciliation)
   Given an account on one platform, scores candidate accounts on another
   platform to estimate whether they belong to the same (or a closely related)
   person.

3. ``CyberShieldEngine`` (engines.cyber_shield)
   Compares two accounts on a *single* platform to determine whether one is
   directing abuse at the other, producing an explainable abuse report.

Every engine speaks the same normalised vocabulary defined in
``cybershield.models`` (Account, Post, ...), which keeps the engines decoupled:
a connector only has to emit normalised objects, and the analysis engines never
need to know which platform the data originally came from.
"""

from cybershield.models import Account, Post, Platform

__all__ = ["Account", "Post", "Platform", "__version__"]

__version__ = "0.1.0"
