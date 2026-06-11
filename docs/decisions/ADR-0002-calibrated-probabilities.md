# ADR-0002 — Every detector emits a calibrated probability

**Status:** Accepted

## Context

Detectors will be combined and compared, and their scores will set thresholds for
routing cases to humans (ADR-0005) and for sorting findings into severity tiers
(ADR-0004). Raw model outputs are not comparable across detectors: one model's
0.8 may mean "almost certainly abusive" while another's 0.8 means "a coin-flip in
disguise." If we fuse or threshold on uncalibrated scores, the whole pipeline's
behaviour becomes unpredictable and unfair.

## Decision

Every detector emits a probability in [0, 1] that is **calibrated** — meaning
that among the cases it scores at 0.8, roughly 80% are truly positive. Detectors
are fit with a calibration step (for example Platt scaling or isotonic
regression) against held-out labelled data, and calibration quality is measured
(reliability diagrams, expected calibration error) and tracked over time.
Detectors that cannot yet be calibrated against real labels ship as explicitly
*uncalibrated* and are treated as advisory only until labels exist.

## Consequences

Scores become meaningful and comparable, so fusion and thresholds behave
predictably and can be reasoned about. Confidence becomes a first-class output
the router can trust. The cost is that every detector needs a labelled
calibration set and periodic recalibration as data drifts, which ties this
decision to the feedback loop (ADR-0006) that produces those labels. We also
accept that calibration must be checked per subgroup, not just globally, which
connects to the fairness gate (ADR-0007).

## Alternatives considered

Using raw model confidences directly was rejected as a false economy: it makes
every downstream threshold a guess. A single global calibration applied after
fusion was rejected because it cannot fix the fact that the inputs being fused
were themselves on incomparable scales.
