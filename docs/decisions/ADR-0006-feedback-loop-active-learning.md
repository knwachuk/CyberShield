# ADR-0006 — Reviewer decisions feed a labelled training loop

**Status:** Accepted

## Context

Abuse is adversarial and moving: terms get coded, slurs get invented, and tactics
adapt specifically to evade detection. A pipeline trained once and frozen decays.
Meanwhile the human reviewers (ADR-0005) are, every day, producing exactly the
thing the detectors and calibrators are starved of: high-quality labelled
decisions on the hardest cases.

## Decision

Reviewer decisions are captured as labelled training data in a feedback store and
fed back to the detectors and calibrators. The cases routed to humans are
disproportionately the ambiguous ones, which makes this a natural **active
learning** loop — the system is continuously labelling precisely where it is most
uncertain. Retraining and recalibration are scheduled and gated (a new model
version must pass ADR-0007's fairness and calibration checks before it ships).
The feedback store records the evidence the reviewer saw and the rationale for the
decision, not just the label, so future training can learn from the reasoning.

## Consequences

The pipeline improves where it is weakest and keeps pace with evolving abuse. The
loop is self-reinforcing in a healthy way: better routing surfaces better labels,
which yield better detectors. The cost is real infrastructure — a feedback store,
versioned datasets and models, and a retraining cadence — and a risk to manage:
feedback loops can entrench reviewer bias, so the sampling for retraining must be
audited and occasionally counter-sampled to avoid the model simply memorising one
team's blind spots. Data governance and retention apply to the feedback store as
to any store of sensitive material.

## Alternatives considered

A static, periodically hand-curated dataset was rejected as too slow against an
adversarial target. Auto-labelling from the model's own confident outputs was
rejected because it amplifies the model's existing biases instead of correcting
them; human labels on uncertain cases are the signal worth having.
