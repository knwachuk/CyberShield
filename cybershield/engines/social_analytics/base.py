"""The connector contract that every platform integration must satisfy.

Adding support for a new platform is intentionally a small job: subclass
``PlatformConnector``, implement ``fetch_account`` and ``fetch_posts`` so they
return normalised ``Account`` / ``Post`` objects, and register the class with
``SocialDataAnalyticsEngine``. The rest of the system — identity reconciliation,
abuse analysis, the GUI — keeps working unchanged because it only ever sees
normalised objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cybershield.models import Account, Platform, Post


class ConnectorError(RuntimeError):
    """Raised when a connector cannot fulfil a request (network, API error...)."""


class CredentialsError(ConnectorError):
    """Raised specifically when required API credentials are missing or rejected."""


class PlatformConnector(ABC):
    """Abstract base class for a single-platform data connector."""

    #: The platform this connector serves. Subclasses must override.
    platform: Platform = Platform.UNKNOWN

    @abstractmethod
    def fetch_account(self, username: str) -> Account:
        """Return the normalised profile for ``username``.

        Raises ``ConnectorError`` (or the more specific ``CredentialsError``)
        on failure so callers can distinguish "no such user" from "we couldn't
        even authenticate".
        """

    @abstractmethod
    def fetch_posts(self, username: str, limit: int = 100) -> list[Post]:
        """Return up to ``limit`` recent normalised posts authored by ``username``."""

    def is_available(self) -> bool:
        """Whether this connector can currently talk to its platform.

        The default implementation assumes a connector is always available
        (e.g. a fixture-backed connector). Live connectors override this to
        report on credential / network readiness without raising.
        """
        return True
