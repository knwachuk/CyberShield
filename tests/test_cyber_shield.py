"""Tests for the Cyber Shield engine and its analyzers (lite mode)."""

from cybershield.engines.cyber_shield import CyberShieldEngine
from cybershield.engines.cyber_shield.analyzers import AbuseAnalyzer
from cybershield.engines.social_analytics import SocialDataAnalyticsEngine, TwitterConnector
from cybershield.models import Account, Platform, Post


def _connector():
    """A fixture-backed connector loaded from the bundled sample data."""
    return TwitterConnector.from_settings()


def _engine():
    sdae = SocialDataAnalyticsEngine()
    sdae.register_connector(_connector())
    return sdae


def test_analyzer_flags_abusive_text():
    analyzer = AbuseAnalyzer()
    result = analyzer.analyze("you are so stupid, nobody likes you")
    assert result.is_abusive
    assert result.abuse_score >= 0.5
    assert any(t["term"] == "stupid" for t in result.matched_terms)


def test_analyzer_passes_clean_text():
    analyzer = AbuseAnalyzer()
    result = analyzer.analyze("Great game last night, what a finish!")
    assert not result.is_abusive
    assert result.matched_terms == []


def test_fuzzy_obfuscation_is_caught():
    analyzer = AbuseAnalyzer()
    # "stup1d" should fuzzy-match "stupid".
    result = analyzer.analyze("you are stup1d")
    assert any(t["term"] == "stupid" for t in result.matched_terms)


def test_directed_abuse_detected_one_way():
    sdae = _engine()
    shield = CyberShieldEngine()
    report = shield.compare_via_engine(
        sdae, Platform.TWITTER, "abuser_joe", "kind_amy", bidirectional=True
    )
    # Joe directs multiple abusive messages at Amy.
    assert report.a_to_b.directed_message_count >= 3
    assert report.a_to_b.abusive_message_count >= 3
    assert report.overall_verdict in {"abuse_detected", "likely_abuse"}
    assert "abuser_joe" in (report.aggressor or "")
    # Amy is not abusive back.
    assert report.b_to_a.abusive_message_count == 0


def test_no_abuse_between_friendly_accounts():
    sdae = _engine()
    shield = CyberShieldEngine()
    report = shield.compare_via_engine(
        sdae, Platform.TWITTER, "neutral_sam", "kind_amy", bidirectional=True
    )
    assert report.overall_verdict == "no_abuse_detected"
    assert report.aggressor is None


def test_only_directed_messages_are_assessed():
    """Joe's non-directed posts (e.g. about a game) must not count against Amy."""
    shield = CyberShieldEngine()
    joe = Account(platform=Platform.TWITTER, username="abuser_joe")
    amy = Account(platform=Platform.TWITTER, username="kind_amy")
    posts = [
        Post(platform=Platform.TWITTER, post_id="1", author_username="abuser_joe",
             text="@kind_amy you are stupid", mentions=["kind_amy"]),
        Post(platform=Platform.TWITTER, post_id="2", author_username="abuser_joe",
             text="this referee is an idiot", mentions=[]),  # not directed at Amy
    ]
    report = shield.compare(joe, amy, posts)
    assert report.a_to_b.directed_message_count == 1
