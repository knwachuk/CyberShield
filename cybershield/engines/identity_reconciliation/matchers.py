"""Per-feature similarity scorers for identity reconciliation.

Each matcher is a small, named function that compares one facet of two accounts
and returns a similarity score in [0, 1] (or ``None`` when the feature is
missing on either side and therefore can't contribute). Keeping every signal
isolated like this means the overall match score is fully explainable: we can
show the user exactly which features matched and by how much, rather than
emitting a single opaque number.

The engine combines these signals with configurable weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cybershield.models import Account
from cybershield.utils import (
    jaccard_similarity,
    levenshtein_ratio,
    normalise,
    sequence_similarity,
)


@dataclass(frozen=True)
class FeatureScore:
    """One feature's contribution to an overall identity match."""

    name: str
    score: Optional[float]          # None => feature could not be evaluated
    weight: float
    detail: str = ""

    @property
    def applicable(self) -> bool:
        return self.score is not None


def score_username(a: Account, b: Account) -> FeatureScore:
    """Handles are the single strongest cross-platform signal.

    People tend to reuse the same handle, so we combine an edit-distance ratio
    with a sequence ratio to reward both near-identical and lightly-edited
    handles (``jane.doe`` vs ``janedoe``).
    """
    if not a.username or not b.username:
        return FeatureScore("username", None, 0.35)
    lev = levenshtein_ratio(a.username, b.username)
    seq = sequence_similarity(a.username, b.username)
    score = max(lev, seq)
    return FeatureScore(
        "username",
        score,
        0.35,
        detail=f"@{a.username} vs @{b.username}",
    )


def score_display_name(a: Account, b: Account) -> FeatureScore:
    """Display / real names are a strong corroborating signal."""
    if not a.display_name or not b.display_name:
        return FeatureScore("display_name", None, 0.25)
    score = max(
        sequence_similarity(a.display_name, b.display_name),
        jaccard_similarity(a.display_name, b.display_name),
    )
    return FeatureScore(
        "display_name",
        score,
        0.25,
        detail=f"{a.display_name!r} vs {b.display_name!r}",
    )


def score_bio(a: Account, b: Account) -> FeatureScore:
    """Bios share vocabulary across platforms; token overlap captures that."""
    if not a.bio or not b.bio:
        return FeatureScore("bio", None, 0.20)
    score = jaccard_similarity(a.bio, b.bio)
    return FeatureScore("bio", score, 0.20, detail="bio token overlap")


def score_location(a: Account, b: Account) -> FeatureScore:
    """Location is a weak but useful tie-breaker."""
    if not a.location or not b.location:
        return FeatureScore("location", None, 0.08)
    score = sequence_similarity(a.location, b.location)
    return FeatureScore(
        "location", score, 0.08, detail=f"{a.location!r} vs {b.location!r}"
    )


def score_url(a: Account, b: Account) -> FeatureScore:
    """A shared external link (personal site) is near-conclusive when present."""
    if not a.url or not b.url:
        return FeatureScore("url", None, 0.12)
    # Compare on the normalised host+path, ignoring scheme and trailing slashes.
    score = 1.0 if _canonical_url(a.url) == _canonical_url(b.url) else 0.0
    return FeatureScore("url", score, 0.12, detail=f"{a.url} vs {b.url}")


def _canonical_url(url: str) -> str:
    cleaned = normalise(url)
    for prefix in ("https://", "http://", "www."):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.rstrip("/")


# The ordered set of matchers the engine runs. New signals (e.g. profile-image
# perceptual hashing) can be appended here without changing the engine code.
ALL_MATCHERS = (
    score_username,
    score_display_name,
    score_bio,
    score_location,
    score_url,
)
