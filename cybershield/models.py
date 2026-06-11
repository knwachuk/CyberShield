"""Normalised data models shared by every CyberShield engine.

These dataclasses form the *lingua franca* of the platform. A platform
connector (e.g. the Twitter connector) is responsible for translating whatever
shape an upstream API returns into these objects. Once data is normalised, the
Identity Reconciliation and Cyber Shield engines can operate on it without
caring which platform it originated from.

Design notes
------------
* We deliberately keep the schema small and platform-agnostic. Fields that only
  some platforms expose live in the free-form ``raw`` dictionary so that no
  information is lost, while the typed fields stay universal.
* Everything is JSON-serialisable via ``to_dict`` so reports, caches and the GUI
  can round-trip objects to disk and back without custom encoders.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Platform(str, Enum):
    """Supported / recognised social-media platforms.

    Inheriting from ``str`` means a Platform compares equal to its string value
    and serialises to plain text in JSON, which keeps cached files readable.
    """

    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    LINKEDIN = "linkedin"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> "Platform":
        """Best-effort parse of a free-text platform name (case-insensitive)."""
        if value is None:
            return cls.UNKNOWN
        normalised = value.strip().lower()
        # Accept a couple of common aliases so callers can say "x" or "X (Twitter)".
        aliases = {"x": cls.TWITTER, "x (twitter)": cls.TWITTER, "ig": cls.INSTAGRAM}
        if normalised in aliases:
            return aliases[normalised]
        for member in cls:
            if member.value == normalised:
                return member
        return cls.UNKNOWN


@dataclass
class Account:
    """A normalised representation of a social-media account/profile.

    Only ``platform`` and ``username`` are strictly required to identify an
    account. Every other field is optional because different platforms expose
    different levels of detail, and because we may only have partial data when
    reconciling identities across platforms.
    """

    platform: Platform
    username: str                      # handle without the leading "@"
    user_id: Optional[str] = None      # platform-native stable id, if known
    display_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None          # personal/website link in the profile
    profile_image_url: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    verified: Optional[bool] = None
    created_at: Optional[datetime] = None
    # Free-form bag for platform-specific fields we don't model explicitly.
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Be forgiving about how platform is supplied (string or enum).
        if not isinstance(self.platform, Platform):
            self.platform = Platform.from_string(str(self.platform))
        # Normalise the handle: strip a leading "@" and surrounding whitespace.
        if self.username:
            self.username = self.username.strip().lstrip("@")

    @property
    def handle(self) -> str:
        """A human-friendly identifier such as ``@alice (twitter)``."""
        return f"@{self.username} ({self.platform.value})"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["platform"] = self.platform.value
        if isinstance(self.created_at, datetime):
            data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Account":
        data = dict(data)  # shallow copy so we don't mutate the caller's dict
        created = data.get("created_at")
        if isinstance(created, str):
            data["created_at"] = _parse_datetime(created)
        data["platform"] = Platform.from_string(data.get("platform", "unknown"))
        # Drop unknown keys so the constructor doesn't explode if the schema grew.
        allowed = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class Post:
    """A normalised post / tweet / status update authored by an account."""

    platform: Platform
    post_id: str
    author_username: str
    text: str
    created_at: Optional[datetime] = None
    # Accounts explicitly addressed by the post (mentions / replies). Stored as
    # bare usernames so the Cyber Shield engine can detect *directed* abuse.
    mentions: list[str] = field(default_factory=list)
    reply_to_username: Optional[str] = None
    like_count: Optional[int] = None
    repost_count: Optional[int] = None
    is_repost: bool = False
    url: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.platform, Platform):
            self.platform = Platform.from_string(str(self.platform))
        self.mentions = [m.strip().lstrip("@").lower() for m in (self.mentions or [])]
        if self.reply_to_username:
            self.reply_to_username = self.reply_to_username.strip().lstrip("@").lower()

    def addresses(self, username: str) -> bool:
        """True if this post mentions or replies to ``username`` (case-insensitive)."""
        target = username.strip().lstrip("@").lower()
        return target in self.mentions or self.reply_to_username == target

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["platform"] = self.platform.value
        if isinstance(self.created_at, datetime):
            data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Post":
        data = dict(data)
        created = data.get("created_at")
        if isinstance(created, str):
            data["created_at"] = _parse_datetime(created)
        data["platform"] = Platform.from_string(data.get("platform", "unknown"))
        allowed = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in data.items() if k in allowed})


def _parse_datetime(value: str) -> Optional[datetime]:
    """Parse the handful of timestamp formats the supported APIs emit.

    We tolerate ISO-8601 with a trailing ``Z`` (Twitter v2) as well as the
    ``YYYY-MM-DD HH:MM:SS+00:00`` form found in some of the cached sample data.
    Returns ``None`` rather than raising so a single odd timestamp never breaks
    an entire ingestion run.
    """
    if not value:
        return None
    candidate = value.strip().replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            dt = parser(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return None
