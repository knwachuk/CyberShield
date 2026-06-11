# ADR-0005 — Route by confidence; humans own the ambiguous middle

**Status:** Accepted

## Context

Several dimensions of the rubric — consent, sarcasm, reclaimed language, the line
between abuse and counterspeech — are not reliably solvable by software today, and
the cost of a confident mistake (silencing a victim, or missing a real threat) is
high. A system that issues an automatic verdict on every case will be wrong in
exactly the cases that matter most. At the same time, sending *every* case to a
human does not scale.

## Decision

The pipeline routes by confidence and severity rather than auto-deciding
everything. Only unambiguous extremes — very high-confidence, high-severity cases,
or clearly benign ones — may be handled automatically, and even then conservatively.
Everything in the ambiguous middle, and anything a low-tractability detector
(ADR-0001) has flagged, is routed to a human review queue with its full evidence
attached. Human-in-the-loop is treated as a designed, permanent feature of the
architecture, not a temporary scaffold to be removed once models improve. There is
no code path that takes an enforcement action without either clearing a high
threshold or passing through a person.

## Consequences

The system fails safe: when it is unsure, a person decides, and the reviewer's
time is spent where it is most valuable. Thresholds become a deliberate
policy knob, set conservatively and tuned against measured error costs. The cost
is the need for a review queue, reviewer tooling, and capacity planning, and the
acceptance that throughput is bounded by human review for the hard cases — which
we regard as correct, not as a limitation. This decision depends on calibrated
confidences (ADR-0002) and attached evidence (ADR-0003), and it feeds the
feedback loop (ADR-0006).

## Alternatives considered

Full automation was rejected as unsafe given the stakes and the irreducible
ambiguity. Full manual review was rejected as unscalable and as a waste of human
attention on the easy cases. Confidence-based routing spends the scarce resource —
human judgement — where software is weakest.
