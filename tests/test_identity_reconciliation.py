"""Tests for the Cyber Identity Reconciliation engine."""

from cybershield.engines.identity_reconciliation import (
    CyberIdentityReconciliationEngine,
)
from cybershield.models import Account, Platform


def _source():
    return Account(
        platform=Platform.TWITTER,
        username="amy_rivera_art",
        display_name="Amy Rivera",
        bio="Illustrator & community organizer. Coffee enthusiast.",
        location="Newark, NJ",
        url="https://amyrivera.art",
    )


def test_strong_match_ranks_first_and_high_confidence():
    engine = CyberIdentityReconciliationEngine()
    source = _source()
    strong = Account(
        platform=Platform.INSTAGRAM,
        username="amyrivera.art",
        display_name="Amy Rivera",
        bio="Illustrator and community organizer in Newark. Coffee + murals.",
        location="Newark",
        url="https://amyrivera.art",
    )
    weak = Account(
        platform=Platform.INSTAGRAM,
        username="totally_unrelated",
        display_name="Bob's Auto Parts",
        bio="Best deals on tires in Texas.",
        location="Austin, TX",
    )
    ranked = engine.reconcile(source, [weak, strong])
    assert ranked[0].candidate.username == "amyrivera.art"
    assert ranked[0].confidence > ranked[1].confidence
    assert ranked[0].band in {"very_likely_same", "likely_same"}


def test_unrelated_account_scores_low():
    engine = CyberIdentityReconciliationEngine()
    weak = Account(
        platform=Platform.INSTAGRAM,
        username="totally_unrelated",
        display_name="Bob's Auto Parts",
        bio="Best deals on tires in Texas.",
        location="Austin, TX",
    )
    result = engine.compare(_source(), weak)
    assert result.confidence < 0.45
    assert result.band == "unlikely"


def test_missing_fields_do_not_break_scoring():
    engine = CyberIdentityReconciliationEngine()
    sparse = Account(platform=Platform.INSTAGRAM, username="amy_rivera_art")
    result = engine.compare(_source(), sparse)
    # Username alone is identical, so confidence should be high despite missing
    # bio/location/url on the candidate.
    assert result.confidence > 0.65
    # The applicable-weight renormalisation means score stays in range.
    assert 0.0 <= result.confidence <= 1.0
