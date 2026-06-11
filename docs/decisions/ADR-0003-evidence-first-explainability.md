# ADR-0003 — Every score carries its evidence

**Status:** Accepted

## Context

The outputs of this system — "this account is abusing that one" — can affect real
people and may need to withstand an appeal or an audit. A score on its own, no
matter how accurate, is not enough: a reviewer has to see what produced it, and
the subject of a decision deserves a reason. The existing engines already lean
this way (the identity engine itemises its feature scores; the abuse analyzer
returns matched terms), and we want that to be a guarantee rather than a habit.

## Decision

Explainability is a construction-time property, not a post-hoc add-on. Every
detector returns, alongside its calibrated score, a structured **evidence**
record: the spans of text, the matched terms, the metadata values, or the
graph facts that drove the score, each with its individual contribution. The
fusion step (ADR-0004) preserves and aggregates this evidence so that a final
severity verdict can always be unfolded back into the per-detector reasons. No
detector is allowed to emit a bare number.

## Consequences

Reviewers can act quickly and fairly because the "why" is attached to the "what",
and the system can produce a human-readable rationale and an audit trail by
default. This also disciplines detector design: a detector that cannot say why it
fired is a detector we do not yet understand well enough to trust. The cost is a
slightly heavier output format and the requirement that even model-based
detectors expose attributions (token importances, nearest examples, or a
generated rationale that is itself checked). Black-box detectors are permitted
only as advisory signals, never as the sole basis of a tier.

## Alternatives considered

Storing only scores and reconstructing explanations later was rejected because
post-hoc explanation of a black box is unreliable and often misleading. Logging
raw model internals was rejected as unreadable to a reviewer; evidence must be
expressed in terms a person can evaluate.
