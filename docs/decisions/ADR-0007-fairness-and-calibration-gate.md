# ADR-0007 — Fairness and calibration auditing is a release gate

**Status:** Accepted

## Context

Toxicity and hate-speech models have well-documented failure modes that fall
unevenly on people: African-American English and mere mentions of identity terms
(for example "I am a gay man") are disproportionately flagged as toxic. In an
abuse-detection system, a biased detector does not just make errors — it
systematically silences or over-polices particular groups, which is the opposite
of the system's purpose. Accuracy measured only in aggregate hides this entirely.

## Decision

Fairness and calibration auditing is a **release gate**: no detector or fused
configuration ships unless it passes subgroup checks, not just global ones. We
measure error rates and calibration across the groups most exposed to model bias
(dialect, identity-term presence, language) using held-out, representative
evaluation sets, and we set thresholds on disparity that a release must meet. The
audit is run on every retrain (ADR-0006) and its results are recorded with the
model version. Counterspeech and quoted-abuse handling are part of the same gate,
since failing them is a major source of over-policing the very people being
defended.

## Consequences

Bias becomes a tracked, blocking metric rather than an incident discovered after
harm. Releases are slower and require maintained evaluation sets that genuinely
represent affected groups — itself a non-trivial, ongoing investment. We accept
that a model with higher aggregate accuracy may be rejected for unacceptable
subgroup disparity; fairness can outrank raw accuracy at the gate. This decision
depends on calibration being a per-subgroup property (ADR-0002) and on the
evidence trail (ADR-0003) that makes disparities diagnosable.

## Alternatives considered

Auditing only global accuracy was rejected because it is exactly the blind spot
that lets biased models pass. One-off fairness reviews were rejected because the
models change continuously; the check must be a gate on every release, not a
launch-day formality.
