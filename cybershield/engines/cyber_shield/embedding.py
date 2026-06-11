"""Lightweight, dependency-free message embedding for visualisation.

The Cyber Shield GUI shows a 2-D scatter of the conversation: each directed
message becomes a point, and lexically similar messages land near each other so
clusters (e.g. a run of insults) are visible at a glance.

A real semantic embedding (sentence-transformers) is the "full-mode" option, but
that pulls in heavy dependencies and a model download. To keep the default GUI
fast and offline we use a transparent, pure-python pipeline:

1. **Hashing-trick vectorisation** — each message is turned into a fixed-length
   numeric vector by hashing its word tokens and character trigrams into buckets.
   Messages sharing words/character patterns get similar vectors. No vocabulary,
   no training, fully deterministic.
2. **PCA to two dimensions** — we project those vectors onto their two principal
   directions using plain power iteration (no numpy), then normalise the result
   into the unit square for easy plotting.

This is "embedding-style" rather than semantically deep, but it is honest about
what it is, runs anywhere, and is enough to reveal structure in a conversation.
Swapping in true embeddings later is a matter of replacing :func:`vectorise`
behind the same interface.
"""

from __future__ import annotations

import math
from typing import Sequence

from cybershield.utils import tokenize

# Dimensionality of the hashed feature space. Small enough to be cheap, large
# enough to keep hash collisions low for short social-media messages.
_DIM = 96


def vectorise(text: str, dim: int = _DIM) -> list[float]:
    """Map text to a fixed-length, L2-normalised vector via the hashing trick.

    Both word tokens and character trigrams are hashed, so the vector captures
    word overlap *and* sub-word similarity (helpful for handles, hashtags and
    light obfuscation).
    """
    vector = [0.0] * dim
    tokens = tokenize(text)
    for token in tokens:
        vector[_bucket(token, dim)] += 1.0
        # Character trigrams add robustness to spelling/obfuscation.
        padded = f"  {token} "
        for i in range(len(padded) - 2):
            vector[_bucket(padded[i : i + 3], dim)] += 0.5
    return _l2_normalise(vector)


def embed_2d(texts: Sequence[str]) -> list[tuple[float, float]]:
    """Return a normalised (x, y) in [0, 1]^2 for each input text.

    Coordinates are produced by projecting the hashed vectors onto their top two
    principal components. Degenerate inputs (no texts, one text, or no variance)
    are handled gracefully so the caller never has to special-case them.
    """
    n = len(texts)
    if n == 0:
        return []
    if n == 1:
        return [(0.5, 0.5)]

    vectors = [vectorise(t) for t in texts]
    centered = _center(vectors)

    pc1 = _principal_component(centered)
    deflated = _deflate(centered, pc1)
    pc2 = _principal_component(deflated)

    coords = [(_dot(v, pc1), _dot(v, pc2)) for v in centered]
    return _normalise_unit_square(coords)


# --------------------------------------------------------------------------- #
# Hashing helpers
# --------------------------------------------------------------------------- #
def _bucket(token: str, dim: int) -> int:
    # Python's hash is salted per-process; use a stable hash so layouts are
    # reproducible across runs (important for an explainable tool).
    h = 2166136261
    for ch in token:
        h = (h ^ ord(ch)) * 16777619 & 0xFFFFFFFF
    return h % dim


def _l2_normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


# --------------------------------------------------------------------------- #
# Minimal PCA (power iteration), pure python
# --------------------------------------------------------------------------- #
def _center(vectors: list[list[float]]) -> list[list[float]]:
    dim = len(vectors[0])
    mean = [0.0] * dim
    for v in vectors:
        for k in range(dim):
            mean[k] += v[k]
    n = len(vectors)
    mean = [m / n for m in mean]
    return [[v[k] - mean[k] for k in range(dim)] for v in vectors]


def _principal_component(centered: list[list[float]], iterations: int = 60) -> list[float]:
    """Top principal direction of the centered data via power iteration on XᵀX."""
    dim = len(centered[0])
    # Deterministic, non-symmetric seed so we don't land orthogonal to the PC.
    v = _l2_normalise([math.sin(k + 1) for k in range(dim)])
    for _ in range(iterations):
        # w = (Xᵀ X) v  computed without forming the covariance matrix.
        w = [0.0] * dim
        for x in centered:
            dot = _dot(x, v)
            if dot == 0.0:
                continue
            for k in range(dim):
                w[k] += x[k] * dot
        norm = math.sqrt(sum(c * c for c in w))
        if norm < 1e-12:
            break  # no variance left; current v is as good as any
        v = [c / norm for c in w]
    return v


def _deflate(centered: list[list[float]], component: list[float]) -> list[list[float]]:
    """Remove the variance already explained by ``component`` from each vector."""
    result = []
    for x in centered:
        projection = _dot(x, component)
        result.append([x[k] - projection * component[k] for k in range(len(x))])
    return result


def _dot(a: list[float], b: list[float]) -> float:
    return sum(a[k] * b[k] for k in range(len(a)))


def _normalise_unit_square(
    coords: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    """Scale raw projections into [0.05, 0.95]^2 with a small margin.

    Falls back to spreading points evenly along a line when an axis has no
    spread, so overlapping/identical messages still render as distinct points.
    """
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y

    out: list[tuple[float, float]] = []
    for i, (x, y) in enumerate(coords):
        nx = (x - min_x) / span_x if span_x > 1e-9 else (i + 1) / (len(coords) + 1)
        ny = (y - min_y) / span_y if span_y > 1e-9 else 0.5
        # Pad into [0.05, 0.95] so points never touch the panel edges.
        out.append((0.05 + 0.90 * nx, 0.05 + 0.90 * ny))
    return out
