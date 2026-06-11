"""The three CyberShield engines.

Importing the engine classes lazily here would create a hard dependency on
optional packages (e.g. transformers for the full Cyber Shield analyzer), so we
keep this namespace package light and let callers import the specific engine
they need, e.g.::

    from cybershield.engines.social_analytics import SocialDataAnalyticsEngine
    from cybershield.engines.identity_reconciliation import CyberIdentityReconciliationEngine
    from cybershield.engines.cyber_shield import CyberShieldEngine
"""
