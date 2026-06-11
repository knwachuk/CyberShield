# CyberShield

A three-engine platform for social-media intelligence and abuse detection.

CyberShield is built around three cooperating engines that share one normalised
data vocabulary, so each can be developed, tested and extended independently:

1. **Social Data Analytics Engine** — collects and normalises account and post
   data from social-media platforms behind a pluggable connector interface.
   Twitter/X is the first supported platform.
2. **Cyber Identity Reconciliation Engine** — given an account on one platform,
   scores candidate accounts on another platform to estimate whether they belong
   to the same person, with a fully explainable, weighted breakdown.
3. **Cyber Shield Engine** — compares two accounts on a single platform to
   determine whether one is directing abuse at the other, and produces an
   itemised abuse report.

A local web **GUI** sits on top of the Cyber Shield engine for interactive use.

## Why this structure

The early prototype was a handful of scripts (`twitter.py`, `post.py`, two
`text_sniffer.py` variants) with a hard-coded API token and results printed to
stdout. CyberShield refactors that work into a clean package:

- secrets come from the environment, never source;
- every engine emits/consumes the same `Account` / `Post` objects, so platforms
  and analyzers are swappable;
- the abuse analyzer keeps the original multi-model idea (lexicon + VADER +
  HateBERT/RoBERTa) but runs the heavy transformer models only in opt-in
  "full" mode, so the common path is fast and dependency-light.

## Install

```bash
# Lite mode (default): lexicon + VADER, GUI, live Twitter collection.
pip install -r requirements.txt

# Full mode: adds transformer hate-speech / sentiment models (large download).
pip install -r requirements-full.txt
```

## Configuration

All configuration is via environment variables (a `.env` file in the project
root is loaded automatically):

| Variable | Purpose | Default |
| --- | --- | --- |
| `CYBERSHIELD_TWITTER_BEARER_TOKEN` | Twitter/X API v2 bearer token | _unset_ → uses bundled sample data |
| `CYBERSHIELD_ANALYZER_MODE` | `lite` or `full` | `lite` |
| `CYBERSHIELD_DATA_DIR` | Location of sample/fixture data | `<repo>/data` |

With no token configured, the Twitter connector serves the bundled sample
accounts in `data/sample_twitter.json`, so everything runs offline.

## Usage

### GUI (primary interface to Cyber Shield)

```bash
python run_gui.py
# open http://127.0.0.1:5000
```

Enter two handles (try the sample accounts `abuser_joe` and `kind_amy`), choose
whether to analyze both directions, and run the comparison.

### Command line

```bash
# Collect an account + posts and show basic analytics.
python cli.py collect kind_amy

# Compare two accounts for directed abuse (both directions).
python cli.py shield abuser_joe kind_amy

# Cross-platform identity match on the bundled sample.
python cli.py reconcile
```

## Tests

```bash
pytest
```

The test suite covers the lite path end-to-end (models, text utilities,
identity scoring, and abuse comparison against the sample fixtures) and requires
no heavy dependencies.

## Package layout

```
cybershield/
  models.py                      normalised Account / Post / Platform
  config.py                      env-based settings + .env loader
  utils/text.py                  dependency-free similarity helpers
  engines/
    social_analytics/            Engine 1: connectors + collection + analytics
      base.py                    PlatformConnector contract
      twitter.py                 Twitter/X connector (live or fixtures)
      engine.py                  SocialDataAnalyticsEngine
    identity_reconciliation/     Engine 2: cross-platform identity matching
      matchers.py                per-feature similarity scorers
      engine.py                  CyberIdentityReconciliationEngine
    cyber_shield/                Engine 3: directed-abuse comparison
      analyzers.py               lexicon + VADER + optional transformers
      engine.py                  CyberShieldEngine
      lexicon.txt                default abuse lexicon
  gui/app.py                     Flask GUI for Cyber Shield
cli.py                           CLI for all three engines
run_gui.py                       GUI launcher
data/                            bundled sample fixtures
tests/                           pytest suite
```

## Extending to new platforms

Subclass `PlatformConnector`, implement `fetch_account` and `fetch_posts` to
return normalised objects, and register the connector in
`SocialDataAnalyticsEngine.with_defaults()`. The identity and abuse engines work
on the new platform immediately, because they only ever see normalised data.

## Responsible-use note

The abuse lexicon shipped here is a small, demonstration-grade list and the
scores are heuristic. CyberShield is intended as decision-support: flag and
explain potential abuse for a human reviewer, not to make automated enforcement
decisions on its own.
