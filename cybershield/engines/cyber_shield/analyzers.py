"""Text analyzers underpinning the Cyber Shield engine.

The engine asks an ``AbuseAnalyzer`` a single question per message: *how abusive
is this text, and why?* The analyzer answers with a ``MessageAssessment`` that
bundles a sentiment reading, any matched abusive terms, and a 0-1 abuse score.

Two operating modes
--------------------
* **lite** (default) — lexicon matching plus VADER sentiment. VADER is a small,
  rule-based model with no native code, so lite mode runs anywhere and starts
  instantly. If VADER itself isn't installed we fall back to a tiny built-in
  sentiment heuristic, so the engine is never hard-blocked by a missing package.
* **full** — additionally consults transformer models (the HateBERT /
  twitter-roberta pipelines from the original prototype) for higher-quality
  hate-speech and sentiment classification. These are imported lazily so the
  heavy dependencies are only required when full mode is actually requested.

This layered design preserves the multi-model spirit of the original
``text_sniffer`` while making the common case cheap and dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cybershield.utils import levenshtein_ratio, normalise, tokenize

_DEFAULT_LEXICON_PATH = Path(__file__).with_name("lexicon.txt")

# A minimal sentiment lexicon used only if VADER is unavailable, so lite mode
# still produces a sensible positive/negative/neutral reading.
_FALLBACK_POSITIVE = {
    "good", "great", "love", "nice", "happy", "thanks", "wonderful", "awesome",
    "kind", "support", "congrats", "proud", "respect", "appreciate",
}
_FALLBACK_NEGATIVE = {
    "bad", "awful", "terrible", "hate", "angry", "worst", "stupid", "idiot",
    "dumb", "ugly", "disgusting", "pathetic", "worthless", "loser",
}


@dataclass
class MessageAssessment:
    """Per-message abuse assessment, fully explainable."""

    text: str
    abuse_score: float                      # 0.0 (clean) .. 1.0 (severe abuse)
    sentiment: str                          # positive | negative | neutral
    sentiment_score: float                  # signed compound in [-1, 1]
    matched_terms: list[dict] = field(default_factory=list)
    models: dict = field(default_factory=dict)  # raw per-model outputs

    @property
    def is_abusive(self) -> bool:
        return self.abuse_score >= 0.5

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "abuse_score": round(self.abuse_score, 3),
            "is_abusive": self.is_abusive,
            "sentiment": self.sentiment,
            "sentiment_score": round(self.sentiment_score, 3),
            "matched_terms": self.matched_terms,
            "models": self.models,
        }


class AbuseAnalyzer:
    """Scores individual messages for abusive content."""

    def __init__(
        self,
        lexicon: Optional[list[str]] = None,
        lexicon_path: Optional[Path] = None,
        full_mode: bool = False,
        fuzzy_threshold: float = 0.85,
    ) -> None:
        self.lexicon = lexicon if lexicon is not None else self._load_lexicon(lexicon_path)
        self.full_mode = full_mode
        self.fuzzy_threshold = fuzzy_threshold
        # Lazily-initialised handles for optional dependencies.
        self._vader = None
        self._transformers_loaded = False
        self._hate_pipeline = None
        self._roberta_pipeline = None

    # ------------------------------------------------------------------ #
    # Lexicon loading
    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_lexicon(path: Optional[Path]) -> list[str]:
        path = path or _DEFAULT_LEXICON_PATH
        terms: list[str] = []
        if Path(path).exists():
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    terms.append(normalise(line))
        return terms

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(self, text: str) -> MessageAssessment:
        """Assess a single message and return an explainable result."""
        matched = self._match_lexicon(text)
        sentiment_label, sentiment_score, vader_raw = self._sentiment(text)

        models: dict = {"vader": vader_raw, "lexicon_hits": len(matched)}

        # Base abuse score blends lexicon evidence and negative sentiment.
        lexicon_component = self._lexicon_component(matched)
        sentiment_component = max(0.0, -sentiment_score)  # only negativity counts
        abuse_score = min(1.0, 0.65 * lexicon_component + 0.35 * sentiment_component)

        # Full mode lets transformer hate-speech detection raise the score.
        if self.full_mode:
            hate_score, model_outputs = self._transformer_signals(text)
            models.update(model_outputs)
            abuse_score = max(abuse_score, hate_score)

        return MessageAssessment(
            text=text,
            abuse_score=abuse_score,
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            matched_terms=matched,
            models=models,
        )

    # ------------------------------------------------------------------ #
    # Lexicon matching (exact + fuzzy)
    # ------------------------------------------------------------------ #
    def _match_lexicon(self, text: str) -> list[dict]:
        """Find abusive terms via exact token match, multi-word phrase match,
        and a fuzzy pass that catches light obfuscation."""
        normalised_text = normalise(text)
        tokens = tokenize(text)
        token_set = set(tokens)
        matched: list[dict] = []
        seen: set[str] = set()

        for term in self.lexicon:
            if term in seen:
                continue
            if " " in term:
                # Multi-word phrase: substring match on the normalised text.
                if term in normalised_text:
                    matched.append({"term": term, "match": "phrase", "severity": "high"})
                    seen.add(term)
                continue
            if term in token_set:
                matched.append({"term": term, "match": "exact", "severity": "high"})
                seen.add(term)
                continue
            # Fuzzy: catch "st*pid"/"stup1d"-style obfuscation against any token.
            for token in tokens:
                if abs(len(token) - len(term)) <= 2:
                    ratio = levenshtein_ratio(token, term)
                    if ratio >= self.fuzzy_threshold:
                        matched.append(
                            {
                                "term": term,
                                "match": "fuzzy",
                                "token": token,
                                "similarity": round(ratio, 3),
                                "severity": "medium",
                            }
                        )
                        seen.add(term)
                        break
        return matched

    @staticmethod
    def _lexicon_component(matched: list[dict]) -> float:
        """Map the number/severity of matched terms onto a 0-1 contribution.

        One high-severity hit already implies strong evidence; additional hits
        push toward 1.0 with diminishing returns.
        """
        if not matched:
            return 0.0
        weight = 0.0
        for hit in matched:
            weight += 0.7 if hit.get("severity") == "high" else 0.45
        return min(1.0, weight)

    # ------------------------------------------------------------------ #
    # Sentiment
    # ------------------------------------------------------------------ #
    def _sentiment(self, text: str) -> tuple[str, float, dict]:
        """Return (label, compound_score, raw). Uses VADER if available."""
        vader = self._get_vader()
        if vader is not None:
            scores = vader.polarity_scores(text)
            compound = scores["compound"]
            label = (
                "positive" if compound > 0.05
                else "negative" if compound < -0.05
                else "neutral"
            )
            return label, compound, scores
        # Fallback heuristic when VADER isn't installed.
        return self._fallback_sentiment(text)

    def _get_vader(self):
        if self._vader is not None:
            return self._vader
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._vader = SentimentIntensityAnalyzer()
        except ImportError:
            self._vader = None
        return self._vader

    @staticmethod
    def _fallback_sentiment(text: str) -> tuple[str, float, dict]:
        tokens = tokenize(text)
        pos = sum(t in _FALLBACK_POSITIVE for t in tokens)
        neg = sum(t in _FALLBACK_NEGATIVE for t in tokens)
        total = pos + neg
        if total == 0:
            return "neutral", 0.0, {"engine": "fallback", "pos": 0, "neg": 0}
        compound = (pos - neg) / total
        label = (
            "positive" if compound > 0.05
            else "negative" if compound < -0.05
            else "neutral"
        )
        return label, compound, {"engine": "fallback", "pos": pos, "neg": neg}

    # ------------------------------------------------------------------ #
    # Optional transformer signals (full mode only)
    # ------------------------------------------------------------------ #
    def _transformer_signals(self, text: str) -> tuple[float, dict]:
        """Run hate-speech + sentiment transformer pipelines.

        Mirrors the models used in the original prototype. Imports happen here,
        on first use, so the heavy dependency is optional.
        """
        if not self._transformers_loaded:
            self._load_transformers()
        outputs: dict = {}
        hate_score = 0.0
        if self._hate_pipeline is not None:
            result = self._hate_pipeline(text)[0]
            outputs["hatebert"] = {
                "label": result["label"],
                "confidence": round(float(result["score"]), 3),
            }
            # HateXplain labels: 'hatespeech', 'offensive', 'normal'.
            if result["label"].lower() in {"hatespeech", "offensive"}:
                hate_score = float(result["score"])
        if self._roberta_pipeline is not None:
            r = self._roberta_pipeline(text)[0]
            outputs["roberta"] = {
                "label": r["label"],
                "confidence": round(float(r["score"]), 3),
            }
        return hate_score, outputs

    def _load_transformers(self) -> None:
        self._transformers_loaded = True
        try:
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                pipeline,
            )

            hate_name = "Hate-speech-CNERG/bert-base-uncased-hatexplain"
            tokenizer = AutoTokenizer.from_pretrained(hate_name)
            model = AutoModelForSequenceClassification.from_pretrained(hate_name)
            self._hate_pipeline = pipeline(
                "text-classification", model=model, tokenizer=tokenizer
            )
            self._roberta_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment",
            )
        except Exception:  # pragma: no cover - heavy/optional path
            # If anything about the heavy stack is unavailable, full mode simply
            # degrades to the lite signals rather than crashing.
            self._hate_pipeline = None
            self._roberta_pipeline = None
