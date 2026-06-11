"""Pure-Python text similarity helpers.

These functions intentionally avoid any heavy dependencies (no numpy, no
transformers) so they can run anywhere — including inside the lightweight GUI
process. The Identity Reconciliation engine uses them to compare usernames,
display names and bios; the Cyber Shield engine reuses the tokenizer.

Each function is small, deterministic and individually testable, which keeps
the scoring logic in the engines easy to reason about and audit.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Matches runs of "word" characters (letters/digits/underscore) across scripts.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def normalise(text: str | None) -> str:
    """Lower-case, strip accents and collapse whitespace.

    Accent stripping (NFKD + drop combining marks) means "José" and "Jose"
    compare as equal, which matters when matching display names across
    platforms that handle Unicode differently.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def tokenize(text: str | None) -> list[str]:
    """Split text into lower-cased word tokens (accent-insensitive)."""
    return _TOKEN_RE.findall(normalise(text))


def jaccard_similarity(a: str | None, b: str | None) -> float:
    """Token-set Jaccard similarity in [0, 1].

    Good for comparing free text such as bios, where word *overlap* matters
    more than word order.
    """
    set_a, set_b = set(tokenize(a)), set(tokenize(b))
    if not set_a and not set_b:
        return 1.0  # two empty strings are trivially identical
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union


def sequence_similarity(a: str | None, b: str | None) -> float:
    """Character-level ratio in [0, 1] using difflib's SequenceMatcher.

    Useful for handles and display names, where small edits (``jane_doe`` vs
    ``janedoe``) should still score highly.
    """
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def levenshtein_ratio(a: str | None, b: str | None) -> float:
    """Normalised edit-distance similarity in [0, 1].

    Implemented directly (rather than via a library) to keep dependencies
    minimal and the behaviour transparent. 1.0 means identical; 0.0 means no
    shared structure relative to the longer string's length.
    """
    s1, s2 = normalise(a), normalise(b)
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    distance = _levenshtein_distance(s1, s2)
    return 1.0 - distance / max(len(s1), len(s2))


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Classic dynamic-programming edit distance, O(len(s1) * len(s2))."""
    # Ensure s2 is the shorter string to minimise the working row width.
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]
