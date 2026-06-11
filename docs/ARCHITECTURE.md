# CyberShield Architecture

This document describes how the three engines fit together and the reasoning
behind the main design decisions. It is aimed at a developer picking up the
codebase for the first time.

## The shared data model

Everything in CyberShield is expressed in two small, platform-agnostic
dataclasses defined in `cybershield/models.py`:

- `Account` — a profile (handle, display name, bio, location, link, metrics).
- `Post` — a single message, including the accounts it addresses (`mentions`,
  `reply_to_username`), which is what lets Cyber Shield detect *directed* abuse.

A `Platform` enum tags both. This shared vocabulary is the backbone of the
system: connectors translate messy upstream APIs into these objects once, and
from then on no other component needs to know which platform produced the data.
That decoupling is what makes the platform pluggable and the analysis engines
reusable.

## Engine 1 — Social Data Analytics

`engines/social_analytics` owns data acquisition.

- `PlatformConnector` (in `base.py`) is the contract every platform integration
  implements: `fetch_account` and `fetch_posts`, both returning normalised
  objects.
- `TwitterConnector` implements it for Twitter/X. It runs **live** when a bearer
  token is configured (API v2 user + tweets endpoints) and falls back to
  **fixtures** otherwise. The two modes are interchangeable from the caller's
  point of view, which is what makes the rest of the platform testable and
  demoable offline.
- `SocialDataAnalyticsEngine` holds a registry of connectors keyed by platform,
  routes collection requests, and computes light, dependency-free analytics
  (volume, mention graph, engagement). Heavier NLP deliberately lives in Engine
  3 so this engine stays cheap.

Adding a platform = new `PlatformConnector` subclass + one registration line.

## Engine 2 — Cyber Identity Reconciliation

`engines/identity_reconciliation` answers: *is this account on platform X the
same person as that account on platform Y?*

The design favours explainability over a black box. `matchers.py` contains one
small scorer per signal (username, display name, bio, location, shared URL),
each returning a `FeatureScore` in `[0, 1]` plus a weight and a human-readable
detail. The engine combines them with a **weighted mean over applicable
features only** — a missing field simply doesn't vote, rather than dragging the
score down. The numeric confidence is mapped to a discrete band
(`very_likely_same` … `unlikely`) so it's interpretable, and `MatchResult.explain()`
prints the full per-feature breakdown.

The engine ranks candidates; it never asserts identity on its own.

## Engine 3 — Cyber Shield

`engines/cyber_shield` answers: *is one account abusing another on the same
platform?*

- `AbuseAnalyzer` (`analyzers.py`) scores a single message. In **lite** mode it
  combines lexicon matching (exact, multi-word phrase, and a fuzzy pass for
  obfuscation like `stup1d`) with VADER sentiment, blending lexicon evidence and
  negativity into a `0–1` abuse score. In **full** mode it additionally consults
  the transformer hate-speech/sentiment pipelines from the original prototype,
  imported lazily so the heavy stack is optional. If VADER itself is missing,
  a small built-in heuristic keeps lite mode working.
- `CyberShieldEngine` (`engine.py`) takes two accounts and their posts, isolates
  the messages each directs at the other, scores them, and aggregates. The
  per-direction verdict blends **intensity** (worst message) with **persistence**
  (how often abuse recurs), so neither a single severe attack nor sustained
  low-grade hostility is hidden by averaging. The two directions are combined
  into an overall verdict and a likely-aggressor attribution (or `mutual` when
  both sides are comparably abusive).

The output (`AbuseReport`) is fully itemised and JSON-serialisable, which is
what the GUI renders.

## The GUI

`gui/app.py` is a single-file Flask app (one inline template) that drives the
Cyber Shield engine: two handles in, an explained abuse report out. It talks
only to the high-level engines, so it never touches connector or analyzer
internals. Flask is imported lazily so importing the package doesn't require it.

## Operating modes summary

| Mode | Abuse analysis | Dependencies | When |
| --- | --- | --- | --- |
| lite (default) | lexicon + VADER | small, pure-python-ish | demos, dev, fast triage |
| full | + HateBERT / RoBERTa | torch + transformers (large) | higher-quality classification |

| Data source | Trigger |
| --- | --- |
| Live Twitter/X API | `CYBERSHIELD_TWITTER_BEARER_TOKEN` set |
| Bundled fixtures | no token, or live lookup miss |

## Design principles recap

1. **One normalised model** decouples platforms from analysis.
2. **Connectors are pluggable**; the engines never special-case a platform.
3. **Explainability first** — both identity and abuse outputs itemise their
   evidence rather than emitting a single opaque number.
4. **Cheap by default, powerful on demand** — heavy ML is opt-in.
5. **Runs offline** — fixtures make the whole system demoable without
   credentials or network access.
