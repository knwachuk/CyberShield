"""Tests for normalised models and the pure-python text utilities."""

from cybershield.models import Account, Platform, Post
from cybershield.utils import (
    jaccard_similarity,
    levenshtein_ratio,
    normalise,
    sequence_similarity,
    tokenize,
)


def test_platform_parsing_aliases():
    assert Platform.from_string("X") is Platform.TWITTER
    assert Platform.from_string("twitter") is Platform.TWITTER
    assert Platform.from_string("nope") is Platform.UNKNOWN


def test_account_normalises_handle_and_platform():
    acct = Account(platform="x", username="  @Alice ")
    assert acct.platform is Platform.TWITTER
    assert acct.username == "Alice"
    assert acct.handle == "@Alice (twitter)"


def test_account_round_trip():
    acct = Account(platform=Platform.TWITTER, username="bob", display_name="Bob")
    restored = Account.from_dict(acct.to_dict())
    assert restored.username == "bob"
    assert restored.platform is Platform.TWITTER


def test_post_addresses_detection():
    post = Post(
        platform=Platform.TWITTER,
        post_id="1",
        author_username="joe",
        text="@amy hello",
        mentions=["@Amy"],
        reply_to_username="Amy",
    )
    assert post.addresses("amy")
    assert post.addresses("@AMY")
    assert not post.addresses("someone_else")


def test_normalise_strips_accents_and_case():
    assert normalise("José  GARCÍA") == "jose garcia"


def test_similarity_bounds():
    assert tokenize("Hello, world!") == ["hello", "world"]
    assert jaccard_similarity("a b c", "a b c") == 1.0
    assert jaccard_similarity("a b", "c d") == 0.0
    assert sequence_similarity("janedoe", "jane_doe") > 0.8
    assert 0.0 <= levenshtein_ratio("kitten", "sitting") <= 1.0
    assert levenshtein_ratio("same", "same") == 1.0
