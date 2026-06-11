"""Central configuration for CyberShield.

All secrets (API tokens) are read from environment variables so that nothing
sensitive is hard-coded into the source tree. This is a deliberate change from
the early prototype scripts, which embedded a bearer token directly in the file.

Environment variables
----------------------
* ``CYBERSHIELD_TWITTER_BEARER_TOKEN`` — Twitter/X API v2 bearer token.
* ``CYBERSHIELD_DATA_DIR``             — override the directory used for cached
                                          sample data (defaults to ``<repo>/data``).
* ``CYBERSHIELD_ANALYZER_MODE``        — ``lite`` (default) or ``full``. ``lite``
                                          uses lexicon + VADER only and has no heavy
                                          ML dependencies; ``full`` additionally loads
                                          transformer models.

A ``.env`` file in the project root is loaded automatically if present, which
keeps local development convenient without exposing tokens in the shell history.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Project root = two levels up from this file (cybershield/config.py -> repo root).
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no third-party dependency).

    Only sets variables that are not already present in the real environment,
    so an explicit ``export`` always wins over the file.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    twitter_bearer_token: str | None
    data_dir: Path
    analyzer_mode: str

    @property
    def has_twitter_credentials(self) -> bool:
        return bool(self.twitter_bearer_token)

    @property
    def is_full_mode(self) -> bool:
        return self.analyzer_mode.lower() == "full"


def load_settings() -> Settings:
    """Build a ``Settings`` object from the current environment."""
    data_dir = Path(
        os.environ.get("CYBERSHIELD_DATA_DIR", str(PROJECT_ROOT / "data"))
    )
    return Settings(
        twitter_bearer_token=os.environ.get("CYBERSHIELD_TWITTER_BEARER_TOKEN"),
        data_dir=data_dir,
        analyzer_mode=os.environ.get("CYBERSHIELD_ANALYZER_MODE", "lite"),
    )


# A module-level default that most callers can import directly.
settings = load_settings()
