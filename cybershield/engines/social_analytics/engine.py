"""The Social Data Analytics Engine itself.

Responsibilities:

* Hold a registry of platform connectors and route requests to the right one.
* Provide a single entry point for collecting an account and its posts.
* Compute light-weight, dependency-free analytics over collected posts
  (volume, mention graph, engagement) that the other engines and the GUI can
  build on.

Heavier NLP analytics (sentiment, abuse) deliberately live in the Cyber Shield
engine rather than here, so this engine stays cheap to run and easy to extend
with new platforms.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from cybershield.engines.social_analytics.base import ConnectorError, PlatformConnector
from cybershield.engines.social_analytics.twitter import TwitterConnector
from cybershield.models import Account, Platform, Post


class SocialDataAnalyticsEngine:
    """Collects social-media data behind a uniform, multi-platform interface."""

    def __init__(self) -> None:
        self._connectors: dict[Platform, PlatformConnector] = {}

    # ------------------------------------------------------------------ #
    # Connector registry
    # ------------------------------------------------------------------ #
    def register_connector(self, connector: PlatformConnector) -> None:
        """Register (or replace) the connector for its platform."""
        self._connectors[connector.platform] = connector

    def connector_for(self, platform: Platform | str) -> PlatformConnector:
        platform = (
            platform if isinstance(platform, Platform) else Platform.from_string(platform)
        )
        connector = self._connectors.get(platform)
        if connector is None:
            raise ConnectorError(f"No connector registered for platform '{platform.value}'.")
        return connector

    @property
    def supported_platforms(self) -> list[Platform]:
        return list(self._connectors.keys())

    @classmethod
    def with_defaults(cls) -> "SocialDataAnalyticsEngine":
        """Convenience builder that wires up the connectors we ship today.

        Currently that means Twitter/X. As new connectors are implemented they
        are registered here, and every downstream consumer gains the new
        platform for free.
        """
        engine = cls()
        engine.register_connector(TwitterConnector.from_settings())
        return engine

    # ------------------------------------------------------------------ #
    # Collection
    # ------------------------------------------------------------------ #
    def collect_account(self, platform: Platform | str, username: str) -> Account:
        return self.connector_for(platform).fetch_account(username)

    def collect_posts(
        self, platform: Platform | str, username: str, limit: int = 100
    ) -> list[Post]:
        return self.connector_for(platform).fetch_posts(username, limit=limit)

    def collect(
        self, platform: Platform | str, username: str, post_limit: int = 100
    ) -> dict:
        """Collect an account, its posts, and a small analytics summary together."""
        account = self.collect_account(platform, username)
        posts = self.collect_posts(platform, username, limit=post_limit)
        return {
            "account": account,
            "posts": posts,
            "analytics": self.summarise(posts),
        }

    # ------------------------------------------------------------------ #
    # Light analytics (pure-python, no ML)
    # ------------------------------------------------------------------ #
    @staticmethod
    def summarise(posts: list[Post]) -> dict:
        """Compute basic descriptive analytics over a list of posts.

        Returns counts, the mention graph (who this author talks to and how
        often) and simple engagement totals. This is the structural backbone
        that, for example, the Cyber Shield engine narrows down to a single
        target when looking for directed abuse.
        """
        if not posts:
            return {
                "post_count": 0,
                "repost_count": 0,
                "reply_count": 0,
                "unique_mentions": 0,
                "top_mentions": [],
                "total_likes": 0,
                "total_reposts": 0,
            }

        mention_counter: Counter[str] = Counter()
        reply_count = 0
        repost_count = 0
        total_likes = 0
        total_reposts = 0

        for post in posts:
            mention_counter.update(post.mentions)
            if post.reply_to_username:
                reply_count += 1
            if post.is_repost:
                repost_count += 1
            total_likes += post.like_count or 0
            total_reposts += post.repost_count or 0

        return {
            "post_count": len(posts),
            "repost_count": repost_count,
            "reply_count": reply_count,
            "unique_mentions": len(mention_counter),
            # Top accounts this author addresses — handy for spotting a target.
            "top_mentions": mention_counter.most_common(10),
            "total_likes": total_likes,
            "total_reposts": total_reposts,
        }
