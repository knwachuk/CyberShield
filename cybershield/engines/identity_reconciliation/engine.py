"""The Cyber Identity Reconciliation Engine.

Workflow
--------
1. Start from a *source* account (e.g. ``@alice`` on Twitter).
2. Supply one or more *candidate* accounts on a target platform — typically the
   shortlist returned by searching that platform for the source's handle and
   display name.
3. The engine scores each candidate against the source across every feature
   matcher and produces a weighted confidence in [0, 1], plus a human-readable
   breakdown and a discrete confidence band.

The engine never asserts identity on its own; it ranks candidates and explains
its reasoning so a human (or the Cyber Shield workflow) can make the final call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from cybershield.engines.identity_reconciliation.matchers import (
    ALL_MATCHERS,
    FeatureScore,
)
from cybershield.models import Account


# Confidence bands keep the numeric score interpretable for end users.
_BANDS = (
    (0.85, "very_likely_same"),
    (0.65, "likely_same"),
    (0.45, "possible"),
    (0.0, "unlikely"),
)


@dataclass
class MatchResult:
    """The outcome of comparing a source account to one candidate."""

    source: Account
    candidate: Account
    confidence: float
    band: str
    features: list[FeatureScore] = field(default_factory=list)

    def explain(self) -> str:
        """A short multi-line explanation of how the score was reached."""
        lines = [
            f"{self.source.handle}  ~  {self.candidate.handle}",
            f"confidence: {self.confidence:.2f} ({self.band})",
        ]
        for feature in self.features:
            if feature.applicable:
                lines.append(
                    f"  - {feature.name}: {feature.score:.2f} "
                    f"(weight {feature.weight:.2f}) {feature.detail}"
                )
            else:
                lines.append(f"  - {feature.name}: n/a (missing data)")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "source": self.source.handle,
            "candidate": self.candidate.handle,
            "confidence": round(self.confidence, 4),
            "band": self.band,
            "features": [
                {
                    "name": f.name,
                    "score": None if f.score is None else round(f.score, 4),
                    "weight": f.weight,
                    "detail": f.detail,
                }
                for f in self.features
            ],
        }


class CyberIdentityReconciliationEngine:
    """Scores and ranks cross-platform identity matches."""

    def __init__(self, matchers: Iterable = ALL_MATCHERS) -> None:
        self.matchers = tuple(matchers)

    def compare(self, source: Account, candidate: Account) -> MatchResult:
        """Score a single candidate against the source account."""
        features = [matcher(source, candidate) for matcher in self.matchers]
        confidence = self._aggregate(features)
        return MatchResult(
            source=source,
            candidate=candidate,
            confidence=confidence,
            band=self._band(confidence),
            features=features,
        )

    def reconcile(
        self, source: Account, candidates: Iterable[Account]
    ) -> list[MatchResult]:
        """Compare the source to every candidate, ranked best-first."""
        results = [self.compare(source, candidate) for candidate in candidates]
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def best_match(
        self, source: Account, candidates: Iterable[Account], threshold: float = 0.65
    ) -> MatchResult | None:
        """Return the top candidate if it clears ``threshold``, else ``None``."""
        ranked = self.reconcile(source, candidates)
        if ranked and ranked[0].confidence >= threshold:
            return ranked[0]
        return None

    # ------------------------------------------------------------------ #
    # Scoring internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _aggregate(features: list[FeatureScore]) -> float:
        """Weighted mean over the *applicable* features only.

        Re-normalising by the applicable weight means a missing field (e.g. no
        bio on one side) neither helps nor hurts the score — it simply doesn't
        vote — which is the intuitive behaviour for partial data.
        """
        applicable = [f for f in features if f.applicable]
        total_weight = sum(f.weight for f in applicable)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum((f.score or 0.0) * f.weight for f in applicable)
        return weighted_sum / total_weight

    @staticmethod
    def _band(confidence: float) -> str:
        for threshold, label in _BANDS:
            if confidence >= threshold:
                return label
        return "unlikely"
