"""The Cyber Shield engine.

Cyber Shield answers a focused question: *given two accounts on the same
platform, is one abusing the other?* It does this by isolating the messages one
account directs at the other (mentions and replies), scoring each with the
``AbuseAnalyzer``, and aggregating the evidence into a verdict with a confidence
level and a fully itemised breakdown.

By default it looks in both directions (A→B and B→A), because real harassment
situations are often asymmetric and it's useful to see who is the aggressor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Optional

from cybershield.engines.cyber_shield.analyzers import AbuseAnalyzer, MessageAssessment
from cybershield.models import Account, Post


# Verdict thresholds applied to a direction's aggregate abuse evidence.
_VERDICTS = (
    (0.70, "abuse_detected"),
    (0.45, "likely_abuse"),
    (0.20, "borderline"),
    (0.0, "no_abuse_detected"),
)


@dataclass
class DirectionReport:
    """Abuse evidence for messages flowing from one account to another."""

    from_account: Account
    to_account: Account
    directed_message_count: int
    abusive_message_count: int
    mean_abuse_score: float
    max_abuse_score: float
    verdict: str
    assessments: list[MessageAssessment] = field(default_factory=list)

    @property
    def abusive_ratio(self) -> float:
        if self.directed_message_count == 0:
            return 0.0
        return self.abusive_message_count / self.directed_message_count

    def to_dict(self) -> dict:
        return {
            "from": self.from_account.handle,
            "to": self.to_account.handle,
            "directed_message_count": self.directed_message_count,
            "abusive_message_count": self.abusive_message_count,
            "abusive_ratio": round(self.abusive_ratio, 3),
            "mean_abuse_score": round(self.mean_abuse_score, 3),
            "max_abuse_score": round(self.max_abuse_score, 3),
            "verdict": self.verdict,
            # Only abusive messages are itemised by default to keep reports tight;
            # the full set is available via ``assessments``.
            "flagged_messages": [
                a.to_dict() for a in self.assessments if a.is_abusive
            ],
        }


@dataclass
class AbuseReport:
    """The full two-way comparison between two accounts."""

    account_a: Account
    account_b: Account
    a_to_b: DirectionReport
    b_to_a: Optional[DirectionReport]
    overall_verdict: str
    aggressor: Optional[str]            # handle of the worse offender, if any

    def to_dict(self) -> dict:
        return {
            "account_a": self.account_a.handle,
            "account_b": self.account_b.handle,
            "overall_verdict": self.overall_verdict,
            "aggressor": self.aggressor,
            "a_to_b": self.a_to_b.to_dict(),
            "b_to_a": self.b_to_a.to_dict() if self.b_to_a else None,
        }

    def summary(self) -> str:
        """A short human-readable headline for the GUI / CLI."""
        if self.overall_verdict == "no_abuse_detected":
            return "No directed abuse detected between these accounts."
        who = f" Likely aggressor: {self.aggressor}." if self.aggressor else ""
        return f"Verdict: {self.overall_verdict.replace('_', ' ')}.{who}"


class CyberShieldEngine:
    """Compares two accounts on one platform to detect directed abuse."""

    def __init__(self, analyzer: Optional[AbuseAnalyzer] = None) -> None:
        self.analyzer = analyzer or AbuseAnalyzer()

    # ------------------------------------------------------------------ #
    # Core comparison
    # ------------------------------------------------------------------ #
    def compare(
        self,
        account_a: Account,
        account_b: Account,
        posts_a: list[Post],
        posts_b: Optional[list[Post]] = None,
    ) -> AbuseReport:
        """Compare two accounts using posts already collected for each.

        ``posts_a`` are A's posts (used to assess A→B). ``posts_b`` are B's posts
        (used to assess B→A); if omitted, only the A→B direction is evaluated.
        """
        a_to_b = self._assess_direction(account_a, account_b, posts_a)
        b_to_a = (
            self._assess_direction(account_b, account_a, posts_b)
            if posts_b is not None
            else None
        )
        overall, aggressor = self._combine(a_to_b, b_to_a)
        return AbuseReport(
            account_a=account_a,
            account_b=account_b,
            a_to_b=a_to_b,
            b_to_a=b_to_a,
            overall_verdict=overall,
            aggressor=aggressor,
        )

    def compare_via_engine(
        self,
        data_engine,
        platform,
        username_a: str,
        username_b: str,
        post_limit: int = 100,
        bidirectional: bool = True,
    ) -> AbuseReport:
        """Convenience: collect both accounts' data, then compare.

        ``data_engine`` is a ``SocialDataAnalyticsEngine``. This keeps the GUI
        thin — it hands us two handles and we orchestrate collection + analysis.
        """
        account_a = data_engine.collect_account(platform, username_a)
        account_b = data_engine.collect_account(platform, username_b)
        posts_a = data_engine.collect_posts(platform, username_a, limit=post_limit)
        posts_b = (
            data_engine.collect_posts(platform, username_b, limit=post_limit)
            if bidirectional
            else None
        )
        return self.compare(account_a, account_b, posts_a, posts_b)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _assess_direction(
        self, sender: Account, recipient: Account, posts: list[Post]
    ) -> DirectionReport:
        # Keep only the sender's posts that actually address the recipient.
        directed = [p for p in (posts or []) if p.addresses(recipient.username)]
        assessments = [self.analyzer.analyze(p.text) for p in directed]

        scores = [a.abuse_score for a in assessments]
        abusive = [a for a in assessments if a.is_abusive]
        mean_score = mean(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        return DirectionReport(
            from_account=sender,
            to_account=recipient,
            directed_message_count=len(directed),
            abusive_message_count=len(abusive),
            mean_abuse_score=mean_score,
            max_abuse_score=max_score,
            verdict=self._verdict(assessments),
            assessments=assessments,
        )

    @staticmethod
    def _verdict(assessments: list[MessageAssessment]) -> str:
        """Derive a direction verdict from its message assessments.

        The signal combines *intensity* (the worst message) with *persistence*
        (how often abuse recurs), since repeated low-grade hostility and a
        single severe attack are both meaningful — and neither should be hidden
        by averaging alone.
        """
        if not assessments:
            return "no_abuse_detected"
        scores = [a.abuse_score for a in assessments]
        abusive_ratio = sum(s >= 0.5 for s in scores) / len(scores)
        # Weight the peak heavily but let a high abusive ratio reinforce it.
        signal = 0.7 * max(scores) + 0.3 * abusive_ratio
        for threshold, label in _VERDICTS:
            if signal >= threshold:
                return label
        return "no_abuse_detected"

    @staticmethod
    def _combine(
        a_to_b: DirectionReport, b_to_a: Optional[DirectionReport]
    ) -> tuple[str, Optional[str]]:
        """Roll the per-direction verdicts into an overall verdict + aggressor."""
        severity_rank = {
            "no_abuse_detected": 0,
            "borderline": 1,
            "likely_abuse": 2,
            "abuse_detected": 3,
        }
        directions = [d for d in (a_to_b, b_to_a) if d is not None]
        worst = max(directions, key=lambda d: severity_rank[d.verdict])
        overall = worst.verdict

        aggressor = None
        if severity_rank[overall] >= 2:  # likely_abuse or worse
            # The aggressor is the sender of the most severe direction, unless
            # both directions are equally and seriously abusive (mutual).
            if (
                b_to_a is not None
                and severity_rank[a_to_b.verdict] == severity_rank[b_to_a.verdict]
                and abs(a_to_b.max_abuse_score - b_to_a.max_abuse_score) < 0.1
            ):
                aggressor = "mutual / reciprocal"
            else:
                aggressor = worst.from_account.handle
        return overall, aggressor
