"""Engine 1 — Social Data Analytics.

Collects and normalises account + post data from social-media platforms behind
a single, platform-agnostic interface.
"""

from cybershield.engines.social_analytics.base import (
    PlatformConnector,
    ConnectorError,
    CredentialsError,
)
from cybershield.engines.social_analytics.engine import SocialDataAnalyticsEngine
from cybershield.engines.social_analytics.twitter import TwitterConnector

__all__ = [
    "SocialDataAnalyticsEngine",
    "PlatformConnector",
    "TwitterConnector",
    "ConnectorError",
    "CredentialsError",
]
