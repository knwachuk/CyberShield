"""Twitter / X connector for the Social Data Analytics engine.

This connector can operate in two modes, chosen automatically:

* **Live mode** — when a bearer token is configured it calls the Twitter/X
  API v2 (``/2/users/by/username`` and ``/2/users/{id}/tweets``) and normalises
  the JSON into ``Account`` / ``Post`` objects.
* **Fixture mode** — when no token is available (or a lookup misses live) it
  serves data from a local fixture file. This keeps the whole platform usable
  for development, demos and tests without burning API quota or leaking
  credentials, and mirrors the cached tweet data that already lived in the
  prototype.

The two earlier prototype scripts (``twitter.py`` and ``post.py``) embedded a
bearer token in source and printed results to stdout. This connector keeps the
same API calls but reads the token from the environment and returns structured
objects instead.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from cybershield.config import settings as default_settings
from cybershield.engines.social_analytics.base import (
    ConnectorError,
    CredentialsError,
    PlatformConnector,
)
from cybershield.models import Account, Platform, Post

# Base URL for the Twitter/X API v2.
_API_BASE = "https://api.twitter.com/2"


class TwitterConnector(PlatformConnector):
    """Collects normalised Twitter/X data, live or from fixtures."""

    platform = Platform.TWITTER

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        fixtures: Optional[dict[str, Any]] = None,
        request_timeout: float = 15.0,
    ) -> None:
        self.bearer_token = bearer_token
        # ``fixtures`` maps a lower-cased username to {"account": {...},
        # "posts": [...]}. Used whenever live access is unavailable.
        self.fixtures = {k.lower(): v for k, v in (fixtures or {}).items()}
        self.request_timeout = request_timeout

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_settings(cls, fixture_path: Optional[Path] = None) -> "TwitterConnector":
        """Build a connector from global settings + an optional fixture file."""
        fixtures: dict[str, Any] = {}
        path = fixture_path or (default_settings.data_dir / "sample_twitter.json")
        if Path(path).exists():
            try:
                fixtures = json.loads(Path(path).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # A broken fixture file shouldn't prevent live mode from working.
                fixtures = {}
        return cls(bearer_token=default_settings.twitter_bearer_token, fixtures=fixtures)

    def is_available(self) -> bool:
        return bool(self.bearer_token) or bool(self.fixtures)

    # ------------------------------------------------------------------ #
    # PlatformConnector contract
    # ------------------------------------------------------------------ #
    def fetch_account(self, username: str) -> Account:
        username = username.strip().lstrip("@")
        if self.bearer_token:
            try:
                return self._fetch_account_live(username)
            except CredentialsError:
                raise
            except ConnectorError:
                # Fall through to fixtures if a live lookup fails for any reason
                # other than bad credentials (e.g. rate-limit, transient 5xx).
                pass
        return self._fetch_account_fixture(username)

    def fetch_posts(self, username: str, limit: int = 100) -> list[Post]:
        username = username.strip().lstrip("@")
        if self.bearer_token:
            try:
                return self._fetch_posts_live(username, limit)
            except CredentialsError:
                raise
            except ConnectorError:
                pass
        return self._fetch_posts_fixture(username, limit)

    # ------------------------------------------------------------------ #
    # Live API implementation
    # ------------------------------------------------------------------ #
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def _get(self, url: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Perform a single authenticated GET and translate transport errors.

        ``requests`` is imported lazily so the package can be installed and used
        in fixture-only mode without the dependency present.
        """
        try:
            import requests  # local import keeps it optional
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ConnectorError(
                "The 'requests' package is required for live Twitter access. "
                "Install it or run in fixture mode."
            ) from exc

        try:
            response = requests.get(
                url, headers=self._headers(), params=params, timeout=self.request_timeout
            )
        except requests.RequestException as exc:
            raise ConnectorError(f"Network error talking to Twitter: {exc}") from exc

        if response.status_code in (401, 403):
            raise CredentialsError(
                f"Twitter rejected the bearer token (HTTP {response.status_code})."
            )
        if response.status_code == 429:
            raise ConnectorError("Twitter rate limit reached (HTTP 429).")
        if response.status_code >= 400:
            raise ConnectorError(
                f"Twitter API error (HTTP {response.status_code}): {response.text[:200]}"
            )
        return response.json()

    def _fetch_account_live(self, username: str) -> Account:
        url = f"{_API_BASE}/users/by/username/{username}"
        params = {
            "user.fields": "description,location,url,public_metrics,verified,"
            "created_at,profile_image_url"
        }
        payload = self._get(url, params)
        if "data" not in payload:
            raise ConnectorError(f"User @{username} not found on Twitter.")
        return self._normalise_account(payload["data"])

    def _fetch_posts_live(self, username: str, limit: int) -> list[Post]:
        account = self._fetch_account_live(username)
        user_id = account.user_id
        posts: list[Post] = []
        next_token: Optional[str] = None
        # The v2 endpoint caps page size at 100; paginate until we hit ``limit``.
        while len(posts) < limit:
            params: dict[str, Any] = {
                "max_results": min(100, limit - len(posts)),
                "tweet.fields": "created_at,public_metrics,entities,referenced_tweets,"
                "in_reply_to_user_id",
                "expansions": "in_reply_to_user_id",
            }
            if next_token:
                params["pagination_token"] = next_token
            payload = self._get(f"{_API_BASE}/users/{user_id}/tweets", params)
            for raw_post in payload.get("data", []):
                posts.append(self._normalise_post(raw_post, author=username))
            next_token = payload.get("meta", {}).get("next_token")
            if not next_token:
                break
            time.sleep(1)  # be polite to the API between pages
        return posts[:limit]

    # ------------------------------------------------------------------ #
    # Fixture implementation
    # ------------------------------------------------------------------ #
    def _fetch_account_fixture(self, username: str) -> Account:
        record = self.fixtures.get(username.lower())
        if not record or "account" not in record:
            raise ConnectorError(
                f"No live credentials and no fixture data for @{username}."
            )
        data = dict(record["account"])
        data.setdefault("platform", Platform.TWITTER.value)
        data.setdefault("username", username)
        return Account.from_dict(data)

    def _fetch_posts_fixture(self, username: str, limit: int) -> list[Post]:
        record = self.fixtures.get(username.lower())
        if not record:
            raise ConnectorError(
                f"No live credentials and no fixture data for @{username}."
            )
        posts = []
        for raw in record.get("posts", [])[:limit]:
            data = dict(raw)
            data.setdefault("platform", Platform.TWITTER.value)
            data.setdefault("author_username", username)
            posts.append(Post.from_dict(data))
        return posts

    # ------------------------------------------------------------------ #
    # Normalisation of live API payloads
    # ------------------------------------------------------------------ #
    def _normalise_account(self, data: dict[str, Any]) -> Account:
        metrics = data.get("public_metrics", {})
        return Account(
            platform=Platform.TWITTER,
            username=data.get("username", ""),
            user_id=data.get("id"),
            display_name=data.get("name"),
            bio=data.get("description"),
            location=data.get("location"),
            url=data.get("url"),
            profile_image_url=data.get("profile_image_url"),
            followers_count=metrics.get("followers_count"),
            following_count=metrics.get("following_count"),
            post_count=metrics.get("tweet_count"),
            verified=data.get("verified"),
            raw=data,
        )

    def _normalise_post(self, data: dict[str, Any], author: str) -> Post:
        metrics = data.get("public_metrics", {})
        # Mentions come from the tweet's "entities" object when requested.
        mentions = [
            m.get("username", "")
            for m in data.get("entities", {}).get("mentions", [])
        ]
        # A reply carries a referenced_tweets entry of type "replied_to"; the
        # replied-to user id is in in_reply_to_user_id, but the API doesn't give
        # us their handle inline, so we leave reply_to_username to mentions which
        # for replies always include the addressed handle as the first mention.
        is_repost = any(
            ref.get("type") == "retweeted"
            for ref in data.get("referenced_tweets", [])
        )
        return Post(
            platform=Platform.TWITTER,
            post_id=str(data.get("id")),
            author_username=author,
            text=data.get("text", ""),
            created_at=data.get("created_at"),
            mentions=mentions,
            reply_to_username=mentions[0] if mentions else None,
            like_count=metrics.get("like_count"),
            repost_count=metrics.get("retweet_count"),
            is_repost=is_repost,
            raw=data,
        )
