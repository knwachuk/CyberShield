# ADR-0004 — Fuse detector outputs into severity tiers, transparently

**Status:** Accepted

## Context

Once detection is decomposed (ADR-0001), something must combine the per-dimension
scores into a single, actionable result. That result should not be a raw number
but a **severity tier** (from "not abuse" through to "critical"), because a death
threat and a rude reply must never share one score, and because tiers are what
drive urgency and how much corroboration a case needs. The combiner is the most
consequential and most contestable part of the pipeline, so how it works must be
inspectable.

## Decision

A dedicated fusion layer maps calibrated detector scores onto the severity tiers
defined in the rubric. The fusion logic is **transparent**: it is expressed as
explicit, versioned rules and weights (data, not buried code), so that any tier
assignment can be traced to the detector scores and rules that produced it.
Certain detectors act as **gates** rather than votes — for example a high-confidence
credible-threat or doxxing signal can raise a case to "critical" on its own, and a
high-confidence counterspeech signal can suppress a false positive — because some
dimensions are not mere contributions to an average. A learned meta-model may be
introduced later, but only if it remains explainable (ADR-0003) and calibrated
(ADR-0002), and it never removes the gate rules.

## Consequences

Verdicts are interpretable and adjustable: tuning behaviour is a reviewed change
to versioned configuration, and every tier carries the evidence chain behind it.
Gate detectors let the system respect that severity is categorical, not just
additive. The cost is the discipline of maintaining the fusion configuration and
versioning it onto every report for reproducibility. We accept that a transparent
rule-plus-gate combiner may be marginally less accurate than an opaque model — a
trade we make deliberately in favour of contestability.

## Alternatives considered

A single opaque model over all detector outputs was rejected for the same reasons
as the monolithic classifier in ADR-0001. A plain weighted average was rejected
because it cannot express categorical gates (a threat is not "a lot of insult").
